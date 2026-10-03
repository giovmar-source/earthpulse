"""
Registro unico delle fonti di dati e servizi usati dal prodotto.

Serve a tre cose:
1. la pagina pubblica "Crediti e licenze" (endpoint /api/v1/credits);
2. il controllo prima della vendita: per ogni fonte lo stato dell'uso commerciale
   ("ok", "condizioni", "da_sostituire") con la nota su cosa fare (docs/LICENZE.md);
3. un solo punto da aggiornare quando una fonte cambia.

Lo stato commerciale è un'informazione interna: la pagina pubblica mostra solo
fornitore, uso, licenza e attribuzione.
"""

from __future__ import annotations

SOURCES = [
    # ---------------------------------------------------------------- Terra: immagini
    {"key": "sentinel2", "group": "Terra · immagini e indici", "name": "Sentinel-2 L2A",
     "provider": "Copernicus (Commissione europea, ESA) tramite Earth Search (Element 84) su AWS",
     "used_for": "Colori reali, indici di vegetazione, acqua, costruito, neve, clorofilla",
     "licence": "Licenza dati Copernicus (libera, anche commerciale)", "licence_url": "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice",
     "attribution": "Contiene dati Copernicus Sentinel modificati [anno]", "commercial": "ok",
     "note": "Il catalogo Earth Search è un servizio gratuito senza garanzia di continuità."},
    {"key": "landsat", "group": "Terra · immagini e indici", "name": "Landsat 4-9 Collection 2",
     "provider": "USGS/NASA tramite Microsoft Planetary Computer",
     "used_for": "Isole di calore, archivio dal 1984",
     "licence": "Pubblico dominio (USGS)", "licence_url": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
     "attribution": "Landsat Collection 2 courtesy of the U.S. Geological Survey", "commercial": "ok",
     "note": "Planetary Computer: verificare i termini d'uso del servizio per un prodotto commerciale."},
    {"key": "blackmarble", "group": "Terra · immagini e indici", "name": "NASA Black Marble (VNP46A4)",
     "provider": "NASA LAADS DAAC", "used_for": "Luci notturne",
     "licence": "Dati NASA, uso libero con citazione", "licence_url": "https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance",
     "attribution": "NASA Black Marble (VNP46A4), LAADS DAAC", "commercial": "ok", "note": "Serve un token Earthdata."},
    {"key": "gibs", "group": "Terra · immagini e indici", "name": "Blue Marble (globo)",
     "provider": "NASA Earth Observatory, NASA GIBS", "used_for": "Aspetto realistico del globo",
     "licence": "Dati NASA, uso libero con citazione", "licence_url": "https://nasa-gibs.github.io/gibs-api-docs/access-basics/",
     "attribution": "Blue Marble: NASA Earth Observatory / NASA EOSDIS GIBS", "commercial": "ok", "note": ""},
    {"key": "openfreemap", "group": "Terra · immagini e indici", "name": "OpenFreeMap",
     "provider": "OpenFreeMap, dati OpenStreetMap", "used_for": "Mappa di base",
     "licence": "Uso commerciale consentito; dati ODbL", "licence_url": "https://openfreemap.org/",
     "attribution": "© OpenMapTiles · Dati © OpenStreetMap contributors", "commercial": "condizioni",
     "note": "Nessuna garanzia di servizio: per la produzione valutare tessere ospitate da noi."},
    # ---------------------------------------------------------------- Terra: atmosfera
    {"key": "s5p", "group": "Terra · atmosfera", "name": "Sentinel-5P (NO₂, CH₄, CO)",
     "provider": "Copernicus Data Space Ecosystem (Sentinel Hub)", "used_for": "Gas dal satellite",
     "licence": "Licenza dati Copernicus", "licence_url": "https://dataspace.copernicus.eu/terms-and-conditions",
     "attribution": "Contiene dati Copernicus Sentinel-5P modificati, elaborati con Copernicus Data Space Ecosystem",
     "commercial": "condizioni", "note": "Quota gratuita 10 000 richieste al mese; per un servizio a pagamento chiarire con CDSE o passare a CREODIAS/Sentinel Hub a pagamento."},
    {"key": "cams", "group": "Terra · atmosfera", "name": "Qualità dell'aria CAMS",
     "provider": "Copernicus Atmosphere Monitoring Service tramite Open-Meteo", "used_for": "Qualità dell'aria",
     "licence": "Dati CAMS: CC BY 4.0. Open-Meteo gratuito: solo uso non commerciale", "licence_url": "https://open-meteo.com/en/terms",
     "attribution": "Copernicus Atmosphere Monitoring Service (CAMS) · Open-Meteo.com", "commercial": "da_sostituire",
     "note": "Il server è già pronto: impostare OPENMETEO_API_KEY (piano commerciale) prima della vendita."},
    {"key": "eumetsat", "group": "Terra · atmosfera", "name": "Meteosat MTG (FCI, LI)",
     "provider": "EUMETSAT (EUMETView)", "used_for": "Nuvole, incendi, fulmini, pioggia",
     "licence": "Politica dati EUMETSAT: immagini con almeno 1 ora di ritardo libere", "licence_url": "https://www-cdn.eumetsat.int/files/2025-02/45173%20-%20Data_Policy(1442019%20V1).pdf",
     "attribution": "Contiene dati EUMETSAT Meteosat modificati [anno]", "commercial": "condizioni",
     "note": "In vendita impostare EUMETSAT_DELAY_MINUTES=60 (ritardo di 1 ora), oppure licenza da 4 000–8 000 € l'anno."},
    # ---------------------------------------------------------------- Terra: acqua, fuoco, suolo
    {"key": "sentinel1", "group": "Terra · acqua, fuoco e suolo", "name": "Sentinel-1 GRD",
     "provider": "Copernicus Data Space Ecosystem (Sentinel Hub)", "used_for": "Acqua e allagamenti dal radar",
     "licence": "Licenza dati Copernicus", "licence_url": "https://dataspace.copernicus.eu/terms-and-conditions",
     "attribution": "Contiene dati Copernicus Sentinel-1 modificati, elaborati con Copernicus Data Space Ecosystem",
     "commercial": "condizioni", "note": "Stessa quota di Sentinel-5P."},
    {"key": "power", "group": "Terra · acqua, fuoco e suolo", "name": "NASA POWER",
     "provider": "NASA Langley Research Center", "used_for": "Pioggia e umidità del suolo",
     "licence": "Dati NASA, uso libero con citazione", "licence_url": "https://power.larc.nasa.gov/docs/referencing/",
     "attribution": "NASA Langley Research Center, progetto POWER, finanziato dalla NASA Earth Science Division",
     "commercial": "ok", "note": "Massimo 5 richieste contemporanee."},
    {"key": "firms", "group": "Terra · acqua, fuoco e suolo", "name": "NASA FIRMS (VIIRS)",
     "provider": "NASA LANCE / EOSDIS", "used_for": "Incendi attivi",
     "licence": "Dati NASA, uso libero anche commerciale", "licence_url": "https://www.earthdata.nasa.gov/learn/articles/nasa-earth-science-data-yours-use-fully-and-without-restrictions",
     "attribution": "NASA FIRMS, LANCE / NASA EOSDIS", "commercial": "ok", "note": "Chiave gratuita FIRMS_MAP_KEY; 5 000 richieste ogni 10 minuti."},
    {"key": "noaa_sea", "group": "Terra · acqua, fuoco e suolo", "name": "NOAA OISST e CoastWatch",
     "provider": "NOAA (ERDDAP CoastWatch)", "used_for": "Temperatura del mare e clorofilla",
     "licence": "Uso e ridistribuzione liberi; clorofilla CC0", "licence_url": "https://coastwatch.pfeg.noaa.gov/erddap/info/ncdcOisst21NrtAgg/index.html",
     "attribution": "NOAA OISST v2.1 · NOAA CoastWatch (VIIRS, OLCI, DINEOF)", "commercial": "ok", "note": ""},
    {"key": "hrl", "group": "Terra · acqua, fuoco e suolo", "name": "HRL Imperviousness Density 2018",
     "provider": "Copernicus Land Monitoring Service (Agenzia europea dell'ambiente)", "used_for": "Suolo impermeabilizzato",
     "licence": "Licenza dati Copernicus (libera, anche commerciale)", "licence_url": "https://land.copernicus.eu/en/data-policy",
     "attribution": "Generato con informazioni del Copernicus Land Monitoring Service dell'Unione europea",
     "commercial": "ok", "note": ""},
    # ---------------------------------------------------------------- Servizi
    {"key": "geocoding", "group": "Servizi", "name": "Ricerca dei luoghi",
     "provider": "Nominatim e Photon (OpenStreetMap), oppure Geoapify", "used_for": "Ricerca per nome e nome del luogo scelto",
     "licence": "Dati ODbL; istanze pubbliche Nominatim/Photon: non per uso commerciale intensivo", "licence_url": "https://operations.osmfoundation.org/policies/nominatim/",
     "attribution": "Dati © OpenStreetMap contributors", "commercial": "da_sostituire",
     "note": "Il server è già pronto: impostare GEOCODER=geoapify e GEOAPIFY_KEY prima della vendita."},
    {"key": "tle", "group": "Servizi", "name": "Orbite dei satelliti (TLE)",
     "provider": "CelesTrak, TLE API", "used_for": "Satelliti in tempo reale",
     "licence": "Dati pubblici (US Space Force via CelesTrak)", "licence_url": "https://celestrak.org",
     "attribution": "Elementi orbitali: CelesTrak", "commercial": "condizioni", "note": "Verificare i termini di Space-Track per l'uso commerciale."},
    # ---------------------------------------------------------------- Oltre la Terra
    {"key": "pds", "group": "Oltre la Terra", "name": "NASA Planetary Data System",
     "provider": "PDS Geosciences Node, PDS Small Bodies Node", "used_for": "Altitudine, gravità, chimica e magnetismo di Luna, Marte, Mercurio, Venere, Cerere",
     "licence": "Pubblico dominio (NASA)", "licence_url": "https://pds.nasa.gov/",
     "attribution": "NASA Planetary Data System (team delle singole missioni citati in ogni mappa)", "commercial": "ok", "note": ""},
    {"key": "trek", "group": "Oltre la Terra", "name": "NASA Solar System Treks",
     "provider": "NASA/JPL", "used_for": "Mosaici di Mercurio, Venere, Cerere, Vesta, Fobos, Encelado, Titano; Marte notturno",
     "licence": "Contenuti NASA, uso libero con citazione", "licence_url": "https://www.nasa.gov/nasa-brand-center/images-and-media/",
     "attribution": "NASA Solar System Treks (team delle missioni citati in ogni mappa)", "commercial": "ok",
     "note": "Non usare il logo NASA e non suggerire approvazione della NASA."},
    {"key": "sss", "group": "Oltre la Terra", "name": "Solar System Scope",
     "provider": "INOVE", "used_for": "Mappe di Luna, Marte e Giove", "licence": "CC BY 4.0",
     "licence_url": "https://www.solarsystemscope.com/textures/", "attribution": "Mappe: Solar System Scope (CC BY 4.0)", "commercial": "ok", "note": ""},
    {"key": "usgs_moons", "group": "Oltre la Terra", "name": "Mosaici delle lune di Giove",
     "provider": "NASA/JPL/USGS Astrogeology", "used_for": "Io, Europa, Ganimede, Callisto",
     "licence": "Pubblico dominio", "licence_url": "https://astrogeology.usgs.gov/", "attribution": "NASA/JPL/USGS Astrogeology", "commercial": "ok", "note": ""},
    {"key": "gazetteer", "group": "Oltre la Terra", "name": "Gazetteer of Planetary Nomenclature",
     "provider": "IAU WGPSN, USGS Astrogeology", "used_for": "Nomi dei luoghi su altri corpi", "licence": "Pubblico dominio (USGS)",
     "licence_url": "https://planetarynames.wr.usgs.gov/", "attribution": "IAU WGPSN, Gazetteer of Planetary Nomenclature (USGS)", "commercial": "ok", "note": ""},
    {"key": "jpl", "group": "Oltre la Terra", "name": "JPL Small-Body Database e Horizons",
     "provider": "NASA/JPL Solar System Dynamics", "used_for": "Orbite di Cerere e Vesta, posizioni delle sonde",
     "licence": "Dati NASA/JPL, riuso consentito", "licence_url": "https://ssd.jpl.nasa.gov/faq.html",
     "attribution": "NASA/JPL Solar System Dynamics", "commercial": "ok", "note": "Servizio senza garanzia: dati in cache."},
    {"key": "sdo", "group": "Oltre la Terra", "name": "Solar Dynamics Observatory",
     "provider": "NASA/SDO", "used_for": "Il Sole dal vivo", "licence": "Immagini non coperte da copyright",
     "licence_url": "https://sdo.gsfc.nasa.gov/data/rules.php", "attribution": "Courtesy of NASA/SDO and the AIA, EVE, and HMI science teams.", "commercial": "ok", "note": ""},
    {"key": "astronomy_engine", "group": "Oltre la Terra", "name": "astronomy-engine",
     "provider": "Don Cross", "used_for": "Posizioni di pianeti, Luna e lune di Giove", "licence": "MIT",
     "licence_url": "https://github.com/cosinekitty/astronomy", "attribution": "astronomy-engine (MIT)", "commercial": "ok", "note": ""},
    # ---------------------------------------------------------------- Immagini delle schede
    {"key": "esa_images", "group": "Immagini delle schede", "name": "Immagini dei satelliti",
     "provider": "ESA/ATG medialab, NASA", "used_for": "Schede dei satelliti", "licence": "Licenza standard ESA (non commerciale); NASA pubblico dominio",
     "licence_url": "https://www.esa.int/ESA_Multimedia/Copyright_Notice_Images", "attribution": "ESA/ATG medialab · NASA", "commercial": "da_sostituire",
     "note": "Sostituire con immagini ESA CC BY-SA 3.0 IGO o chiedere il permesso all'ESA."},
]

PUBLIC_FIELDS = ("key", "group", "name", "provider", "used_for", "licence", "licence_url", "attribution")


def public() -> list:
    return [{k: s[k] for k in PUBLIC_FIELDS} for s in SOURCES]


def commercial_report() -> str:
    """Tabella Markdown per docs/LICENZE.md (uso interno)."""
    label = {"ok": "✅ sì", "condizioni": "🟡 con condizioni", "da_sostituire": "🔴 da sostituire prima della vendita"}
    lines = ["| Fonte | Uso | Licenza | Uso commerciale | Cosa fare |", "|---|---|---|---|---|"]
    for s in SOURCES:
        lines.append(f"| {s['name']} | {s['used_for']} | [{s['licence']}]({s['licence_url']}) | "
                     f"{label[s['commercial']]} | {s['note'] or '—'} |")
    return "\n".join(lines)
