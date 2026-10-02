# EarthPulse · Fonti

Raccolta delle fonti usate per costruire EarthPulse (dati, servizi, fatti citati nei testi).
Le fonti di ogni evento di **Big Events** sono anche dentro `data/stories.json` e si vedono
nel sito sotto ogni evento; quelle dei dati sono nella **Metodologia** del sito
(`web/src/methodology.js`, sezione "Fonti e attribuzioni").

## Dati satellitari e servizi

| Cosa | Fonte |
|---|---|
| Sentinel-2 L2A (immagini, indici) | [Earth Search STAC (Element 84)](https://earth-search.aws.element84.com/v1) · [ESA SentiWiki](https://sentiwiki.copernicus.eu/web/s2-mission) |
| Landsat 4-9 Collection 2 (calore, archivio) | [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2) |
| Luci notturne VNP46A4 | [NASA Black Marble / LAADS DAAC](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A4/) |
| Qualità dell'aria (CAMS) | [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) |
| Gas Sentinel-5P | [Copernicus Data Space: Sentinel-5P L2](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S5PL2.html) · [Autenticazione](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html) · [Quote](https://documentation.dataspace.copernicus.eu/Quotas.html) |
| Nuvole, incendi, fulmini, pioggia (Meteosat MTG) | [EUMETView, prodotti MTG](https://view.eumetsat.int/geoserver/mtg_fd/ows?service=WMS&request=GetCapabilities) |
| Legenda "Tipo di nubi" | [Guida rapida Cloud Type RGB (EUMETSAT)](https://user.eumetsat.int/s3/eup-strapi-media/QG_Cloud_Type_RGB_ab06957dd1.pdf) · [Guida estesa (EUMETrain)](https://resources.eumetrain.org/data/7/736/navmenu.php?tab=4&page=1.0.0) |
| Orbite (TLE) | [CelesTrak](https://celestrak.org) · [TLE API](https://tle.ivanstanojevic.me) |
| Mappa di base | [OpenFreeMap](https://openfreemap.org) · © OpenStreetMap contributors |
| Globo realistico (Blue Marble) | [NASA GIBS](https://nasa-gibs.github.io/gibs-api-docs/access-basics/) |
| Gas, andamento giornaliero | [Sentinel Hub Statistical API (CDSE)](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Statistical.html) |

## Satelliti (schede)

- Sentinel-2: [ESA Sentinel-2](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2) · [eoPortal](https://www.eoportal.org/satellite-missions/copernicus-sentinel-2)
- Landsat 9: [NASA Science – Landsat 9](https://science.nasa.gov/mission/landsat-9/)
- Suomi NPP: [eoPortal – Suomi NPP](https://www.eoportal.org/satellite-missions/suomi-npp)
- Sentinel-5P: [ESA Sentinel-5P](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-5P)
- Meteosat-12 (MTG-I1): [MTG-I1 – Wikipedia](https://en.wikipedia.org/wiki/MTG-I1) · [Inizio del servizio principale (SpaceDaily)](https://www.spacedaily.com/reports/Meteosat_12_begins_prime_service_delivering_enhanced_weather_data_for_Europe_999.html) · [NORAD 54743 (N2YO)](https://www.n2yo.com/satellite/?s=54743)
- Immagini: ESA/ATG medialab (Licenza standard ESA), NASA (pubblico dominio)

## Oltre la Terra

- Mappe: [Solar System Scope](https://www.solarsystemscope.com/textures/) (CC BY 4.0) · [USGS Astrogeology](https://astrogeology.usgs.gov/) (pubblico dominio)
- Versioni ridimensionate: [amarcher/solar-system, PR #87](https://github.com/amarcher/solar-system/pull/87)
- Calcoli: [astronomy-engine](https://github.com/cosinekitty/astronomy) (MIT)
- Possibili sviluppi: [NASA Moon Trek](https://trek.nasa.gov/moon/index.html) · [Trek API](https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon)

## Big Events

Le fonti di ogni evento sono in `data/stories.json` (campo `sources`). Fonti consultate in più:

- Emilia-Romagna 2023: [Copernicus – Historic floods](https://www.copernicus.eu/en/media/image-day-gallery/historic-floods-hit-emilia-romagna-italy) · [JRC Data Catalogue](https://data.jrc.ec.europa.eu/dataset/63248754-b1a1-4e52-b10e-112fb86dea18)
- Valencia 2024: [Copernicus – Devastating flooding in Valencia](https://www.copernicus.eu/en/media/image-day-gallery/devastating-flooding-valencia-spain)
- Derna 2023: [Derna dam collapses – Wikipedia](https://en.wikipedia.org/wiki/Derna_dam_collapses) · [Science Advances](https://www.science.org/doi/10.1126/sciadv.adu2865)
- Lahaina 2023: [NASA Applied Sciences – Hawaii Wildfires](https://appliedsciences.nasa.gov/what-we-do/disasters/disasters-activations/hawaii-wildfires-aug-2023)
- Hunga Tonga 2022: [Nature – Eruption chronology](https://www.nature.com/articles/s43247-022-00606-3)
- Lago Mead: [NASA JPL – Lake Mead and Drought](https://www.jpl.nasa.gov/images/pia19731-lake-mead-and-drought/)
- Ghiacciaio Columbia: [NASA – Alaskan Ice in Retreat](https://earthobservatory.nasa.gov/images/149445/alaskan-ice-in-retreat-35-years-at-columbia-glacier)

## Analisi del progetto (ottobre 2026)

Licenze, pubblicazione, fisco e dati planetari: vedi `docs/ANALISI_PROGETTO.md`, sezione "Fonti principali".
