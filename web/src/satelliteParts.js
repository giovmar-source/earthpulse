// Parti dei satelliti, punti numerati sulle immagini (frazioni 0..1 di
// larghezza e altezza; null = non visibile in quella vista).
// Stessi testi della schermata "Satelliti" dell'app Android.

export const SATELLITE_PARTS = {
  "sentinel-2": {
    "images": [
      {
        "label": "Esterno",
        "src": "img/sentinel2_exterior.jpg",
        "caption": "Sentinel-2 in orbita: a sinistra lo strumento nella coperta isolante dorata, a destra la piattaforma con l'ala del pannello solare.",
        "credit": "Immagine: ESA/ATG medialab · Licenza standard ESA"
      },
      {
        "label": "Interno",
        "src": "img/sentinel2_interior.jpg",
        "caption": "Vista interna, con le pareti della piattaforma aperte: al centro il serbatoio, a destra la struttura dello strumento con i sensori stellari sopra.",
        "credit": "Immagine: ESA/ATG medialab · Licenza standard ESA"
      }
    ],
    "parts": [
      {
        "number": 1,
        "name": "Piattaforma",
        "role": "Il \"telaio\" che porta tutto: struttura, computer di bordo, energia, controllo termico.",
        "color": "#D5DBE0",
        "spots": [
          [
            0.521,
            0.407
          ],
          [
            0.383,
            0.28
          ]
        ],
        "description": "Sentinel-2 usa la piattaforma AstroBus-L di Airbus Defence and Space; il prime contractor è Airbus DS di Friedrichshafen (Germania). La piattaforma ospita il computer di bordo, la distribuzione dell'energia, i cablaggi e i sistemi termici che tengono ogni apparato nel suo intervallo di temperatura.",
        "facts": [
          [
            "Massa al lancio",
            "1140 kg"
          ],
          [
            "Dimensioni",
            "3,4 × 1,8 × 2,35 m"
          ],
          [
            "Vita di progetto",
            "7,25 anni"
          ],
          [
            "Batterie e carburante",
            "per 12 anni"
          ],
          [
            "Controllo missione",
            "ESOC, Darmstadt"
          ]
        ],
        "info": "Riusare una piattaforma già qualificata riduce rischi, costi e tempi: si progetta da zero solo ciò che la missione richiede davvero, qui lo strumento. La vita di progetto è 7,25 anni, ma batterie e carburante sono dimensionati per 12: è questo margine che oggi permette missioni estese, come la campagna di Sentinel-2A iniziata nel 2025.",
        "inEarthPulse": null
      },
      {
        "number": 2,
        "name": "Strumento MSI",
        "role": "La fotocamera multispettrale: tutto il resto del satellite esiste per lei.",
        "color": "#EEF1F3",
        "spots": [
          [
            0.354,
            0.4
          ],
          [
            0.68,
            0.56
          ]
        ],
        "description": "Il Multi-Spectral Instrument è un telescopio a tre specchi (TMA) che raccoglie la luce riflessa dalla Terra e la divide in 13 bande, dal blu all'infrarosso a onde corte. Due piani focali la misurano: uno per visibile e vicino infrarosso (VNIR), uno per l'infrarosso a onde corte (SWIR), ciascuno con 12 rivelatori sfalsati su due file per coprire 290 km di larghezza.",
        "facts": [
          [
            "Bande",
            "13 (4 a 10 m, 6 a 20 m, 3 a 60 m)"
          ],
          [
            "Larghezza ripresa",
            "290 km"
          ],
          [
            "Specchi",
            "carburo di silicio (SiC)"
          ],
          [
            "Rivelatori",
            "VNIR CMOS · SWIR MCT"
          ],
          [
            "SWIR raffreddato",
            "sotto 210 K (−63 °C)"
          ],
          [
            "Massa · potenza",
            "~290 kg · < 266 W"
          ]
        ],
        "info": "Il requisito di partenza è rivedere ogni punto delle terre emerse ogni 5 giorni con due satelliti: da 786 km servono 290 km di larghezza, un campo visivo enorme per un telescopio. Il TMA usa solo specchi, quindi non ha aberrazioni cromatiche e resta nitido su tutto il campo in tutte le 13 bande. Il carburo di silicio è rigido, leggero e si deforma poco con la temperatura, che cambia a ogni passaggio tra luce e ombra. I rivelatori SWIR vanno raffreddati per ridurre il rumore termico.",
        "inEarthPulse": "EarthPulse usa le bande B02-B03-B04 per i colori reali, B08 e B04 per l'NDVI, B03 per l'acqua, B11 per umidità e costruito, B12 per gli incendi. Le file di rivelatori sfalsate vedono ogni punto con angoli leggermente diversi: l'elaborazione a terra (livello 1C) riallinea le bande sulla stessa griglia."
      },
      {
        "number": 3,
        "name": "Pannello solare",
        "role": "Produce l'energia per tutto il satellite.",
        "color": "#26467F",
        "spots": [
          [
            0.755,
            0.555
          ],
          null
        ],
        "description": "Un'ala di pannelli fotovoltaici, aperta dopo il lancio, alimenta il satellite e ricarica le batterie agli ioni di litio. In una parte di ogni orbita il satellite è nell'ombra della Terra e vive solo con le batterie.",
        "facts": [
          [
            "Superficie",
            "7,1 m²"
          ],
          [
            "Potenza a inizio vita",
            "2300 W"
          ],
          [
            "Potenza a fine vita",
            "1730 W"
          ],
          [
            "Batteria",
            "ioni di litio, 102 Ah a fine vita"
          ]
        ],
        "info": "Si dimensiona sul caso peggiore: fine vita (le celle perdono efficienza con le radiazioni), eclisse e massimo consumo durante ripresa e trasmissione. Per questo a inizio missione la potenza (2300 W) è ben più alta di quella garantita alla fine (1730 W). La batteria va dimensionata per l'ombra, ma anche per il numero di cicli: un ciclo di carica e scarica a ogni orbita, per anni.",
        "inEarthPulse": null
      },
      {
        "number": 4,
        "name": "Controllo d'assetto",
        "role": "Sa dove si trova e dove punta, e corregge l'orientamento.",
        "color": "#6D8FA0",
        "spots": [
          [
            0.339,
            0.215
          ],
          [
            0.651,
            0.35
          ]
        ],
        "description": "Tre sensori stellari (star tracker) riconoscono le stelle e danno l'orientamento; giroscopi a fibra ottica misurano le rotazioni; un ricevitore GPS a doppia frequenza dà posizione e ora. Quattro ruote di reazione fanno ruotare il satellite e tre magnetotorquer sfruttano il campo magnetico terrestre.",
        "facts": [
          [
            "Star tracker",
            "3"
          ],
          [
            "Ruote di reazione",
            "4"
          ],
          [
            "Magnetotorquer",
            "3"
          ],
          [
            "GPS",
            "doppia frequenza (L1/L2)"
          ],
          [
            "Geolocalizzazione",
            "~20 m senza punti a terra"
          ]
        ],
        "info": "Per controllare tre assi bastano tre ruote: la quarta è ridondanza, così un guasto non ferma la missione. Le ruote assorbono le piccole coppie di disturbo accumulando velocità; i magnetotorquer le \"scaricano\" senza consumare carburante. La precisione di assetto e posizione decide quanto bene ogni pixel cade sul punto giusto della Terra.",
        "inEarthPulse": "È questa precisione che permette a EarthPulse di sovrapporre due date pixel per pixel sulla stessa griglia, nel cursore prima/dopo."
      },
      {
        "number": 5,
        "name": "Propulsione",
        "role": "Piccoli motori per mantenere l'orbita e, a fine vita, abbassarla.",
        "color": "#C0633F",
        "spots": [
          null,
          [
            0.432,
            0.5
          ]
        ],
        "description": "Un sistema a monopropellente: l'idrazina passa su un catalizzatore e si decompone in gas caldo, senza bisogno di un ossidante. I propulsori da 1 N correggono l'orbita per mantenere la traccia a terra ripetibile, evitano i detriti spaziali e a fine missione abbassano l'orbita.",
        "facts": [
          [
            "Propellente",
            "120 kg di idrazina"
          ],
          [
            "Propulsori",
            "1 N"
          ],
          [
            "Usi",
            "orbita, detriti, fine vita"
          ]
        ],
        "info": "Il monopropellente è la soluzione più semplice e affidabile: un solo fluido e nessuna combustione da regolare. Il carburante non si può ricaricare: insieme alle batterie fissa la durata massima della missione. Una parte è riservata alla fine vita, per ridurre il tempo che il satellite passerà in orbita da spento e quindi il rischio di detriti.",
        "inEarthPulse": null
      },
      {
        "number": 6,
        "name": "Comunicazioni",
        "role": "Comandi dalla Terra, immagini verso la Terra.",
        "color": "#8B6BBE",
        "spots": [
          [
            0.469,
            0.215
          ],
          [
            0.484,
            0.36
          ]
        ],
        "description": "La banda S porta i telecomandi e la telemetria, cioè lo stato di salute del satellite. Le immagini scendono in banda X verso le stazioni di terra, oppure passano con un terminale laser ai satelliti europei EDRS in orbita geostazionaria, che le ritrasmettono a terra.",
        "facts": [
          [
            "Banda S",
            "64 kbit/s su · 2 Mbit/s giù"
          ],
          [
            "Banda X",
            "560 Mbit/s"
          ],
          [
            "Memoria di bordo",
            "2,4 Tbit"
          ],
          [
            "Dati al giorno",
            "~1,6 TB compressi"
          ],
          [
            "Stazioni",
            "Kiruna, Matera, Maspalomas, Svalbard"
          ]
        ],
        "info": "È un problema di bilancio dei dati: lo strumento produce più di quanto si possa scaricare in continuo, e ogni stazione è visibile solo pochi minuti per orbita. Si comprime a bordo, si memorizza e si scarica ai passaggi; il relè laser via EDRS aggiunge occasioni di scarico. Comandi e immagini viaggiano su canali separati: se la catena dei dati ha un problema, il satellite resta controllabile.",
        "inEarthPulse": null
      },
      {
        "number": 7,
        "name": "Orbita",
        "role": "Non è un pezzo, ma è la prima scelta di progetto.",
        "color": "#3FA37A",
        "spots": [
          null,
          null
        ],
        "description": "Orbita eliosincrona a 786 km con inclinazione di 98,62°: il satellite passa sopra ogni luogo sempre alla stessa ora locale, le 10:30 del mattino. Un giro dura 101 minuti; un satellite rivede lo stesso punto ogni 10 giorni, due satelliti sfasati ogni 5.",
        "facts": [
          [
            "Quota",
            "786 km"
          ],
          [
            "Inclinazione",
            "98,62°"
          ],
          [
            "Ora di passaggio",
            "10:30 (nodo discendente)"
          ],
          [
            "Periodo",
            "101 min"
          ],
          [
            "Rivisita",
            "10 giorni (1 sat.) · 5 giorni (2 sat.)"
          ],
          [
            "Lanci",
            "2A 2015 · 2B 2017 · 2C 2024"
          ]
        ],
        "info": "Le 10:30 sono un compromesso: il Sole è già abbastanza alto da dare buona luce e ombre non troppo lunghe, ma è presto rispetto alle nuvole che si formano nelle ore più calde. L'orbita decide la larghezza di ripresa necessaria, quindi lo strumento, i dati, l'energia: tutto il resto discende da qui. Dal 21 gennaio 2025 Sentinel-2C ha preso il posto di 2A, che continua con una campagna estesa.",
        "inEarthPulse": "Per questo la timeline di EarthPulse confronta scene della stessa stagione: stessa ora del giorno e luce il più simile possibile."
      }
    ],
    "overview": "Un satellite è un sistema: ogni parte esiste per servire la missione. Si parte dal requisito (vedere ogni punto delle terre emerse ogni 5 giorni, fino a 10 m, in 13 bande) e ogni scelta ne discende: l'orbita fissa la larghezza di ripresa; larghezza e risoluzione fissano quanti dati si producono; i dati fissano memoria e antenne; tutto insieme fissa l'energia, e l'energia il pannello e le batterie. Tocca un numero sull'immagine per vedere come.",
    "sources": "Fonti dei dati: ESA (Sentinel-2 operations; SentiWiki, S2 Mission) ed eoPortal (Copernicus: Sentinel-2)."
  },
  "landsat": {
    "images": [
      {
        "label": "Esterno",
        "src": "img/landsat9.jpg",
        "caption": "Landsat 9 in orbita: a sinistra gli strumenti rivolti verso la Terra, a destra la grande ala del pannello solare.",
        "credit": "Immagine: NASA · pubblico dominio"
      }
    ],
    "parts": [
      {
        "number": 1,
        "name": "Piattaforma",
        "role": "Il satellite \"gemello\" di Landsat 8, costruito per dare continuità all'archivio.",
        "color": "#D5DBE0",
        "spots": [
          [
            0.22,
            0.5
          ],
          null
        ],
        "description": "Landsat 9 è stato progettato e costruito da Northrop Grumman sulla piattaforma LEOStar-3 ed è stato lanciato il 27 settembre 2021 con un razzo Atlas V 401 da Vandenberg, in California. È gestito da NASA e USGS.",
        "facts": [
          [
            "Lancio",
            "27 settembre 2021, Atlas V 401"
          ],
          [
            "Costruttore",
            "Northrop Grumman (LEOStar-3)"
          ],
          [
            "Vita di progetto",
            "5 anni"
          ],
          [
            "Consumabili",
            "per 10 anni"
          ],
          [
            "Scene al giorno",
            "circa 740"
          ]
        ],
        "info": "Landsat 9 è molto simile a Landsat 8, per scelta: riusare un progetto già collaudato riduce rischi e tempi e, soprattutto, garantisce che i dati di oggi siano confrontabili con quelli di ieri. Per un archivio che copre decenni la continuità conta più della novità.",
        "inEarthPulse": null
      },
      {
        "number": 2,
        "name": "Strumento OLI-2",
        "role": "La fotocamera multispettrale: dal visibile all'infrarosso a onde corte.",
        "color": "#EEF1F3",
        "spots": [
          [
            0.155,
            0.57
          ],
          null
        ],
        "description": "L'Operational Land Imager 2 riprende una striscia larga 185 km in 9 bande, dal visibile all'infrarosso a onde corte, con pixel di 30 m (15 m per la banda pancromatica, in bianco e nero).",
        "facts": [
          [
            "Bande",
            "9"
          ],
          [
            "Risoluzione",
            "30 m (pancromatica 15 m)"
          ],
          [
            "Larghezza ripresa",
            "185 km"
          ],
          [
            "Precisione dei valori",
            "14 bit"
          ]
        ],
        "info": "14 bit significano 16.384 livelli per ogni pixel: più sfumature sia nelle zone molto scure, come l'acqua, sia in quelle molto chiare, come neve e deserti. Le bande sono scelte per restare compatibili con i Landsat precedenti.",
        "inEarthPulse": "Nella sezione \"Nel tempo\" le immagini degli ultimi anni vengono da OLI e OLI-2; quelle degli anni '80 e '90 dal suo antenato TM, su Landsat 5."
      },
      {
        "number": 3,
        "name": "Strumento TIRS-2",
        "role": "Il termometro: misura il calore emesso dalle superfici.",
        "color": "#E07A4F",
        "spots": [
          null,
          null
        ],
        "description": "Il Thermal Infrared Sensor 2 misura la radiazione termica in 2 bande dell'infrarosso, con pixel di 100 m (distribuiti ricampionati a 30 m).",
        "facts": [
          [
            "Bande termiche",
            "2"
          ],
          [
            "Risoluzione",
            "100 m (distribuita a 30 m)"
          ],
          [
            "Larghezza ripresa",
            "185 km"
          ]
        ],
        "info": "Il calore ha lunghezze d'onda molto più lunghe della luce visibile: a parità di telescopio i dettagli sono più grossolani e i rivelatori devono essere raffreddati per non \"vedere\" il proprio calore. Per questo il termico ha pixel di 100 m mentre OLI-2 arriva a 30 m.",
        "inEarthPulse": "Le isole di calore di EarthPulse usano la temperatura delle superfici calcolata da TIRS e TIRS-2."
      },
      {
        "number": 4,
        "name": "Pannello solare",
        "role": "Produce l'energia per il satellite.",
        "color": "#26467F",
        "spots": [
          [
            0.515,
            0.39
          ],
          null
        ],
        "description": "Un'unica grande ala di pannelli fotovoltaici, orientata verso il Sole, alimenta strumenti e piattaforma e ricarica le batterie per la parte di orbita passata nell'ombra della Terra.",
        "facts": [],
        "info": "Un'ala sola su un lato è la soluzione più semplice e leggera per un satellite che guarda sempre la Terra: l'ala ruota per seguire il Sole mentre il corpo resta puntato verso il basso.",
        "inEarthPulse": null
      },
      {
        "number": 5,
        "name": "Orbita",
        "role": "Stessa orbita di Landsat 8, sfasata di mezzo ciclo.",
        "color": "#3FA37A",
        "spots": [
          null,
          null
        ],
        "description": "Orbita eliosincrona a 705 km: Landsat 9 passa sopra l'equatore verso le 10:12 del mattino, ora locale. Da solo rivede lo stesso punto ogni 16 giorni; insieme a Landsat 8 ogni 8.",
        "facts": [
          [
            "Quota",
            "705 km"
          ],
          [
            "Ora di passaggio",
            "circa 10:12 (nodo discendente)"
          ],
          [
            "Rivisita",
            "16 giorni · 8 con Landsat 8"
          ],
          [
            "Archivio Landsat",
            "dal 1972"
          ]
        ],
        "info": "L'orbita riprende quella dei Landsat precedenti: stessa quota e stessa griglia di passaggi a terra, così le immagini di anni diversi si sovrappongono e l'archivio resta coerente.",
        "inEarthPulse": null
      }
    ],
    "overview": "Landsat osserva le terre emerse dal 1972: è l'archivio satellitare più lungo al mondo. Landsat 9 lavora in coppia con Landsat 8 e porta due strumenti: OLI-2 per la luce riflessa e TIRS-2 per il calore. Tocca un numero sull'immagine.",
    "sources": "Fonti dei dati: NASA Science (Landsat 9). TIRS-2 non ha un punto sull'immagine: lo trovi nell'elenco."
  },
  "suomi-npp": {
    "images": [
      {
        "label": "Esterno",
        "src": "img/suomi_npp.jpg",
        "caption": "Suomi NPP: il corpo dorato della piattaforma con gli strumenti, le antenne e, a destra, l'ala del pannello solare.",
        "credit": "Immagine: NASA · pubblico dominio"
      }
    ],
    "parts": [
      {
        "number": 1,
        "name": "Piattaforma",
        "role": "Satellite meteorologico e climatico di NASA e NOAA.",
        "color": "#D9A441",
        "spots": [
          [
            0.44,
            0.32
          ],
          null
        ],
        "description": "Suomi NPP porta il nome del meteorologo Verner Suomi. Costruito da Ball Aerospace sulla piattaforma BCP-2000, è stato lanciato il 28 ottobre 2011 con un razzo Delta II. Oltre a VIIRS porta altri quattro strumenti per meteo e clima: CrIS, ATMS, OMPS e CERES.",
        "facts": [
          [
            "Lancio",
            "28 ottobre 2011, Delta II"
          ],
          [
            "Massa al lancio",
            "circa 2,1 t"
          ],
          [
            "Piattaforma",
            "Ball BCP-2000"
          ],
          [
            "Vita di progetto",
            "5 anni (consumabili per 7)"
          ],
          [
            "Distribuzione dati",
            "NOAA la interrompe dal 1° novembre 2026"
          ]
        ],
        "info": "Progettato per 5 anni, ha lavorato per oltre 14: i margini su carburante e componenti si trasformano in anni di dati in più. Ora il suo lavoro passa a NOAA-20 e NOAA-21, che portano copie aggiornate degli stessi strumenti.",
        "inEarthPulse": "Le luci notturne di EarthPulse vengono da Suomi NPP (dal 2012). Per gli anni futuri useremo gli stessi prodotti ricavati da NOAA-20."
      },
      {
        "number": 2,
        "name": "Strumento VIIRS",
        "role": "Vede tutta la Terra ogni giorno, anche di notte.",
        "color": "#EEF1F3",
        "spots": [
          [
            0.18,
            0.5
          ],
          null
        ],
        "description": "Il Visible Infrared Imaging Radiometer Suite riprende una striscia larga 3000 km in 22 bande, dal visibile all'infrarosso termico. Una di queste, la banda giorno/notte (Day/Night Band), è abbastanza sensibile da misurare le luci delle città e la luce della Luna riflessa dalle nuvole.",
        "facts": [
          [
            "Bande",
            "22, dal visibile al termico"
          ],
          [
            "Risoluzione",
            "da circa 400 a 800 m"
          ],
          [
            "Larghezza ripresa",
            "3000 km"
          ],
          [
            "Banda speciale",
            "giorno/notte (luci notturne)"
          ]
        ],
        "info": "Con 3000 km di larghezza bastano due passaggi al giorno per vedere tutta la Terra, di giorno e di notte. Il prezzo è la risoluzione: pixel di centinaia di metri. È il compromesso opposto a Sentinel-2, che vede dettagli di 10 m ma torna sullo stesso punto ogni 5 giorni.",
        "inEarthPulse": "La sezione \"Di notte\" usa la media annuale della banda giorno/notte (NASA Black Marble VNP46A4), corretta per Luna, nuvole e atmosfera."
      },
      {
        "number": 3,
        "name": "Comunicazioni",
        "role": "Scarica ogni orbita i dati di tutti gli strumenti.",
        "color": "#8B6BBE",
        "spots": [
          [
            0.39,
            0.6
          ],
          null
        ],
        "description": "I dati memorizzati a bordo scendono in banda X a 300 Mbit/s; un secondo canale da 15 Mbit/s trasmette in diretta a chiunque abbia un'antenna adatta, per esempio i servizi meteo locali.",
        "facts": [
          [
            "Dati memorizzati",
            "banda X, 300 Mbit/s"
          ],
          [
            "Trasmissione diretta",
            "15 Mbit/s"
          ]
        ],
        "info": "Per un satellite meteorologico conta la tempestività: la trasmissione diretta permette di usare le immagini pochi minuti dopo il passaggio, senza aspettare lo scarico alle stazioni principali.",
        "inEarthPulse": null
      },
      {
        "number": 4,
        "name": "Pannello solare",
        "role": "Produce l'energia per i cinque strumenti.",
        "color": "#26467F",
        "spots": [
          [
            0.883,
            0.25
          ],
          null
        ],
        "description": "Un'ala di celle all'arseniuro di gallio (GaAs), più efficienti di quelle al silicio, fornisce in media circa 2 kW anche a fine vita.",
        "facts": [
          [
            "Celle",
            "arseniuro di gallio (GaAs)"
          ],
          [
            "Potenza media",
            "circa 2 kW a fine vita"
          ]
        ],
        "info": "Cinque strumenti accesi sempre, giorno e notte, richiedono molta più energia di un satellite che riprende solo sopra le terre emerse: le celle ad alta efficienza riducono superficie e massa dell'ala.",
        "inEarthPulse": null
      },
      {
        "number": 5,
        "name": "Orbita",
        "role": "Passa di pomeriggio e nel cuore della notte.",
        "color": "#3FA37A",
        "spots": [
          null,
          null
        ],
        "description": "Orbita eliosincrona a circa 830 km, un giro ogni 101 minuti. Suomi NPP passa sopra ogni luogo verso le 13:30 e, dall'altra parte dell'orbita, verso l'1:30 di notte: è quel passaggio notturno che vede le luci delle città.",
        "facts": [
          [
            "Quota",
            "circa 830 km"
          ],
          [
            "Periodo",
            "101 minuti"
          ],
          [
            "Passaggi",
            "circa 13:30 e 1:30 ora locale"
          ]
        ],
        "info": "L'ora del passaggio è una scelta di missione: di notte all'1:30 le città sono ancora illuminate ma il traffico è basso, e la stessa ora ogni notte rende confrontabili le misure di giorni e anni diversi.",
        "inEarthPulse": null
      }
    ],
    "overview": "Suomi NPP è nato come ponte tra i satelliti climatici NASA e la nuova serie meteorologica JPSS. Il suo strumento VIIRS riprende l'intero pianeta ogni giorno, anche di notte: è così che si misurano le luci delle città.",
    "sources": "Fonti dei dati: eoPortal (Suomi NPP) e Wikipedia (Suomi NPP)."
  }
}
