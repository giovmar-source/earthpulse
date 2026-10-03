# Licenze e uso commerciale delle fonti

Documento interno, generato da `src/sources.py` (`python -c "from src import sources; print(sources.commercial_report())"`).
La pagina pubblica "Crediti e licenze" del sito mostra le stesse fonti senza la colonna sull'uso commerciale.

Prima del lancio a pagamento tutte le righe 🔴 vanno risolte e le 🟡 verificate.

| Fonte | Uso | Licenza | Uso commerciale | Cosa fare |
|---|---|---|---|---|
| Sentinel-2 L2A | Colori reali, indici di vegetazione, acqua, costruito, neve, clorofilla | [Licenza dati Copernicus (libera, anche commerciale)](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice) | ✅ sì | Il catalogo Earth Search è un servizio gratuito senza garanzia di continuità. |
| Landsat 4-9 Collection 2 | Isole di calore, archivio dal 1984 | [Pubblico dominio (USGS)](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits) | ✅ sì | Planetary Computer: verificare i termini d'uso del servizio per un prodotto commerciale. |
| NASA Black Marble (VNP46A4) | Luci notturne | [Dati NASA, uso libero con citazione](https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance) | ✅ sì | Serve un token Earthdata. |
| Blue Marble (globo) | Aspetto realistico del globo | [Dati NASA, uso libero con citazione](https://nasa-gibs.github.io/gibs-api-docs/access-basics/) | ✅ sì | — |
| OpenFreeMap | Mappa di base | [Uso commerciale consentito; dati ODbL](https://openfreemap.org/) | 🟡 con condizioni | Nessuna garanzia di servizio: per la produzione valutare tessere ospitate da noi. |
| Sentinel-5P (NO₂, CH₄, CO) | Gas dal satellite | [Licenza dati Copernicus](https://dataspace.copernicus.eu/terms-and-conditions) | 🟡 con condizioni | Quota gratuita 10 000 richieste al mese; per un servizio a pagamento chiarire con CDSE o passare a CREODIAS/Sentinel Hub a pagamento. |
| Qualità dell'aria CAMS | Qualità dell'aria | [Dati CAMS: CC BY 4.0. Open-Meteo gratuito: solo uso non commerciale](https://open-meteo.com/en/terms) | 🔴 da sostituire prima della vendita | Il server è già pronto: impostare OPENMETEO_API_KEY (piano commerciale) prima della vendita. |
| Meteosat MTG (FCI, LI) | Nuvole, incendi, fulmini, pioggia | [Politica dati EUMETSAT: immagini con almeno 1 ora di ritardo libere](https://www-cdn.eumetsat.int/files/2025-02/45173%20-%20Data_Policy(1442019%20V1).pdf) | 🟡 con condizioni | In vendita impostare EUMETSAT_DELAY_MINUTES=60 (ritardo di 1 ora), oppure licenza da 4 000–8 000 € l'anno. |
| Sentinel-1 GRD | Acqua e allagamenti dal radar | [Licenza dati Copernicus](https://dataspace.copernicus.eu/terms-and-conditions) | 🟡 con condizioni | Stessa quota di Sentinel-5P. |
| NASA POWER | Pioggia e umidità del suolo | [Dati NASA, uso libero con citazione](https://power.larc.nasa.gov/docs/referencing/) | ✅ sì | Massimo 5 richieste contemporanee. |
| NASA FIRMS (VIIRS) | Incendi attivi | [Dati NASA, uso libero anche commerciale](https://www.earthdata.nasa.gov/learn/articles/nasa-earth-science-data-yours-use-fully-and-without-restrictions) | ✅ sì | Chiave gratuita FIRMS_MAP_KEY; 5 000 richieste ogni 10 minuti. |
| NOAA OISST e CoastWatch | Temperatura del mare e clorofilla | [Uso e ridistribuzione liberi; clorofilla CC0](https://coastwatch.pfeg.noaa.gov/erddap/info/ncdcOisst21NrtAgg/index.html) | ✅ sì | — |
| HRL Imperviousness Density 2018 | Suolo impermeabilizzato | [Licenza dati Copernicus (libera, anche commerciale)](https://land.copernicus.eu/en/data-policy) | ✅ sì | — |
| Ricerca dei luoghi | Ricerca per nome e nome del luogo scelto | [Dati ODbL; istanze pubbliche Nominatim/Photon: non per uso commerciale intensivo](https://operations.osmfoundation.org/policies/nominatim/) | 🔴 da sostituire prima della vendita | Il server è già pronto: impostare GEOCODER=geoapify e GEOAPIFY_KEY prima della vendita. |
| Orbite dei satelliti (TLE) | Satelliti in tempo reale | [Dati pubblici (US Space Force via CelesTrak)](https://celestrak.org) | 🟡 con condizioni | Verificare i termini di Space-Track per l'uso commerciale. |
| NASA Planetary Data System | Altitudine, gravità, chimica e magnetismo di Luna, Marte, Mercurio, Venere, Cerere | [Pubblico dominio (NASA)](https://pds.nasa.gov/) | ✅ sì | — |
| NASA Solar System Treks | Mosaici di Mercurio, Venere, Cerere, Vesta, Fobos, Encelado, Titano; Marte notturno | [Contenuti NASA, uso libero con citazione](https://www.nasa.gov/nasa-brand-center/images-and-media/) | ✅ sì | Non usare il logo NASA e non suggerire approvazione della NASA. |
| Solar System Scope | Mappe di Luna, Marte e Giove | [CC BY 4.0](https://www.solarsystemscope.com/textures/) | ✅ sì | — |
| Mosaici delle lune di Giove | Io, Europa, Ganimede, Callisto | [Pubblico dominio](https://astrogeology.usgs.gov/) | ✅ sì | — |
| Gazetteer of Planetary Nomenclature | Nomi dei luoghi su altri corpi | [Pubblico dominio (USGS)](https://planetarynames.wr.usgs.gov/) | ✅ sì | — |
| JPL Small-Body Database e Horizons | Orbite di Cerere e Vesta, posizioni delle sonde | [Dati NASA/JPL, riuso consentito](https://ssd.jpl.nasa.gov/faq.html) | ✅ sì | Servizio senza garanzia: dati in cache. |
| Solar Dynamics Observatory | Il Sole dal vivo | [Immagini non coperte da copyright](https://sdo.gsfc.nasa.gov/data/rules.php) | ✅ sì | — |
| astronomy-engine | Posizioni di pianeti, Luna e lune di Giove | [MIT](https://github.com/cosinekitty/astronomy) | ✅ sì | — |
| Immagini dei satelliti | Schede dei satelliti | [Licenza standard ESA (non commerciale); NASA pubblico dominio](https://www.esa.int/ESA_Multimedia/Copyright_Notice_Images) | 🔴 da sostituire prima della vendita | Sostituire con immagini ESA CC BY-SA 3.0 IGO o chiedere il permesso all'ESA. |
