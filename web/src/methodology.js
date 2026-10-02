// Metodologia (stessi testi della schermata dell'app, più le sezioni del sito).
// Ogni voce: ['p', paragrafo] · ['b', punto elenco] · ['f', formula]

export const METHODOLOGY = [
  {
    "title": "1 · I dati",
    "items": [
      [
        "p",
        "Usiamo immagini Sentinel-2 del programma europeo Copernicus, prodotto Level-2A (riflettanza della superficie, già corretta per l'atmosfera). Le scene sono cercate nel catalogo STAC Earth Search di Element 84."
      ],
      [
        "b",
        "Risoluzione delle bande usate: 10 m."
      ],
      [
        "b",
        "Un passaggio sullo stesso punto ogni 2–5 giorni circa, ma molte immagini sono coperte da nuvole."
      ],
      [
        "b",
        "L'area analizzata è un quadrato di circa 1 × 1 km (circa 10.000 pixel) centrato sul punto scelto."
      ]
    ]
  },
  {
    "title": "2 · L'indice NDVI",
    "items": [
      [
        "f",
        "NDVI = (NIR − RED) / (NIR + RED)"
      ],
      [
        "p",
        "NIR è la banda B08 (vicino infrarosso), RED è la banda B04 (rosso). La vegetazione fotosinteticamente attiva assorbe il rosso e riflette molto l'infrarosso, quindi ha NDVI alto."
      ],
      [
        "p",
        "Valori indicativi, che variano con il tipo di superficie e la stagione:"
      ],
      [
        "b",
        "sotto 0: acqua, neve, nuvole residue;"
      ],
      [
        "b",
        "0 – 0,2: suolo nudo, roccia, aree urbane;"
      ],
      [
        "b",
        "0,2 – 0,5: vegetazione rada, prati, colture giovani;"
      ],
      [
        "b",
        "oltre 0,5: vegetazione densa (boschi, colture sviluppate)."
      ],
      [
        "p",
        "Il valore mostrato è la media dei pixel validi dell'area."
      ]
    ]
  },
  {
    "title": "3 · Controllo di qualità",
    "items": [
      [
        "p",
        "Ogni pixel viene verificato con la classificazione della scena (SCL) di Sentinel-2. Escludiamo i pixel senza dati, saturi o difettosi, le ombre delle nuvole, le nuvole a media e alta probabilità, i cirri sottili, la neve e i pixel non classificati."
      ],
      [
        "b",
        "Una scena è usata solo se almeno il 70% dei pixel dell'area è valido."
      ],
      [
        "b",
        "Se in un giorno ci sono più scene, si tiene quella con meno nuvole dichiarate."
      ],
      [
        "b",
        "Dal 25 gennaio 2022 i dati Sentinel-2 L2A possono avere uno scostamento radiometrico di 1000 (processing baseline 04.00). Non ci fidiamo solo del catalogo: lo sottraiamo solo se i dati lo contengono davvero, cioè se anche i pixel più scuri (acqua, ombre) stanno sopra circa 1000. Così i confronti tra anni diversi restano corretti."
      ]
    ]
  },
  {
    "title": "4 · Osservazione recente",
    "items": [
      [
        "p",
        "Cerchiamo la scena valida più recente negli ultimi 45 giorni. La mostriamo come recente solo se ha al massimo 20 giorni; altrimenti viene segnalato che non rappresenta la situazione attuale."
      ],
      [
        "p",
        "Distinguiamo sempre la data di acquisizione (quando il satellite ha ripreso l'area) dalla data di elaborazione (quando è stata calcolata l'analisi)."
      ]
    ]
  },
  {
    "title": "5 · Baseline stagionale",
    "items": [
      [
        "p",
        "L'NDVI cambia molto con le stagioni, quindi non confrontiamo luglio con gennaio. La baseline usa le osservazioni valide degli ultimi 3 anni nella stessa finestra stagionale (±15 giorni dalla stessa data), fino a 3 per anno. Il valore di riferimento è la mediana, meno sensibile ai valori anomali della media."
      ],
      [
        "b",
        "Servono almeno 3 osservazioni storiche, altrimenti il confronto non viene mostrato."
      ],
      [
        "b",
        "Supporto storico: insufficiente (<2), limitato (2–3), buono (4–5), forte (6 o più)."
      ]
    ]
  },
  {
    "title": "6 · Anomalia",
    "items": [
      [
        "f",
        "Anomalia % = (NDVI − baseline) / |baseline| × 100"
      ],
      [
        "b",
        "≤ −8%: marcatamente sotto la baseline;"
      ],
      [
        "b",
        "da −8% a −5%: sotto la baseline;"
      ],
      [
        "b",
        "da −5% a 0%: leggermente sotto la baseline;"
      ],
      [
        "b",
        "da 0% a +5%: vicino alla baseline;"
      ],
      [
        "b",
        "≥ +5%: sopra la baseline."
      ],
      [
        "p",
        "Se la baseline è inferiore a 0,2 (poca o nessuna vegetazione) la percentuale è poco significativa: mostriamo la differenza assoluta."
      ]
    ]
  },
  {
    "title": "Altri indici",
    "items": [
      [
        "p",
        "Oltre all'NDVI mostriamo altri indici calcolati dalle stesse immagini Sentinel-2, tutti come differenze normalizzate tra due bande:"
      ],
      [
        "f",
        "NDWI = (B03 − B08) / (B03 + B08)"
      ],
      [
        "b",
        "Acqua (NDWI): evidenzia laghi, fiumi e allagamenti; in città può confondere tetti e ombre con l'acqua."
      ],
      [
        "f",
        "NDMI = (B08 − B11) / (B08 + B11)"
      ],
      [
        "b",
        "Umidità (NDMI): contenuto d'acqua della vegetazione, utile per lo stress idrico e la siccità."
      ],
      [
        "f",
        "NDBI = (B11 − B08) / (B11 + B08)"
      ],
      [
        "b",
        "Costruito (NDBI): evidenzia edifici e superfici impermeabili, ma anche suolo nudo e rocce."
      ],
      [
        "f",
        "dNBR = NBR(prima) − NBR(dopo)"
      ],
      [
        "b",
        "Gravità incendio (dNBR, con NBR = (B08 − B12) / (B08 + B12)): classi USGS 0,10 · 0,27 · 0,44 · 0,66. Misura l'effetto sulla vegetazione, non l'intensità delle fiamme."
      ],
      [
        "f",
        "NDRE = (B08 − B05) / (B08 + B05)"
      ],
      [
        "b",
        "Clorofilla (NDRE): usa la banda red-edge B05, sensibile alla clorofilla; nelle colture fitte distingue meglio dell'NDVI le piante in difficoltà."
      ],
      [
        "f",
        "NDSI = (B03 − B11) / (B03 + B11)"
      ],
      [
        "b",
        "Neve (NDSI): sopra 0,4 di solito neve o ghiaccio. Qui la classe \"neve\" della SCL non viene scartata."
      ],
      [
        "f",
        "NDCI = (B05 − B04) / (B05 + B04)"
      ],
      [
        "b",
        "Alghe (NDCI), solo sull'acqua: clorofilla del fitoplancton, indicatore qualitativo delle fioriture."
      ],
      [
        "f",
        "NDTI = (B04 − B03) / (B04 + B03)"
      ],
      [
        "b",
        "Torbidità (NDTI), solo sull'acqua: sedimenti in sospensione, per esempio dopo le piogge o alle foci."
      ],
      [
        "b",
        "Superficie d'acqua: pixel classificati come acqua dalla SCL oppure con NDWI > 0, esclusi quelli coperti da nuvole; il numero di pixel per l'area di un pixel dà gli ettari."
      ],
      [
        "b",
        "B05, B11 e B12 hanno pixel di 20 m: sono ricampionate in modo bilineare sulla griglia di 10 m, quindi i dettagli più fini sono meno nitidi."
      ]
    ]
  },
  {
    "title": "Ogni indice: valore e confronto",
    "items": [
      [
        "p",
        "Ogni indice ha la sua sezione, costruita come quella della vegetazione: il valore nell'area di 1 × 1 km intorno al punto e il confronto con la stessa stagione degli anni precedenti."
      ],
      [
        "b",
        "Valore della scena: la mediana dell'indice sui pixel validi della zona utile. Per Clorofilla, Umidità e Costruito la zona utile è la terraferma (l'acqua libera è esclusa); per Alghe e Torbidità è solo l'acqua; per la Neve la classe \"neve\" della SCL non viene scartata."
      ],
      [
        "b",
        "Una scena è usata solo se almeno il 70% della zona utile è senza nuvole. L'osservazione recente è la più nuova valida degli ultimi 45 giorni."
      ],
      [
        "b",
        "Confronto: mediana delle scene valide degli ultimi 3 anni nella stessa finestra (±15 giorni), fino a 3 per anno; servono almeno 3 osservazioni."
      ],
      [
        "b",
        "Questi indici sono spesso vicini a zero o negativi, quindi la variazione percentuale non avrebbe senso: usiamo la differenza assoluta. Sotto 0,03 è \"come negli anni scorsi\", da 0,03 a 0,08 un cambiamento \"di poco\", oltre 0,08 un cambiamento netto."
      ],
      [
        "b",
        "Acqua: oltre all'indice mostriamo gli ettari d'acqua libera (SCL acqua oppure NDWI > 0, senza nuvole). Neve: la quota dell'area con NDSI sopra 0,4."
      ],
      [
        "b",
        "Il grafico \"Stesso periodo, anni diversi\" mostra ogni immagine valida degli anni precedenti nella stessa finestra stagionale (punti grigi), l'intervallo osservato (fascia), la mediana di riferimento (linea tratteggiata) e il valore attuale (punto arancione). Sotto i numeri c'è la mappa dell'indice su 3 × 3 km, oggi e un anno fa, con il riquadro tratteggiato dell'area di 1 km. Per la vegetazione anche la mappa della variazione."
      ]
    ]
  },
  {
    "title": "Immagini dall'alto",
    "items": [
      [
        "p",
        "La sezione \"Dall'alto\" mostra i colori reali di un'area di 1, 2 o 3 km di lato da due scene quasi senza nuvole (almeno 95% di pixel validi): la più recente e quella più vicina alla stessa data di un anno prima. Con \"Scegli le date\" si può confrontare qualsiasi coppia di stagioni. Le mappe degli indici sono nelle loro sezioni."
      ],
      [
        "b",
        "Colori reali: calcolati dalle bande B04, B03 e B02 come riflettanza della superficie (16 bit), non dall'immagine \"True Color\" a 8 bit, che satura già a riflettanza 0,31 e trasforma deserti e sabbia in un quadrato giallo chiaro. Usiamo una curva tonale morbida (arcoseno iperbolico): le zone scure vengono schiarite, quelle chiare compresse gradualmente fino al \"bianco\" della scena (99,5° percentile, tra 0,30 e 0,90). La curva è applicata per il 25% alla luminosità (colori pieni) e per il 75% canale per canale: le superfici chiare come la sabbia tendono al beige invece che all'arancione, come le vede l'occhio, mentre vegetazione e acqua restano quasi invariate. La data precedente è armonizzata alla più recente (percentili 2–98) e usa lo stesso bianco: è solo una scelta di visualizzazione."
      ],
      [
        "b",
        "NDVI: scala di colori fissa, quindi due date sono confrontabili a colpo d'occhio."
      ],
      [
        "b",
        "Variazione: NDVI dopo meno NDVI prima, solo dove entrambe le immagini sono valide."
      ],
      [
        "b",
        "Le due date sono ricampionate sulla stessa griglia di 10 m, così coincidono pixel per pixel."
      ]
    ]
  },
  {
    "title": "Luci notturne",
    "items": [
      [
        "p",
        "Il sensore VIIRS (satellite Suomi NPP) misura la luce emessa di notte. NASA Black Marble (prodotto VNP46A4) ne ricava una media annuale, dal 2012, corretta per luce lunare, nuvole e atmosfera."
      ],
      [
        "b",
        "Usiamo il composito \"quasi verticale, senza neve\": la vista più adatta a confrontare anni diversi."
      ],
      [
        "b",
        "Pixel di 15 secondi d'arco (circa 500 m): per questo l'area è di 30–120 km, non di 1–3 km."
      ],
      [
        "b",
        "Scala logaritmica: ogni passo di colore vale circa il triplo di luce, così si vedono sia i paesi sia i centri città."
      ],
      [
        "b",
        "Il mare (maschera terra/mare del prodotto) è in blu uniforme; restano visibili solo porti e navi molto illuminati."
      ],
      [
        "b",
        "La variazione percentuale somma la luce di tutta la terraferma dell'area. I LED bianchi sono visti meno da VIIRS: un calo può anche indicare un cambio di lampioni."
      ]
    ]
  },
  {
    "title": "Isole di calore",
    "items": [
      [
        "p",
        "La temperatura delle superfici viene dal sensore termico di Landsat 8 e 9 (USGS/NASA, Collection 2 Level-2): misura a 100 m, distribuita a 30 m. I satelliti passano verso le 10:30 del mattino."
      ],
      [
        "b",
        "Usiamo fino a 4 giornate estive (giugno-agosto, ultimi 3 anni) con almeno l'80% della terraferma senza nuvole."
      ],
      [
        "b",
        "Anomalia: per ogni giornata la differenza di ogni punto dalla mediana della terraferma dell'area; poi la mediana tra le giornate. Così conta dove fa più caldo, non quanto era calda quella singola giornata."
      ],
      [
        "b",
        "Mare, laghi e fiumi sono esclusi (maschera dell'acqua di Landsat, unita tra tutte le giornate)."
      ],
      [
        "b",
        "È la temperatura delle superfici, non dell'aria: asfalto e tetti al sole possono superare i 50 °C mentre l'aria è a 32 °C."
      ],
      [
        "b",
        "Accanto al calore mostriamo i colori reali di Sentinel-2 (10 m) di una giornata limpida vicina, per riconoscere i luoghi."
      ]
    ]
  },
  {
    "title": "Archivio dal 1984",
    "items": [
      [
        "p",
        "La sezione \"Com'era dal 1984\" usa l'archivio Landsat Collection 2 (USGS/NASA): Landsat 5 TM (1984-2011), Landsat 7 ETM+, Landsat 8 e 9 OLI, con pixel di 30 m."
      ],
      [
        "b",
        "Per ogni anno una giornata della stagione estiva (giugno-settembre; nell'emisfero sud dicembre-marzo) con meno del 20% di nuvole e almeno l'85% dell'area limpida."
      ],
      [
        "b",
        "Riflettanza della superficie con la stessa scala per tutti gli anni e tutti i sensori, quindi i colori sono confrontabili a colpo d'occhio."
      ],
      [
        "b",
        "Landsat 7 dal 2003 ha un guasto (SLC-off) che lascia strisce vuote: lo usiamo solo se quell'anno non c'è altro (di solito il 2012)."
      ],
      [
        "b",
        "I sensori di epoche diverse hanno bande leggermente diverse: le piccole differenze di colore o di NDVI tra decenni non sono significative, i grandi cambiamenti sì."
      ],
      [
        "b",
        "Stessa curva tonale dei colori reali di Sentinel-2: sabbia, roccia e cemento non diventano bianchi."
      ]
    ]
  },
  {
    "title": "Scegli le date",
    "items": [
      [
        "p",
        "Con \"Scegli le date\" il confronto non è più tra oggi e un anno fa, ma tra due stagioni a scelta degli ultimi 5 anni."
      ],
      [
        "b",
        "Per ogni stagione (inverno, primavera, estate, autunno) teniamo la scena con più pixel validi tra le 3 con meno nuvole dichiarate: almeno il 90% dell'area senza nuvole, o l'80% se non c'è di meglio."
      ],
      [
        "b",
        "Variazione e colori della data precedente vengono ricalcolati sulla coppia scelta."
      ]
    ]
  },
  {
    "title": "Qualità dell'aria",
    "items": [
      [
        "p",
        "I valori vengono dal servizio europeo Copernicus Atmosphere Monitoring Service (CAMS), letti tramite Open-Meteo. CAMS unisce un modello dell'atmosfera con misure da satellite e da stazioni a terra."
      ],
      [
        "b",
        "In Europa la griglia è di circa 11 km con dati ogni ora; nel resto del mondo di circa 45 km. Descrivono l'aria della zona, non della singola strada."
      ],
      [
        "b",
        "Indice europeo della qualità dell'aria (EEA): Buona fino a 20, Discreta fino a 40, Moderata fino a 60, Scadente fino a 80, Molto scadente fino a 100, oltre Pessima. Ogni inquinante ha il suo sotto-indice; l'indice complessivo è il peggiore."
      ],
      [
        "b",
        "Il grafico mostra ieri, oggi e domani: a destra della linea \"ora\" i valori sono una previsione."
      ],
      [
        "b",
        "Le misure dirette del satellite Sentinel-5P (mappe dei gas, pixel di circa 5 km) sono nella sezione \"Gas dal satellite\"."
      ]
    ]
  },
  {
    "title": "Gas dal satellite (Sentinel-5P)",
    "items": [
      [
        "p",
        "Lo strumento TROPOMI di Sentinel-5P misura ogni giorno, verso le 13:30 ora locale, la luce del Sole riflessa dall'atmosfera e ne ricava la quantità di diversi gas nella colonna d'aria. Leggiamo i dati di livello 2 tramite le API Sentinel Hub di Copernicus Data Space Ecosystem."
      ],
      [
        "b",
        "Andamento sul luogo: media giornaliera entro 15 km dal punto (Statistical API), negli ultimi 30, 90 o 365 giorni, confrontata con gli stessi giorni dell'anno precedente. Ogni giorno è la media dei passaggi validi del satellite (mosaicking per orbita); le richieste sono divise in blocchi di 30 giorni. La linea è la media mobile su 7 giorni (almeno 3 giorni con dati), i punti sono i singoli giorni: i giorni nuvolosi mancano. Se i giorni validi sono meno della metà, la linea unisce direttamente i singoli giorni e compare un avviso."
      ],
      [
        "b",
        "Mappa: media di tutti i passaggi validi degli ultimi 7 giorni (30 per il metano, che ha più lacune) su 300 × 300 km, a confronto con gli stessi giorni dell'anno precedente."
      ],
      [
        "b",
        "Usiamo solo i dati che superano il controllo di qualità del prodotto (qa ≥ 75% per NO₂, ≥ 50% per gli altri gas). Pixel TROPOMI di circa 5,5 × 3,5 km."
      ],
      [
        "b",
        "Lettura indicativa per l'NO₂ troposferico (media di più giorni): sotto 30 µmol/m² basso (aree rurali), 30–70 medio, 70–150 alto (grandi città), oltre 150 molto alto. Metano in ppb rispetto alla media globale recente (circa 1880–1930 ppb). Sono soglie orientative, non limiti di legge."
      ],
      [
        "b",
        "Sono quantità nella colonna d'aria, non concentrazioni al livello della strada: per l'aria che respiriamo vale la sezione \"Qualità dell'aria\"."
      ],
      [
        "b",
        "Ogni area e periodo viene calcolato una volta al giorno e tenuto in memoria, per rispettare le quote del servizio."
      ]
    ]
  },
  {
    "title": "Nuvole in diretta",
    "items": [
      [
        "p",
        "Le immagini vengono dallo strumento FCI di Meteosat-12 (MTG-I1), il primo Meteosat di terza generazione, erede dello strumento SEVIRI. È in orbita geostazionaria a 36.000 km sopra l'equatore e riprende Europa, Africa e Atlantico ogni 10 minuti."
      ],
      [
        "b",
        "Le immagini sono servite da EUMETView (EUMETSAT) con circa 15-20 minuti di ritardo."
      ],
      [
        "b",
        "Colori: composito GeoColour, colori naturali di giorno e nuvole su sfondo notturno di notte. Tipo di nubi: distingue nubi basse d'acqua da nubi alte di ghiaccio. Polvere: la sabbia del deserto appare rosa-magenta."
      ],
      [
        "b",
        "Nelle animazioni lunghe usiamo un'immagine ogni 20 minuti (6 ore), 30 minuti (12 e 24 ore)."
      ]
    ]
  },
  {
    "title": "Satelliti e orbite",
    "items": [
      [
        "p",
        "Le posizioni dei satelliti sul globo sono calcolate nel browser con il modello SGP4 a partire dagli elementi orbitali (TLE) pubblicati da CelesTrak, aggiornati ogni 6 ore dal nostro server."
      ],
      [
        "b",
        "Se CelesTrak non risponde usiamo una fonte di riserva e, in ultimo, una copia salvata: la posizione resta credibile per alcune settimane, con un errore che cresce nel tempo."
      ],
      [
        "b",
        "La linea tratteggiata è la traccia a terra del prossimo giro; quella tenue il percorso degli ultimi 25 minuti."
      ]
    ]
  },
  {
    "title": "Oltre la Terra",
    "items": [
      [
        "p",
        "Luna, Marte, Giove e le sue quattro lune principali sono disegnati in 3D (three.js) come sfere con la loro mappa globale in proiezione equirettangolare (2048 × 1024 pixel). Giove è leggermente schiacciato ai poli, come nella realtà."
      ],
      [
        "b",
        "Mappe: Luna, Marte e Giove da Solar System Scope (CC BY 4.0, da dati NASA); Io, Europa, Ganimede e Callisto dai mosaici globali USGS Astrogeology delle sonde Voyager e Galileo (pubblico dominio). Europa e Callisto hanno mosaici in bianco e nero con una leggera tinta; le zone mai fotografate sono in grigio."
      ],
      [
        "b",
        "\"Adesso\": fase e distanza della Luna, distanza di Marte e Giove e posizione delle lune di Giove sono calcolate nel browser con la libreria astronomy-engine (modelli VSOP87, teoria lunare e L1.2 per le lune di Giove), senza servizi esterni."
      ],
      [
        "b",
        "Il disegno delle lune di Giove mostra la loro posizione vista dalla Terra, come in un binocolo, ruotato perché la linea delle lune sia orizzontale; le distanze sono in raggi di Giove (71.492 km)."
      ],
      [
        "b",
        "Altri corpi: Mercurio, Venere, Cerere, Vesta, Fobos, Encelado e Titano usano i mosaici globali di NASA Solar System Treks (MESSENGER, Magellan, Dawn, Viking, Cassini), uniti dal server in una mappa di 2048 × 1024 pixel. Venere è un'immagine radar: le nubi nascondono la superficie. Titano è ripreso a 938 nm, nel vicino infrarosso che attraversa la foschia. Fobos non è sferico (27 × 22 × 18 km): la sfera è un'approssimazione. Encelado e la mappa \"Colori potenziati\" di Mercurio sono a falsi colori."
      ],
      [
        "b",
        "Mappe con valori numerici: il server scarica i dati originali dal Planetary Data System della NASA (pubblico dominio), li porta tutti alla stessa griglia (nord in alto, longitudine da 180° O a 180° E, al massimo 4 pixel per grado) e li colora. Le soglie sono fisse per l'altitudine e calcolate sui dati per le altre mappe (dal 2° al 98° percentile, arrotondate); le scale divergenti (gravità, magnetismo) sono simmetriche attorno a zero. Il grigio indica dove il dato manca. Toccando il globo si legge il valore del pixel che contiene il punto, con la sua dimensione."
      ],
      [
        "b",
        "Luna: altitudine LRO LOLA (LDEM_4, metri rispetto a 1737,4 km); torio (ppm), ossido di ferro (% in peso) e idrogeno (ppm) da Lunar Prospector, celle di 0,5° (Lawrence et al.); anomalia di gravità in aria libera da GRAIL (modello GRGM660PRIM fino al grado 320, milligal)."
      ],
      [
        "b",
        "Marte: altitudine MGS MOLA (MEGDR, metri rispetto all'areoide); acqua nel suolo da Mars Odyssey GRS (% in peso, celle di 5°, alte latitudini escluse; Boynton et al. 2007); inerzia termica da MGS TES (J m⁻² K⁻¹ s⁻½, tra 60° N e 50° S); componente radiale del campo magnetico crostale a 400 km di quota da MGS MAG/ER (nT, celle di 1°; Connerney et al. 2001); infrarosso notturno THEMIS (qualitativo)."
      ],
      [
        "b",
        "Mercurio: rapporto magnesio/silicio dallo spettrometro a raggi X di MESSENGER (celle di 0,25°, copertura parziale; Nittler et al. 2020). Cerere: idrogeno come percentuale di acqua equivalente dallo spettrometro GRaND di Dawn (risoluzione di circa 600 km; Prettyman et al.)."
      ]
    ]
  },
  {
    "title": "Big Events",
    "items": [
      [
        "p",
        "Ogni evento ha luogo, area (da 4 a 12 km di lato), data e due finestre di tempo \"prima\" e \"dopo\" in cui cerchiamo le immagini più limpide. Per gli eventi recenti usiamo Sentinel-2 (10 m), per i cambiamenti di decenni l'archivio Landsat (30 m)."
      ],
      [
        "b",
        "Dopo una verifica visiva alcune scene sono fissate per avere risposte rapide e sempre uguali."
      ],
      [
        "b",
        "I testi e i numeri di ogni evento vengono dalle fonti elencate sotto l'evento (agenzie spaziali, servizi Copernicus, articoli scientifici, enciclopedie): i dati sulle vittime possono cambiare con il tempo."
      ],
      [
        "b",
        "Durante alluvioni e incendi il cielo è spesso coperto: l'immagine \"dopo\" è la prima abbastanza limpida, non sempre il momento peggiore."
      ]
    ]
  },
  {
    "title": "7 · Limiti",
    "items": [
      [
        "b",
        "L'NDVI non misura direttamente la salute della vegetazione: è legato alla sua risposta spettrale."
      ],
      [
        "b",
        "Un'anomalia non dimostra da sola la causa: siccità, tagli, incendi, raccolti, ma anche differenze di osservazione possono produrla."
      ],
      [
        "b",
        "Nella vegetazione molto densa l'NDVI tende a saturare e varia poco."
      ],
      [
        "b",
        "Un singolo valore anomalo va confermato da osservazioni successive: un calo isolato può dipendere da foschia, geometria di ripresa o tile diversa."
      ],
      [
        "b",
        "L'area è un quadrato approssimato e può includere superfici diverse (strade, edifici, acqua)."
      ],
      [
        "b",
        "Gas: contiene dati Copernicus Sentinel-5P modificati, tramite Sentinel Hub (Copernicus Data Space Ecosystem)."
      ],
      [
        "b",
        "I pixel di 10 m mescolano elementi diversi: piccoli cambiamenti possono non essere visibili."
      ],
      [
        "b",
        "Nelle mappe di variazione, lungo strade e fiumi possono comparire sottili bordi rossi e verdi: sono dovuti al piccolo disallineamento tra due acquisizioni, non a cambiamenti reali."
      ]
    ]
  },
  {
    "title": "Fonti e attribuzioni",
    "items": [
      [
        "b",
        "Contiene dati Copernicus Sentinel modificati, elaborati da EarthPulse."
      ],
      [
        "b",
        "Catalogo delle immagini: Earth Search (Element 84), dati Sentinel-2 su AWS Open Data."
      ],
      [
        "b",
        "Temperatura e archivio storico: Landsat 4-9 Collection 2 (USGS/NASA), tramite Microsoft Planetary Computer."
      ],
      [
        "b",
        "Luci notturne: NASA Black Marble VNP46A4 (Román et al.), distribuito da LAADS DAAC / NASA Earthdata."
      ],
      [
        "b",
        "Mappa: OpenFreeMap e OpenMapTiles, dati © OpenStreetMap contributors (ODbL). Ricerca dei luoghi: Nominatim e Photon."
      ],
      [
        "b",
        "Qualità dell'aria: Copernicus Atmosphere Monitoring Service (CAMS), tramite Open-Meteo.com."
      ],
      [
        "b",
        "Nuvole: © EUMETSAT, immagini Meteosat MTG-I1 FCI da EUMETView. Coste e confini: Natural Earth."
      ],
      [
        "b",
        "Orbite: elementi TLE di CelesTrak. Immagini dei satelliti: ESA/ATG medialab (Licenza standard ESA) e NASA (pubblico dominio)."
      ],
      [
        "b",
        "Oltre la Terra: Solar System Scope (CC BY 4.0), NASA/JPL/USGS Astrogeology (pubblico dominio), elaborazioni del progetto amarcher/solar-system; dati LRO LOLA, Lunar Prospector, GRAIL, MGS MOLA/TES/MAG, Mars Odyssey GRS, MESSENGER XRS e Dawn GRaND dal NASA Planetary Data System (pubblico dominio); mosaici MESSENGER, Magellan, Dawn, Viking, Cassini e THEMIS tramite NASA Solar System Treks; calcoli astronomici con astronomy-engine (MIT)."
      ]
    ]
  }
]
