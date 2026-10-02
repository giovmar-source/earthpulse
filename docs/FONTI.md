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
- Altitudine Luna: [LRO LOLA LDEM_4 (PDS)](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_4.lbl) · pubblico dominio
- Altitudine Marte: [MGS MOLA MEGDR 4 ppd (PDS)](https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg004/megt90n000cb.lbl) · pubblico dominio
- Marte di notte all'infrarosso: [THEMIS Night IR, Mars Trek](https://trek.nasa.gov/tiles/Mars/EQ/THEMIS_NightIR_ControlledMosaics_100m_v2_oct2018/1.0.0/WMTSCapabilities.xml) (NASA/JPL/ASU)
- Catalogo e API: [NASA Moon Trek](https://trek.nasa.gov/moon/index.html) · [Trek API](https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon) · [ricerca prodotti Trek](https://trek.nasa.gov/moon/TrekServices/ws/index/eq/searchItems?start=0&rows=60&key=Diviner)
- Uso dei contenuti NASA: [NASA Images and Media Usage Guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/) (citare NASA come fonte, non suggerire che NASA approvi il prodotto)
- Luna, Lunar Prospector (torio, ferro, idrogeno, 0,5°): [prodotti speciali PDS](https://pds-geosciences.wustl.edu/missions/lunarp/reduced_special.html)
- Luna, gravità GRAIL: [GRGM660PRIM, anomalia in aria libera](https://pds-geosciences.wustl.edu/grail/grail-l-lgrs-5-rdr-v1/grail_1001/rsdmap/gggrx_0660pm_anom_l320.lbl)
- Marte, acqua (Mars Odyssey GRS): [elementi, PDS](https://pds-geosciences.wustl.edu/missions/odyssey/grs_elements.html)
- Marte, inerzia termica (MGS TES): [prodotti speciali TES](https://pds-geosciences.wustl.edu/missions/mgs/tesspecial.html)
- Marte, campo magnetico crostale (MGS MAG/ER): [Connerney et al. 2001, dati](https://mgs-mager.gsfc.nasa.gov/publications/grl_28_connerney/data/grl_28_connerney_data.html)
- Mercurio, Mg/Si (MESSENGER XRS): [mappe XRS, PDS](https://pds.nasa.gov/ds-view/pds/viewProfile.jsp?dsid=MESS-H-XRS-3-RDR-MAPS-V1.0)
- Cerere, idrogeno (Dawn GRaND): [mappe GRaND, PDS Small Bodies Node](https://sbn.psi.edu/pds/resource/dawn/dwncgrdmaps.html)
- Mosaici Trek: Mercurio MESSENGER MDIS (MD3Color, EnhancedColor), Venere Magellan C3-MDIR, Cerere Dawn FC (DLR), Vesta Dawn HAMO TrueClr (DLR), Fobos Viking (DLR), Encelado (P. Schenk, LPI), Titano Cassini ISS 938 nm (E. Karkoschka): [portale Trek](https://trek.nasa.gov/)
- Non usati, perché i metadati Trek non danno la scala dei colori in numeri: Diviner (temperatura), Clementine FeO, Kaguya (gravità), rilievi a colori di Trek. Non trovati su Trek: lune minori di Saturno, Plutone, Caronte, Tritone, Callisto

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
