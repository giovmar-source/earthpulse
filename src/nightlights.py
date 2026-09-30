"""
Luci notturne annuali NASA Black Marble (VIIRS VNP46A4, collezione 2).

Come funziona
-------------
- VNP46A4 e' un composito annuale (dal 2012) su una griglia globale in
  lat/lon a 15 secondi d'arco (~460 m all'equatore), divisa in tile da
  10 x 10 gradi (2400 x 2400 pixel). Tile h00v00 = angolo nord-ovest
  (lon -180, lat 90).
- I file (HDF5, 100-150 MB) si trovano con la ricerca granuli di NASA CMR
  (pubblica) e si scaricano da Earthdata Cloud con un token Earthdata.
- Non scarichiamo il file intero: lo apriamo con h5py tramite richieste
  HTTP "Range" e leggiamo solo la finestra attorno al luogo scelto.

Variabile usata: NearNadir_Composite_Snow_Free (radianza in nW/cm²/sr,
vista quasi verticale, senza neve: la piu' adatta ai confronti tra anni).

Credenziali (mai nel codice o su GitHub):
- EARTHDATA_TOKEN                        (consigliato), oppure
- EARTHDATA_USERNAME + EARTHDATA_PASSWORD
"""

from __future__ import annotations

import io
import math
import os
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

import numpy as np
import requests
from PIL import Image

from src.imagery import color_stops_hex, colorize, to_png


CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
PRODUCT = "VNP46A4"
PRODUCT_VERSION = "2"
FIRST_YEAR = 2012

GRID_PATH = "HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields"
VARIABLE = "NearNadir_Composite_Snow_Free"
QUALITY_VARIABLE = f"{VARIABLE}_Quality"
QUALITY_FILL = 255
LAND_WATER_VARIABLE = "Land_Water_Mask"
SEA_WATER = 3                    # 011 = Sea Water (User Guide, Collection 2)
SEA_DARK_RADIANCE = 2.0          # sul mare mostriamo solo luci evidenti (porti, navi)

TILE_DEGREES = 10
TILE_PIXELS = 2400
PIXELS_PER_DEGREE = TILE_PIXELS // TILE_DEGREES  # 240 -> 15"
KM_PER_DEGREE_LAT = 111.32

MIN_SIDE_KM = 10
MAX_SIDE_KM = 150
DEFAULT_SIDE_KM = 60
IMAGE_SIZE = 600

HTTP_TIMEOUT = (10, 60)
BLOCK_SIZE = 512 * 1024
MAX_CACHED_BLOCKS = 64          # ~32 MB massimo per file aperto
PREFETCH_WORKERS = 6
CMR_CACHE_SECONDS = 12 * 3600
ARRAY_CACHE_SIZE = 48

# Scala colori su log10(radianza): nero-blu (buio) -> viola -> arancio
# -> giallo -> bianco (centri citta').
NIGHT_COLOR_STOPS = [
    (-0.7, (6, 8, 22)),
    (0.0, (30, 28, 85)),
    (0.5, (115, 45, 125)),
    (1.0, (225, 105, 40)),
    (1.5, (255, 195, 60)),
    (2.2, (255, 250, 225)),
]
NIGHT_INVALID_COLOR = (70, 70, 70)
NIGHT_SEA_COLOR = (16, 28, 48)
NIGHT_LEGEND_LABELS = ["Buio", "Periferie, strade", "Centri urbani"]

ATTRIBUTION = (
    "Luci notturne: NASA Black Marble VNP46A4 (VIIRS/Suomi NPP), "
    "LAADS DAAC / Earthdata"
)


class NightLightsUnavailable(RuntimeError):
    """Dati luci notturne non raggiungibili (credenziali, rete, archivio)."""


# ------------------------------------------------------------------
# Geometria: area -> tile e pixel
# ------------------------------------------------------------------

@dataclass(frozen=True)
class PixelWindow:
    """Finestra in pixel globali: righe [row0, row1), colonne [col0, col1)."""
    row0: int
    row1: int
    col0: int
    col1: int

    @property
    def shape(self):
        return (self.row1 - self.row0, self.col1 - self.col0)


def area_bbox(lat: float, lon: float, side_km: float):
    """Quadrato di lato side_km centrato sul punto -> (ovest, sud, est, nord)."""
    half_lat = side_km / 2 / KM_PER_DEGREE_LAT
    cos_lat = max(math.cos(math.radians(lat)), 0.05)
    half_lon = side_km / 2 / (KM_PER_DEGREE_LAT * cos_lat)
    south = max(lat - half_lat, -90.0)
    north = min(lat + half_lat, 90.0)
    return (lon - half_lon, south, lon + half_lon, north)


def global_window(bbox) -> PixelWindow:
    """Bbox in gradi -> finestra di pixel sulla griglia globale 15"."""
    west, south, east, north = bbox
    col0 = math.floor((west + 180.0) * PIXELS_PER_DEGREE)
    col1 = math.ceil((east + 180.0) * PIXELS_PER_DEGREE)
    row0 = math.floor((90.0 - north) * PIXELS_PER_DEGREE)
    row1 = math.ceil((90.0 - south) * PIXELS_PER_DEGREE)
    row0 = max(row0, 0)
    row1 = min(row1, 180 * PIXELS_PER_DEGREE)
    return PixelWindow(row0, max(row1, row0 + 1), col0, max(col1, col0 + 1))


def tile_id(h: int, v: int) -> str:
    return f"h{h:02d}v{v:02d}"


def tile_for_point(lat: float, lon: float):
    h = int((lon + 180.0) // TILE_DEGREES) % 36
    v = min(int((90.0 - lat) // TILE_DEGREES), 17)
    return h, v


def tile_pieces(window: PixelWindow):
    """
    Divide la finestra globale nei pezzi che cadono in ciascun tile.
    Restituisce [(h, v, righe_tile, colonne_tile, righe_out, colonne_out)]
    con slice pronti per leggere dal tile e scrivere nell'array finale.
    Gestisce anche l'antimeridiano (colonne fuori da 0..8640).
    """
    pieces = []
    v_first = window.row0 // TILE_PIXELS
    v_last = (window.row1 - 1) // TILE_PIXELS
    h_first = math.floor(window.col0 / TILE_PIXELS)
    h_last = math.floor((window.col1 - 1) / TILE_PIXELS)

    for v in range(v_first, v_last + 1):
        tile_row0 = v * TILE_PIXELS
        r0 = max(window.row0, tile_row0)
        r1 = min(window.row1, tile_row0 + TILE_PIXELS)
        for h_raw in range(h_first, h_last + 1):
            tile_col0 = h_raw * TILE_PIXELS
            c0 = max(window.col0, tile_col0)
            c1 = min(window.col1, tile_col0 + TILE_PIXELS)
            h = h_raw % 36
            pieces.append((
                h, v,
                slice(r0 - tile_row0, r1 - tile_row0),
                slice(c0 - tile_col0, c1 - tile_col0),
                slice(r0 - window.row0, r1 - window.row0),
                slice(c0 - window.col0, c1 - window.col0),
            ))
    return pieces


# ------------------------------------------------------------------
# Autenticazione e ricerca dei file (NASA CMR)
# ------------------------------------------------------------------

EARTHDATA_LOGIN_HOST = "urs.earthdata.nasa.gov"


class _EarthdataSession(requests.Session):
    """
    Sessione che rimanda nome utente/password solo al server di login
    NASA durante i redirect (schema consigliato da NASA Earthdata).
    """

    def rebuild_auth(self, prepared_request, response):
        headers = prepared_request.headers
        url = prepared_request.url
        if "Authorization" in headers:
            original = requests.utils.urlparse(response.request.url).hostname
            redirect = requests.utils.urlparse(url).hostname
            if (original != redirect
                    and redirect != EARTHDATA_LOGIN_HOST
                    and original != EARTHDATA_LOGIN_HOST):
                del headers["Authorization"]


def has_credentials() -> bool:
    return bool(
        os.environ.get("EARTHDATA_TOKEN")
        or (os.environ.get("EARTHDATA_USERNAME")
            and os.environ.get("EARTHDATA_PASSWORD"))
    )


def make_session() -> requests.Session:
    token = os.environ.get("EARTHDATA_TOKEN", "").strip()
    if token:
        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {token}"
        return session

    username = os.environ.get("EARTHDATA_USERNAME", "").strip()
    password = os.environ.get("EARTHDATA_PASSWORD", "")
    if username and password:
        session = _EarthdataSession()
        session.auth = (username, password)
        return session

    raise NightLightsUnavailable(
        "Luci notturne non configurate: manca EARTHDATA_TOKEN "
        "(oppure EARTHDATA_USERNAME e EARTHDATA_PASSWORD)."
    )


_GRANULE_RE = re.compile(
    rf"{PRODUCT}\.A(\d{{4}})001\.(h\d\dv\d\d)\.(\d{{3}})\.(\d+)\.h5$"
)


def parse_granule_name(name: str):
    """'VNP46A4.A2014001.h19v04.002.2025090174551.h5' -> (2014, 'h19v04', '2025090174551')."""
    match = _GRANULE_RE.search(name)
    if not match:
        return None
    return int(match.group(1)), match.group(2), match.group(4)


def pick_granule_urls(entries, wanted_tile: str) -> dict:
    """
    Dalle voci CMR -> {anno: url https del file .h5} per un tile.
    Se ci sono piu' versioni dello stesso anno tiene la piu' recente.
    """
    best = {}
    for entry in entries:
        for link in entry.get("links", []):
            href = link.get("href", "")
            if not href.startswith("https://") or not href.endswith(".h5"):
                continue
            if "opendap" in href.lower():
                continue
            parsed = parse_granule_name(href.rsplit("/", 1)[-1])
            if not parsed:
                continue
            year, tile, produced = parsed
            if tile != wanted_tile:
                continue
            current = best.get(year)
            if current is None or produced > current[0]:
                best[year] = (produced, href)
    return {year: href for year, (_, href) in sorted(best.items())}


_cmr_cache = {}
_cmr_lock = threading.Lock()


def find_granules(h: int, v: int) -> dict:
    """{anno: url} per il tile, usando la ricerca pubblica NASA CMR."""
    wanted = tile_id(h, v)
    now = time.time()
    with _cmr_lock:
        cached = _cmr_cache.get(wanted)
        if cached and now - cached[0] < CMR_CACHE_SECONDS:
            return cached[1]

    center_lon = -180 + h * TILE_DEGREES + TILE_DEGREES / 2
    center_lat = 90 - v * TILE_DEGREES - TILE_DEGREES / 2
    params = {
        "short_name": PRODUCT,
        "version": PRODUCT_VERSION,
        "point": f"{center_lon},{center_lat}",
        "page_size": 100,
        "sort_key": "start_date",
    }
    try:
        response = requests.get(CMR_GRANULES_URL, params=params,
                                timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        entries = response.json().get("feed", {}).get("entry", [])
    except (requests.RequestException, ValueError) as error:
        raise NightLightsUnavailable(
            f"Ricerca NASA CMR non riuscita: {error}"
        ) from error

    urls = pick_granule_urls(entries, wanted)
    with _cmr_lock:
        _cmr_cache[wanted] = (now, urls)
    return urls


def available_years(lat: float, lon: float) -> list:
    h, v = tile_for_point(lat, lon)
    return sorted(find_granules(h, v))


# ------------------------------------------------------------------
# Lettura parziale di un file remoto (HTTP Range)
# ------------------------------------------------------------------

class HttpRangeFile(io.RawIOBase):
    """
    File remoto in sola lettura, letto a blocchi con richieste HTTP Range.
    h5py lo apre come un file normale e scarica solo i blocchi necessari.
    """

    def __init__(self, url: str, session: requests.Session,
                 block_size: int = BLOCK_SIZE,
                 max_blocks: int = MAX_CACHED_BLOCKS):
        super().__init__()
        self.session = session
        self.block_size = block_size
        self.max_blocks = max_blocks
        self.position = 0
        self.bytes_downloaded = 0
        self.requests_made = 0
        self._blocks = OrderedDict()
        self._lock = threading.Lock()
        self.fetch_session = session
        self.url, self.size = self._resolve(url)

    # -- apertura -------------------------------------------------
    def _resolve(self, url: str):
        """Segue i redirect (login, S3 firmato) e ricava la dimensione."""
        try:
            response = self.session.get(
                url, headers={"Range": "bytes=0-0"},
                timeout=HTTP_TIMEOUT, allow_redirects=True, stream=True,
            )
        except requests.RequestException as error:
            raise NightLightsUnavailable(
                f"Archivio NASA non raggiungibile: {error}"
            ) from error

        try:
            if response.status_code in (401, 403):
                raise NightLightsUnavailable(
                    "Accesso NASA Earthdata negato: controlla il token "
                    f"(HTTP {response.status_code})."
                )
            if response.status_code != 206:
                raise NightLightsUnavailable(
                    "Il server NASA non accetta letture parziali "
                    f"(HTTP {response.status_code})."
                )
            content_range = response.headers.get("Content-Range", "")
            match = re.search(r"/(\d+)$", content_range)
            if not match:
                raise NightLightsUnavailable(
                    f"Dimensione del file sconosciuta ({content_range!r})."
                )
            self.requests_made += 1
            original_host = requests.utils.urlparse(url).hostname
            final_host = requests.utils.urlparse(response.url).hostname
            if final_host != original_host:
                # URL firmato (es. S3): va letto SENZA le nostre credenziali.
                self.fetch_session = requests.Session()
            return response.url, int(match.group(1))
        finally:
            response.close()

    # -- interfaccia file ------------------------------------------
    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self.position = offset
        elif whence == io.SEEK_CUR:
            self.position += offset
        elif whence == io.SEEK_END:
            self.position = self.size + offset
        else:
            raise ValueError(f"whence non valido: {whence}")
        self.position = max(self.position, 0)
        return self.position

    def readinto(self, buffer):
        view = memoryview(buffer).cast("B")
        wanted = min(len(view), self.size - self.position)
        if wanted <= 0:
            return 0

        first = self.position // self.block_size
        last = (self.position + wanted - 1) // self.block_size
        self._ensure_blocks(first, last)

        written = 0
        while written < wanted:
            absolute = self.position + written
            index = absolute // self.block_size
            inner = absolute - index * self.block_size
            with self._lock:
                block = self._blocks.get(index)
                if block is not None:
                    self._blocks.move_to_end(index)
            if block is None:           # uscito dalla cache nel frattempo
                self._fetch(index, index)
                continue
            count = min(len(block) - inner, wanted - written)
            view[written:written + count] = block[inner:inner + count]
            written += count

        self.position += written
        return written

    # -- blocchi ---------------------------------------------------
    def _missing_groups(self, indices):
        """Blocchi mancanti raggruppati in intervalli consecutivi [(primo, ultimo)]."""
        with self._lock:
            missing = sorted(i for i in set(indices) if i not in self._blocks)
        groups = []
        for index in missing:
            if groups and index == groups[-1][1] + 1:
                groups[-1][1] = index
            else:
                groups.append([index, index])
        return [tuple(group) for group in groups]

    def _ensure_blocks(self, first: int, last: int):
        for start, end in self._missing_groups(range(first, last + 1)):
            self._fetch(start, end)

    def prefetch(self, byte_ranges, workers: int = PREFETCH_WORKERS):
        """
        Scarica in parallelo i blocchi che coprono gli intervalli di byte
        indicati [(inizio, lunghezza)], prima che h5py li chieda uno a uno.
        """
        indices = set()
        for start, length in byte_ranges:
            if length <= 0:
                continue
            first = start // self.block_size
            last = min(start + length - 1, self.size - 1) // self.block_size
            indices.update(range(first, last + 1))
        if len(indices) > self.max_blocks:
            return  # troppi dati: lasciamo fare a h5py, senza cache piena
        groups = self._missing_groups(indices)
        if not groups:
            return
        if len(groups) == 1:
            self._fetch(*groups[0])
            return
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(workers, len(groups))) as pool:
            for future in [pool.submit(self._fetch, a, b) for a, b in groups]:
                future.result()

    def _fetch(self, first: int, last: int):
        byte0 = first * self.block_size
        byte1 = min((last + 1) * self.block_size, self.size) - 1
        data = None
        for attempt in range(3):
            try:
                response = self.fetch_session.get(
                    self.url, headers={"Range": f"bytes={byte0}-{byte1}"},
                    timeout=HTTP_TIMEOUT,
                )
                with self._lock:
                    self.requests_made += 1
                if response.status_code == 206:
                    data = response.content
                    break
                if response.status_code in (401, 403):
                    raise NightLightsUnavailable(
                        f"Accesso negato durante la lettura (HTTP {response.status_code})."
                    )
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)
        if data is None or len(data) != byte1 - byte0 + 1:
            raise NightLightsUnavailable("Lettura parziale del file NASA non riuscita.")

        with self._lock:
            self.bytes_downloaded += len(data)
            for offset, index in enumerate(range(first, last + 1)):
                chunk = data[offset * self.block_size:(offset + 1) * self.block_size]
                self._blocks[index] = chunk
            while len(self._blocks) > self.max_blocks:
                self._blocks.popitem(last=False)


# ------------------------------------------------------------------
# Lettura della radianza
# ------------------------------------------------------------------

@dataclass
class NightScene:
    """Radianza (nW/cm²/sr, NaN = nessun dato) e maschera del mare."""
    radiance: np.ndarray
    sea: np.ndarray


def chunk_byte_ranges(dataset, rows: slice, cols: slice) -> list:
    """
    Posizione nel file dei blocchi compressi (chunk) che coprono la finestra.
    Serve a scaricarli in parallelo; se non si puo' sapere, lista vuota.
    """
    chunks = dataset.chunks
    if not chunks:
        return []
    ranges = []
    try:
        for row in range(rows.start // chunks[0] * chunks[0], rows.stop, chunks[0]):
            for col in range(cols.start // chunks[1] * chunks[1], cols.stop, chunks[1]):
                info = dataset.id.get_chunk_info_by_coord((row, col))
                if info.byte_offset is not None and info.size:
                    ranges.append((int(info.byte_offset), int(info.size)))
    except Exception:
        return []
    return ranges


def read_tile_window(h5file, rows: slice, cols: slice,
                     remote: HttpRangeFile | None = None) -> NightScene:
    """Legge radianza, qualita' e maschera terra/mare nella finestra del tile."""
    fields = h5file[GRID_PATH]
    dataset = fields[VARIABLE]
    names = [VARIABLE, QUALITY_VARIABLE, LAND_WATER_VARIABLE]
    present = [name for name in names if name in fields]

    if remote is not None:
        byte_ranges = []
        for name in present:
            byte_ranges += chunk_byte_ranges(fields[name], rows, cols)
        remote.prefetch(byte_ranges)

    data = dataset[rows, cols].astype(np.float32)

    fill = dataset.attrs.get("_FillValue")
    if fill is not None:
        fill = float(np.asarray(fill).flat[0])
        data[np.isclose(data, fill)] = np.nan

    if QUALITY_VARIABLE in present:
        quality = fields[QUALITY_VARIABLE][rows, cols]
        data[quality == QUALITY_FILL] = np.nan

    scale = float(np.asarray(dataset.attrs.get("scale_factor", 1.0)).flat[0])
    offset = float(np.asarray(dataset.attrs.get(
        "add_offset", dataset.attrs.get("offset", 0.0))).flat[0])
    data = data * scale + offset
    data[data < 0] = np.nan

    if LAND_WATER_VARIABLE in present:
        sea = fields[LAND_WATER_VARIABLE][rows, cols] == SEA_WATER
    else:
        sea = np.zeros(data.shape, dtype=bool)
    return NightScene(data, sea)


def open_remote_h5(url: str, session: requests.Session):
    import h5py

    remote = HttpRangeFile(url, session)
    return remote, h5py.File(remote, "r")


_array_cache = OrderedDict()
_array_lock = threading.Lock()


def night_scene_for_area(lat: float, lon: float, side_km: float, year: int,
                         session: requests.Session | None = None,
                         stats: dict | None = None) -> NightScene:
    """Radianza e mare sulla finestra dell'area (righe nord->sud)."""
    window = global_window(area_bbox(lat, lon, side_km))
    key = (window, year)
    with _array_lock:
        if key in _array_cache:
            _array_cache.move_to_end(key)
            return _array_cache[key]

    session = session or make_session()
    radiance = np.full(window.shape, np.nan, dtype=np.float32)
    # Tile mancanti nell'archivio = solo oceano: li trattiamo come mare.
    sea = np.ones(window.shape, dtype=bool)
    found_any = False
    for h, v, tile_rows, tile_cols, out_rows, out_cols in tile_pieces(window):
        url = find_granules(h, v).get(year)
        if url is None:
            continue
        found_any = True
        remote, h5file = open_remote_h5(url, session)
        try:
            piece = read_tile_window(h5file, tile_rows, tile_cols, remote)
            radiance[out_rows, out_cols] = piece.radiance
            sea[out_rows, out_cols] = piece.sea
        finally:
            h5file.close()
            if stats is not None:
                stats["bytes"] = stats.get("bytes", 0) + remote.bytes_downloaded
                stats["requests"] = stats.get("requests", 0) + remote.requests_made
                stats["file_size"] = remote.size

    if not found_any:
        raise NightLightsUnavailable(
            f"Nessun dato di luci notturne per il {year} in quest'area."
        )

    scene = NightScene(radiance, sea)
    with _array_lock:
        _array_cache[key] = scene
        while len(_array_cache) > ARRAY_CACHE_SIZE:
            _array_cache.popitem(last=False)
    return scene


# ------------------------------------------------------------------
# Immagine e numeri
# ------------------------------------------------------------------

def _resize(array: np.ndarray, size: int, resample) -> np.ndarray:
    return np.asarray(Image.fromarray(array).resize((size, size), resample))


def resample_square(radiance: np.ndarray, sea: np.ndarray | None = None,
                    size: int = IMAGE_SIZE):
    """
    La griglia e' in gradi: in orizzontale i pixel sono piu' stretti in km.
    Riportiamo l'area a un quadrato (stessi km per lato) con interpolazione
    bilineare dei valori; maschere (dato mancante, mare) con nearest.
    """
    valid = np.isfinite(radiance)
    filled = np.where(valid, radiance, 0).astype(np.float32)
    values = _resize(filled, size, Image.BILINEAR)
    valid_big = _resize(valid.astype(np.uint8) * 255, size, Image.NEAREST) > 0
    if sea is None:
        sea_big = np.zeros((size, size), dtype=bool)
    else:
        sea_big = _resize(sea.astype(np.uint8) * 255, size, Image.NEAREST) > 0
    return values, valid_big, sea_big


def colorize_radiance(radiance: np.ndarray, valid: np.ndarray,
                      sea: np.ndarray | None = None) -> np.ndarray:
    log_values = np.log10(np.clip(radiance, 0.05, None))
    image = colorize(log_values, valid, NIGHT_COLOR_STOPS)
    if sea is not None:
        # Mare scuro in tinta unita (si vede la costa); restano le luci forti.
        image[sea & (radiance < SEA_DARK_RADIANCE)] = NIGHT_SEA_COLOR
    image[~valid] = NIGHT_INVALID_COLOR
    return image


def render_radiance_png(scene: NightScene, size: int = IMAGE_SIZE) -> bytes:
    values, valid, sea = resample_square(scene.radiance, scene.sea, size)
    return to_png(colorize_radiance(values, valid, sea))


def light_summary(scene: NightScene) -> dict:
    """Numeri semplici per confrontare gli anni (solo terraferma)."""
    radiance = scene.radiance
    land = ~scene.sea
    valid = np.isfinite(radiance) & land
    count = int(valid.sum())
    land_count = int(land.sum())
    if count == 0:
        return {"valid_percentage": 0.0, "total_radiance": None,
                "mean_radiance": None, "lit_percentage": None}
    values = radiance[valid]
    return {
        "valid_percentage": round(100.0 * count / max(land_count, 1), 1),
        "total_radiance": round(float(values.sum()), 1),
        "mean_radiance": round(float(values.mean()), 2),
        # Pixel con almeno ~1 nW/cm²/sr: aree con illuminazione artificiale.
        "lit_percentage": round(100.0 * float((values >= 1.0).mean()), 1),
    }


def percent_change(before, after):
    if before is None or after is None or before <= 0:
        return None
    return round(100.0 * (after - before) / before, 1)


def legend() -> dict:
    return {
        "unit": "nW/cm²/sr",
        "scale": "log10",
        # Stesso formato delle altre legende: [[log10(radianza), "#rrggbb"], ...]
        "color_stops": color_stops_hex(NIGHT_COLOR_STOPS),
        "labels": NIGHT_LEGEND_LABELS,
        "sea_color": "#%02x%02x%02x" % NIGHT_SEA_COLOR,
    }
