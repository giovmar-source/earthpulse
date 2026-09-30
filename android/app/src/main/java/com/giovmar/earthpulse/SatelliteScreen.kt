package com.giovmar.earthpulse

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// ------------------------------------------------------------------
// MODELLO: parti del satellite
// ------------------------------------------------------------------
//
// Immagini: illustrazioni ESA/ATG medialab (Licenza standard ESA: uso
// educativo e informativo, non commerciale). Ogni parte ha la posizione
// del suo punto numerato sulle due immagini, come frazione di larghezza
// e altezza (0..1); null = non visibile in quella vista.

internal data class SatFact(val label: String, val value: String)

private data class SatPart(
    val number: Int,
    val name: String,
    val role: String,
    val color: Color,
    val exterior: Offset?,
    val interior: Offset?,
    val description: String,
    val facts: List<SatFact>,
    val engineering: String,
    val inEarthPulse: String? = null
)

/** Un'immagine del satellite; i punti delle parti sono in exterior (0) e interior (1). */
private data class SatImage(
    val label: String,
    val res: Int,
    val caption: String,
    val credit: String
)

private data class SatelliteInfo(
    val name: String,
    val headline: String,
    val intro: String,
    val images: List<SatImage>,
    val parts: List<SatPart>,
    val overview: String,
    val sources: String
)

/** Punto della parte sull'immagine n. index (0 = prima immagine, 1 = seconda). */
private fun SatPart.spot(index: Int): Offset? = if (index == 0) exterior else interior

private val SENTINEL2_PARTS: List<SatPart> = listOf(
    SatPart(
        number = 1,
        name = "Piattaforma",
        role = "Il \"telaio\" che porta tutto: struttura, computer di bordo, energia, controllo termico.",
        color = Color(0xFFD5DBE0),
        exterior = Offset(0.521f, 0.407f),
        interior = Offset(0.383f, 0.28f),
        description = "Sentinel-2 usa la piattaforma AstroBus-L di Airbus Defence and Space; " +
            "il prime contractor è Airbus DS di Friedrichshafen (Germania). La piattaforma " +
            "ospita il computer di bordo, la distribuzione dell'energia, i cablaggi e i " +
            "sistemi termici che tengono ogni apparato nel suo intervallo di temperatura.",
        facts = listOf(
            SatFact("Massa al lancio", "1140 kg"),
            SatFact("Dimensioni", "3,4 × 1,8 × 2,35 m"),
            SatFact("Vita di progetto", "7,25 anni"),
            SatFact("Batterie e carburante", "per 12 anni"),
            SatFact("Controllo missione", "ESOC, Darmstadt")
        ),
        engineering = "Riusare una piattaforma già qualificata riduce rischi, costi e tempi: " +
            "si progetta da zero solo ciò che la missione richiede davvero, qui lo strumento. " +
            "La vita di progetto è 7,25 anni, ma batterie e carburante sono dimensionati per 12: " +
            "è questo margine che oggi permette missioni estese, come la campagna di " +
            "Sentinel-2A iniziata nel 2025."
    ),
    SatPart(
        number = 2,
        name = "Strumento MSI",
        role = "La fotocamera multispettrale: tutto il resto del satellite esiste per lei.",
        color = Color(0xFFEEF1F3),
        exterior = Offset(0.354f, 0.40f),
        interior = Offset(0.68f, 0.56f),
        description = "Il Multi-Spectral Instrument è un telescopio a tre specchi (TMA) che " +
            "raccoglie la luce riflessa dalla Terra e la divide in 13 bande, dal blu " +
            "all'infrarosso a onde corte. Due piani focali la misurano: uno per visibile e " +
            "vicino infrarosso (VNIR), uno per l'infrarosso a onde corte (SWIR), ciascuno con " +
            "12 rivelatori sfalsati su due file per coprire 290 km di larghezza.",
        facts = listOf(
            SatFact("Bande", "13 (4 a 10 m, 6 a 20 m, 3 a 60 m)"),
            SatFact("Larghezza ripresa", "290 km"),
            SatFact("Specchi", "carburo di silicio (SiC)"),
            SatFact("Rivelatori", "VNIR CMOS · SWIR MCT"),
            SatFact("SWIR raffreddato", "sotto 210 K (−63 °C)"),
            SatFact("Massa · potenza", "~290 kg · < 266 W")
        ),
        engineering = "Il requisito di partenza è rivedere ogni punto delle terre emerse ogni " +
            "5 giorni con due satelliti: da 786 km servono 290 km di larghezza, un campo visivo " +
            "enorme per un telescopio. Il TMA usa solo specchi, quindi non ha aberrazioni " +
            "cromatiche e resta nitido su tutto il campo in tutte le 13 bande. Il carburo di " +
            "silicio è rigido, leggero e si deforma poco con la temperatura, che cambia a ogni " +
            "passaggio tra luce e ombra. I rivelatori SWIR vanno raffreddati per ridurre il " +
            "rumore termico.",
        inEarthPulse = "EarthPulse usa le bande B02-B03-B04 per i colori reali, B08 e B04 per " +
            "l'NDVI, B03 per l'acqua, B11 per umidità e costruito, B12 per gli incendi. Le file " +
            "di rivelatori sfalsate vedono ogni punto con angoli leggermente diversi: " +
            "l'elaborazione a terra (livello 1C) riallinea le bande sulla stessa griglia."
    ),
    SatPart(
        number = 3,
        name = "Pannello solare",
        role = "Produce l'energia per tutto il satellite.",
        color = Color(0xFF26467F),
        exterior = Offset(0.755f, 0.555f),
        interior = null,
        description = "Un'ala di pannelli fotovoltaici, aperta dopo il lancio, alimenta il " +
            "satellite e ricarica le batterie agli ioni di litio. In una parte di ogni orbita " +
            "il satellite è nell'ombra della Terra e vive solo con le batterie.",
        facts = listOf(
            SatFact("Superficie", "7,1 m²"),
            SatFact("Potenza a inizio vita", "2300 W"),
            SatFact("Potenza a fine vita", "1730 W"),
            SatFact("Batteria", "ioni di litio, 102 Ah a fine vita")
        ),
        engineering = "Si dimensiona sul caso peggiore: fine vita (le celle perdono efficienza " +
            "con le radiazioni), eclisse e massimo consumo durante ripresa e trasmissione. " +
            "Per questo a inizio missione la potenza (2300 W) è ben più alta di quella " +
            "garantita alla fine (1730 W). La batteria va dimensionata per l'ombra, ma anche " +
            "per il numero di cicli: un ciclo di carica e scarica a ogni orbita, per anni."
    ),
    SatPart(
        number = 4,
        name = "Controllo d'assetto",
        role = "Sa dove si trova e dove punta, e corregge l'orientamento.",
        color = Color(0xFF6D8FA0),
        exterior = Offset(0.339f, 0.215f),
        interior = Offset(0.651f, 0.35f),
        description = "Tre sensori stellari (star tracker) riconoscono le stelle e danno " +
            "l'orientamento; giroscopi a fibra ottica misurano le rotazioni; un ricevitore GPS " +
            "a doppia frequenza dà posizione e ora. Quattro ruote di reazione fanno ruotare il " +
            "satellite e tre magnetotorquer sfruttano il campo magnetico terrestre.",
        facts = listOf(
            SatFact("Star tracker", "3"),
            SatFact("Ruote di reazione", "4"),
            SatFact("Magnetotorquer", "3"),
            SatFact("GPS", "doppia frequenza (L1/L2)"),
            SatFact("Geolocalizzazione", "~20 m senza punti a terra")
        ),
        engineering = "Per controllare tre assi bastano tre ruote: la quarta è ridondanza, così " +
            "un guasto non ferma la missione. Le ruote assorbono le piccole coppie di disturbo " +
            "accumulando velocità; i magnetotorquer le \"scaricano\" senza consumare carburante. " +
            "La precisione di assetto e posizione decide quanto bene ogni pixel cade sul punto " +
            "giusto della Terra.",
        inEarthPulse = "È questa precisione che permette a EarthPulse di sovrapporre due date " +
            "pixel per pixel sulla stessa griglia, nel cursore prima/dopo."
    ),
    SatPart(
        number = 5,
        name = "Propulsione",
        role = "Piccoli motori per mantenere l'orbita e, a fine vita, abbassarla.",
        color = Color(0xFFC0633F),
        exterior = null,
        interior = Offset(0.432f, 0.50f),
        description = "Un sistema a monopropellente: l'idrazina passa su un catalizzatore e si " +
            "decompone in gas caldo, senza bisogno di un ossidante. I propulsori da 1 N " +
            "correggono l'orbita per mantenere la traccia a terra ripetibile, evitano i " +
            "detriti spaziali e a fine missione abbassano l'orbita.",
        facts = listOf(
            SatFact("Propellente", "120 kg di idrazina"),
            SatFact("Propulsori", "1 N"),
            SatFact("Usi", "orbita, detriti, fine vita")
        ),
        engineering = "Il monopropellente è la soluzione più semplice e affidabile: un solo " +
            "fluido e nessuna combustione da regolare. Il carburante non si può ricaricare: " +
            "insieme alle batterie fissa la durata massima della missione. Una parte è " +
            "riservata alla fine vita, per ridurre il tempo che il satellite passerà in " +
            "orbita da spento e quindi il rischio di detriti."
    ),
    SatPart(
        number = 6,
        name = "Comunicazioni",
        role = "Comandi dalla Terra, immagini verso la Terra.",
        color = Color(0xFF8B6BBE),
        exterior = Offset(0.469f, 0.215f),
        interior = Offset(0.484f, 0.36f),
        description = "La banda S porta i telecomandi e la telemetria, cioè lo stato di salute " +
            "del satellite. Le immagini scendono in banda X verso le stazioni di terra, oppure " +
            "passano con un terminale laser ai satelliti europei EDRS in orbita geostazionaria, " +
            "che le ritrasmettono a terra.",
        facts = listOf(
            SatFact("Banda S", "64 kbit/s su · 2 Mbit/s giù"),
            SatFact("Banda X", "560 Mbit/s"),
            SatFact("Memoria di bordo", "2,4 Tbit"),
            SatFact("Dati al giorno", "~1,6 TB compressi"),
            SatFact("Stazioni", "Kiruna, Matera, Maspalomas, Svalbard")
        ),
        engineering = "È un problema di bilancio dei dati: lo strumento produce più di quanto si " +
            "possa scaricare in continuo, e ogni stazione è visibile solo pochi minuti per " +
            "orbita. Si comprime a bordo, si memorizza e si scarica ai passaggi; il relè laser " +
            "via EDRS aggiunge occasioni di scarico. Comandi e immagini viaggiano su canali " +
            "separati: se la catena dei dati ha un problema, il satellite resta controllabile."
    ),
    SatPart(
        number = 7,
        name = "Orbita",
        role = "Non è un pezzo, ma è la prima scelta di progetto.",
        color = Color(0xFF3FA37A),
        exterior = null,
        interior = null,
        description = "Orbita eliosincrona a 786 km con inclinazione di 98,62°: il satellite " +
            "passa sopra ogni luogo sempre alla stessa ora locale, le 10:30 del mattino. Un " +
            "giro dura 101 minuti; un satellite rivede lo stesso punto ogni 10 giorni, due " +
            "satelliti sfasati ogni 5.",
        facts = listOf(
            SatFact("Quota", "786 km"),
            SatFact("Inclinazione", "98,62°"),
            SatFact("Ora di passaggio", "10:30 (nodo discendente)"),
            SatFact("Periodo", "101 min"),
            SatFact("Rivisita", "10 giorni (1 sat.) · 5 giorni (2 sat.)"),
            SatFact("Lanci", "2A 2015 · 2B 2017 · 2C 2024")
        ),
        engineering = "Le 10:30 sono un compromesso: il Sole è già abbastanza alto da dare " +
            "buona luce e ombre non troppo lunghe, ma è presto rispetto alle nuvole che si " +
            "formano nelle ore più calde. L'orbita decide la larghezza di ripresa necessaria, " +
            "quindi lo strumento, i dati, l'energia: tutto il resto discende da qui. Dal 21 " +
            "gennaio 2025 Sentinel-2C ha preso il posto di 2A, che continua con una campagna " +
            "estesa.",
        inEarthPulse = "Per questo la timeline di EarthPulse confronta scene della stessa " +
            "stagione: stessa ora del giorno e luce il più simile possibile."
    )
)

private const val OVERVIEW_TEXT =
    "Un satellite è un sistema: ogni parte esiste per servire la missione. Si parte dal " +
        "requisito (vedere ogni punto delle terre emerse ogni 5 giorni, fino a 10 m, in 13 " +
        "bande) e ogni scelta ne discende: l'orbita fissa la larghezza di ripresa; larghezza " +
        "e risoluzione fissano quanti dati si producono; i dati fissano memoria e antenne; " +
        "tutto insieme fissa l'energia, e l'energia il pannello e le batterie. Tocca un " +
        "numero sull'immagine per vedere come."

// ------------------------------------------------------------------
// LANDSAT 9 (immagine NASA, pubblico dominio)
// ------------------------------------------------------------------

private val LANDSAT9_PARTS: List<SatPart> = listOf(
    SatPart(
        number = 1,
        name = "Piattaforma",
        role = "Il satellite \"gemello\" di Landsat 8, costruito per dare continuità all'archivio.",
        color = Color(0xFFD5DBE0),
        exterior = Offset(0.22f, 0.50f),
        interior = null,
        description = "Landsat 9 è stato progettato e costruito da Northrop Grumman sulla " +
            "piattaforma LEOStar-3 ed è stato lanciato il 27 settembre 2021 con un razzo " +
            "Atlas V 401 da Vandenberg, in California. È gestito da NASA e USGS.",
        facts = listOf(
            SatFact("Lancio", "27 settembre 2021, Atlas V 401"),
            SatFact("Costruttore", "Northrop Grumman (LEOStar-3)"),
            SatFact("Vita di progetto", "5 anni"),
            SatFact("Consumabili", "per 10 anni"),
            SatFact("Scene al giorno", "circa 740")
        ),
        engineering = "Landsat 9 è molto simile a Landsat 8, per scelta: riusare un progetto " +
            "già collaudato riduce rischi e tempi e, soprattutto, garantisce che i dati di " +
            "oggi siano confrontabili con quelli di ieri. Per un archivio che copre decenni " +
            "la continuità conta più della novità."
    ),
    SatPart(
        number = 2,
        name = "Strumento OLI-2",
        role = "La fotocamera multispettrale: dal visibile all'infrarosso a onde corte.",
        color = Color(0xFFEEF1F3),
        exterior = Offset(0.155f, 0.57f),
        interior = null,
        description = "L'Operational Land Imager 2 riprende una striscia larga 185 km in 9 " +
            "bande, dal visibile all'infrarosso a onde corte, con pixel di 30 m (15 m per la " +
            "banda pancromatica, in bianco e nero).",
        facts = listOf(
            SatFact("Bande", "9"),
            SatFact("Risoluzione", "30 m (pancromatica 15 m)"),
            SatFact("Larghezza ripresa", "185 km"),
            SatFact("Precisione dei valori", "14 bit")
        ),
        engineering = "14 bit significano 16.384 livelli per ogni pixel: più sfumature sia nelle " +
            "zone molto scure, come l'acqua, sia in quelle molto chiare, come neve e deserti. " +
            "Le bande sono scelte per restare compatibili con i Landsat precedenti.",
        inEarthPulse = "Nella sezione \"Nel tempo\" le immagini degli ultimi anni vengono da " +
            "OLI e OLI-2; quelle degli anni '80 e '90 dal suo antenato TM, su Landsat 5."
    ),
    SatPart(
        number = 3,
        name = "Strumento TIRS-2",
        role = "Il termometro: misura il calore emesso dalle superfici.",
        color = Color(0xFFE07A4F),
        exterior = null,
        interior = null,
        description = "Il Thermal Infrared Sensor 2 misura la radiazione termica in 2 bande " +
            "dell'infrarosso, con pixel di 100 m (distribuiti ricampionati a 30 m).",
        facts = listOf(
            SatFact("Bande termiche", "2"),
            SatFact("Risoluzione", "100 m (distribuita a 30 m)"),
            SatFact("Larghezza ripresa", "185 km")
        ),
        engineering = "Il calore ha lunghezze d'onda molto più lunghe della luce visibile: a " +
            "parità di telescopio i dettagli sono più grossolani e i rivelatori devono essere " +
            "raffreddati per non \"vedere\" il proprio calore. Per questo il termico ha pixel " +
            "di 100 m mentre OLI-2 arriva a 30 m.",
        inEarthPulse = "Le isole di calore di EarthPulse usano la temperatura delle superfici " +
            "calcolata da TIRS e TIRS-2."
    ),
    SatPart(
        number = 4,
        name = "Pannello solare",
        role = "Produce l'energia per il satellite.",
        color = Color(0xFF26467F),
        exterior = Offset(0.515f, 0.39f),
        interior = null,
        description = "Un'unica grande ala di pannelli fotovoltaici, orientata verso il Sole, " +
            "alimenta strumenti e piattaforma e ricarica le batterie per la parte di orbita " +
            "passata nell'ombra della Terra.",
        facts = emptyList(),
        engineering = "Un'ala sola su un lato è la soluzione più semplice e leggera per un " +
            "satellite che guarda sempre la Terra: l'ala ruota per seguire il Sole mentre il " +
            "corpo resta puntato verso il basso."
    ),
    SatPart(
        number = 5,
        name = "Orbita",
        role = "Stessa orbita di Landsat 8, sfasata di mezzo ciclo.",
        color = Color(0xFF3FA37A),
        exterior = null,
        interior = null,
        description = "Orbita eliosincrona a 705 km: Landsat 9 passa sopra l'equatore verso le " +
            "10:12 del mattino, ora locale. Da solo rivede lo stesso punto ogni 16 giorni; " +
            "insieme a Landsat 8 ogni 8.",
        facts = listOf(
            SatFact("Quota", "705 km"),
            SatFact("Ora di passaggio", "circa 10:12 (nodo discendente)"),
            SatFact("Rivisita", "16 giorni · 8 con Landsat 8"),
            SatFact("Archivio Landsat", "dal 1972")
        ),
        engineering = "L'orbita riprende quella dei Landsat precedenti: stessa quota e stessa " +
            "griglia di passaggi a terra, così le immagini di anni diversi si sovrappongono " +
            "e l'archivio resta coerente."
    )
)

// ------------------------------------------------------------------
// SUOMI NPP (immagine NASA, pubblico dominio)
// ------------------------------------------------------------------

private val SUOMI_PARTS: List<SatPart> = listOf(
    SatPart(
        number = 1,
        name = "Piattaforma",
        role = "Satellite meteorologico e climatico di NASA e NOAA.",
        color = Color(0xFFD9A441),
        exterior = Offset(0.44f, 0.32f),
        interior = null,
        description = "Suomi NPP porta il nome del meteorologo Verner Suomi. Costruito da Ball " +
            "Aerospace sulla piattaforma BCP-2000, è stato lanciato il 28 ottobre 2011 con un " +
            "razzo Delta II. Oltre a VIIRS porta altri quattro strumenti per meteo e clima: " +
            "CrIS, ATMS, OMPS e CERES.",
        facts = listOf(
            SatFact("Lancio", "28 ottobre 2011, Delta II"),
            SatFact("Massa al lancio", "circa 2,1 t"),
            SatFact("Piattaforma", "Ball BCP-2000"),
            SatFact("Vita di progetto", "5 anni (consumabili per 7)"),
            SatFact("Distribuzione dati", "NOAA la interrompe dal 1° novembre 2026")
        ),
        engineering = "Progettato per 5 anni, ha lavorato per oltre 14: i margini su carburante " +
            "e componenti si trasformano in anni di dati in più. Ora il suo lavoro passa a " +
            "NOAA-20 e NOAA-21, che portano copie aggiornate degli stessi strumenti.",
        inEarthPulse = "Le luci notturne di EarthPulse vengono da Suomi NPP (dal 2012). Per gli " +
            "anni futuri useremo gli stessi prodotti ricavati da NOAA-20."
    ),
    SatPart(
        number = 2,
        name = "Strumento VIIRS",
        role = "Vede tutta la Terra ogni giorno, anche di notte.",
        color = Color(0xFFEEF1F3),
        exterior = Offset(0.18f, 0.50f),
        interior = null,
        description = "Il Visible Infrared Imaging Radiometer Suite riprende una striscia larga " +
            "3000 km in 22 bande, dal visibile all'infrarosso termico. Una di queste, la " +
            "banda giorno/notte (Day/Night Band), è abbastanza sensibile da misurare le luci " +
            "delle città e la luce della Luna riflessa dalle nuvole.",
        facts = listOf(
            SatFact("Bande", "22, dal visibile al termico"),
            SatFact("Risoluzione", "da circa 400 a 800 m"),
            SatFact("Larghezza ripresa", "3000 km"),
            SatFact("Banda speciale", "giorno/notte (luci notturne)")
        ),
        engineering = "Con 3000 km di larghezza bastano due passaggi al giorno per vedere tutta " +
            "la Terra, di giorno e di notte. Il prezzo è la risoluzione: pixel di centinaia di " +
            "metri. È il compromesso opposto a Sentinel-2, che vede dettagli di 10 m ma torna " +
            "sullo stesso punto ogni 5 giorni.",
        inEarthPulse = "La sezione \"Di notte\" usa la media annuale della banda giorno/notte " +
            "(NASA Black Marble VNP46A4), corretta per Luna, nuvole e atmosfera."
    ),
    SatPart(
        number = 3,
        name = "Comunicazioni",
        role = "Scarica ogni orbita i dati di tutti gli strumenti.",
        color = Color(0xFF8B6BBE),
        exterior = Offset(0.39f, 0.60f),
        interior = null,
        description = "I dati memorizzati a bordo scendono in banda X a 300 Mbit/s; un secondo " +
            "canale da 15 Mbit/s trasmette in diretta a chiunque abbia un'antenna adatta, per " +
            "esempio i servizi meteo locali.",
        facts = listOf(
            SatFact("Dati memorizzati", "banda X, 300 Mbit/s"),
            SatFact("Trasmissione diretta", "15 Mbit/s")
        ),
        engineering = "Per un satellite meteorologico conta la tempestività: la trasmissione " +
            "diretta permette di usare le immagini pochi minuti dopo il passaggio, senza " +
            "aspettare lo scarico alle stazioni principali."
    ),
    SatPart(
        number = 4,
        name = "Pannello solare",
        role = "Produce l'energia per i cinque strumenti.",
        color = Color(0xFF26467F),
        exterior = Offset(0.883f, 0.25f),
        interior = null,
        description = "Un'ala di celle all'arseniuro di gallio (GaAs), più efficienti di quelle " +
            "al silicio, fornisce in media circa 2 kW anche a fine vita.",
        facts = listOf(
            SatFact("Celle", "arseniuro di gallio (GaAs)"),
            SatFact("Potenza media", "circa 2 kW a fine vita")
        ),
        engineering = "Cinque strumenti accesi sempre, giorno e notte, richiedono molta più " +
            "energia di un satellite che riprende solo sopra le terre emerse: le celle ad alta " +
            "efficienza riducono superficie e massa dell'ala."
    ),
    SatPart(
        number = 5,
        name = "Orbita",
        role = "Passa di pomeriggio e nel cuore della notte.",
        color = Color(0xFF3FA37A),
        exterior = null,
        interior = null,
        description = "Orbita eliosincrona a circa 830 km, un giro ogni 101 minuti. Suomi NPP " +
            "passa sopra ogni luogo verso le 13:30 e, dall'altra parte dell'orbita, verso l'1:30 " +
            "di notte: è quel passaggio notturno che vede le luci delle città.",
        facts = listOf(
            SatFact("Quota", "circa 830 km"),
            SatFact("Periodo", "101 minuti"),
            SatFact("Passaggi", "circa 13:30 e 1:30 ora locale")
        ),
        engineering = "L'ora del passaggio è una scelta di missione: di notte all'1:30 le città " +
            "sono ancora illuminate ma il traffico è basso, e la stessa ora ogni notte rende " +
            "confrontabili le misure di giorni e anni diversi."
    )
)

// ------------------------------------------------------------------
// ELENCO DEI SATELLITI
// ------------------------------------------------------------------

private val SATELLITES = listOf(
    SatelliteInfo(
        name = "Sentinel-2",
        headline = "Copernicus Sentinel-2 · ESA/UE",
        intro = "Immagini a 10 m in 13 bande: analisi, colori reali, indici e storie.",
        images = listOf(
            SatImage(
                "Esterno", R.drawable.sentinel2_exterior,
                "Sentinel-2 in orbita: a sinistra lo strumento nella coperta isolante dorata, " +
                    "a destra la piattaforma con l'ala del pannello solare.",
                "Immagine: ESA/ATG medialab · Licenza standard ESA"
            ),
            SatImage(
                "Interno", R.drawable.sentinel2_interior,
                "Vista interna, con le pareti della piattaforma aperte: al centro il serbatoio, " +
                    "a destra la struttura dello strumento con i sensori stellari sopra.",
                "Immagine: ESA/ATG medialab · Licenza standard ESA"
            )
        ),
        parts = SENTINEL2_PARTS,
        overview = OVERVIEW_TEXT,
        sources = "Fonti dei dati: ESA (Sentinel-2 operations; SentiWiki, S2 Mission) ed " +
            "eoPortal (Copernicus: Sentinel-2)."
    ),
    SatelliteInfo(
        name = "Landsat 9",
        headline = "Landsat 9 · NASA/USGS",
        intro = "Erede di 50 anni di Landsat: archivio dal 1984 e temperatura delle superfici.",
        images = listOf(
            SatImage(
                "Esterno", R.drawable.landsat9,
                "Landsat 9 in orbita: a sinistra gli strumenti rivolti verso la Terra, a " +
                    "destra la grande ala del pannello solare.",
                "Immagine: NASA · pubblico dominio"
            )
        ),
        parts = LANDSAT9_PARTS,
        overview = "Landsat osserva le terre emerse dal 1972: è l'archivio satellitare più " +
            "lungo al mondo. Landsat 9 lavora in coppia con Landsat 8 e porta due strumenti: " +
            "OLI-2 per la luce riflessa e TIRS-2 per il calore. Tocca un numero sull'immagine.",
        sources = "Fonti dei dati: NASA Science (Landsat 9). TIRS-2 non ha un punto " +
            "sull'immagine: lo trovi nell'elenco."
    ),
    SatelliteInfo(
        name = "Suomi NPP",
        headline = "Suomi NPP · NASA/NOAA",
        intro = "Vede tutta la Terra ogni giorno e anche di notte: le luci notturne vengono da qui.",
        images = listOf(
            SatImage(
                "Esterno", R.drawable.suomi_npp,
                "Suomi NPP: il corpo dorato della piattaforma con gli strumenti, le antenne e, " +
                    "a destra, l'ala del pannello solare.",
                "Immagine: NASA · pubblico dominio"
            )
        ),
        parts = SUOMI_PARTS,
        overview = "Suomi NPP è nato come ponte tra i satelliti climatici NASA e la nuova " +
            "serie meteorologica JPSS. Il suo strumento VIIRS riprende l'intero pianeta ogni " +
            "giorno, anche di notte: è così che si misurano le luci delle città.",
        sources = "Fonti dei dati: eoPortal (Suomi NPP) e Wikipedia (Suomi NPP)."
    )
)

// ------------------------------------------------------------------
// SCHERMATA
// ------------------------------------------------------------------

@Composable
fun SatelliteScreen(onBack: () -> Unit) {
    var satIndex by rememberSaveable { mutableStateOf(0) }
    var imageIndex by rememberSaveable { mutableStateOf(0) }
    var selected by rememberSaveable { mutableStateOf<Int?>(null) }
    val satellite = SATELLITES[satIndex.coerceIn(0, SATELLITES.lastIndex)]
    val image = satellite.images[imageIndex.coerceIn(0, satellite.images.lastIndex)]

    Column(
        Modifier
            .fillMaxSize()
            .background(Background)
            .statusBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(22.dp)
    ) {
        Text(
            "←  Mappa",
            color = Green,
            modifier = Modifier
                .clickable { onBack() }
                .padding(vertical = 8.dp)
        )
        Spacer(Modifier.height(18.dp))
        Text(
            "I SATELLITI DI EARTHPULSE",
            color = Green, fontSize = 11.sp, letterSpacing = 1.5.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(Modifier.height(6.dp))
        Text(
            "Chi scatta le immagini",
            fontSize = 24.sp, fontWeight = FontWeight.Bold, color = DarkGreen
        )
        Spacer(Modifier.height(10.dp))

        // Scelta del satellite
        Row(
            Modifier.horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            SATELLITES.forEachIndexed { index, option ->
                PillChip(option.name, index == satIndex) {
                    satIndex = index
                    imageIndex = 0
                    selected = null
                }
            }
        }
        Spacer(Modifier.height(10.dp))
        Text(satellite.headline, fontSize = 15.sp, fontWeight = FontWeight.SemiBold, color = DarkGreen)
        Text(satellite.intro, fontSize = 13.sp, lineHeight = 19.sp, color = Muted,
            modifier = Modifier.padding(top = 2.dp))
        Spacer(Modifier.height(12.dp))

        // Viste (solo se il satellite ne ha più di una)
        if (satellite.images.size > 1) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                satellite.images.forEachIndexed { index, option ->
                    PillChip(option.label, index == imageIndex) { imageIndex = index }
                }
            }
            Spacer(Modifier.height(10.dp))
        }

        SatelliteImage(
            satellite = satellite,
            imageIndex = imageIndex,
            selected = selected,
            onSpotClick = { number -> selected = if (selected == number) null else number }
        )
        Text(
            image.caption,
            fontSize = 12.sp, lineHeight = 17.sp, color = Muted,
            modifier = Modifier.padding(top = 6.dp)
        )
        Text(
            image.credit,
            fontSize = 10.sp, color = Muted,
            modifier = Modifier.padding(top = 2.dp)
        )

        // Elenco delle parti (comprende quelle non visibili nella vista scelta)
        Spacer(Modifier.height(12.dp))
        Row(
            Modifier.horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            satellite.parts.forEach { part ->
                val isSelected = part.number == selected
                Surface(
                    shape = RoundedCornerShape(50),
                    color = if (isSelected) DarkGreen else Color.White,
                    modifier = Modifier.clickable {
                        selected = if (isSelected) null else part.number
                        // Se la parte si vede solo nell'altra vista, passiamo a quella.
                        if (!isSelected && part.spot(imageIndex) == null) {
                            satellite.images.indices.firstOrNull { part.spot(it) != null }
                                ?.let { imageIndex = it }
                        }
                    }
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp)
                    ) {
                        Box(
                            Modifier
                                .size(10.dp)
                                .clip(CircleShape)
                                .background(part.color)
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(
                            "${part.number} · ${part.name}",
                            color = if (isSelected) Color.White else DarkGreen,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }
            }
        }

        Spacer(Modifier.height(14.dp))
        val part = satellite.parts.firstOrNull { it.number == selected }
        if (part == null) OverviewCard(satellite.overview) else PartCard(part)

        Spacer(Modifier.height(16.dp))
        Text(satellite.sources, fontSize = 11.sp, lineHeight = 15.sp, color = Muted)
        Spacer(Modifier.height(30.dp))
    }
}

@Composable
private fun PillChip(text: String, selected: Boolean, onClick: () -> Unit) {
    Surface(
        shape = RoundedCornerShape(50),
        color = if (selected) DarkGreen else Color.White,
        modifier = Modifier.clickable { onClick() }
    ) {
        Text(
            text,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
            color = if (selected) Color.White else DarkGreen,
            fontSize = 13.sp,
            fontWeight = FontWeight.SemiBold
        )
    }
}

/** Immagine del satellite con i punti numerati sopra (posizioni in frazioni 0..1). */
@Composable
private fun SatelliteImage(
    satellite: SatelliteInfo,
    imageIndex: Int,
    selected: Int?,
    onSpotClick: (Int) -> Unit
) {
    val image = satellite.images[imageIndex.coerceIn(0, satellite.images.lastIndex)]
    BoxWithConstraints(
        Modifier
            .fillMaxWidth()
            .aspectRatio(16f / 9f)
            .clip(RoundedCornerShape(16.dp))
            .background(Color.Black)
    ) {
        Image(
            painter = painterResource(image.res),
            contentDescription = "${satellite.name}, ${image.label.lowercase()}",
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Fit
        )
        val spotSize = 28.dp
        satellite.parts.forEach { part ->
            val spot = part.spot(imageIndex) ?: return@forEach
            val isSelected = part.number == selected
            Box(
                Modifier
                    .offset(
                        x = maxWidth * spot.x - spotSize / 2,
                        y = maxHeight * spot.y - spotSize / 2
                    )
                    .size(spotSize)
                    .clip(CircleShape)
                    .background(if (isSelected) Orange else Color.White.copy(alpha = 0.92f))
                    .border(2.dp, if (isSelected) Color.White else Orange, CircleShape)
                    .clickable { onSpotClick(part.number) },
                contentAlignment = Alignment.Center
            ) {
                Text(
                    part.number.toString(),
                    color = if (isSelected) Color.White else DarkGreen,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
private fun OverviewCard(text: String) {
    InfoCardBox {
        Text("Visione d'insieme", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = DarkGreen)
        Spacer(Modifier.height(6.dp))
        Text(text, fontSize = 14.sp, lineHeight = 21.sp, color = Muted)
    }
}

@Composable
private fun PartCard(part: SatPart) {
    InfoCardBox {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier
                    .size(14.dp)
                    .clip(CircleShape)
                    .background(part.color)
            )
            Spacer(Modifier.width(8.dp))
            Text(
                "${part.number} · ${part.name}",
                fontSize = 18.sp, fontWeight = FontWeight.Bold, color = DarkGreen
            )
        }
        Text(part.role, fontSize = 13.sp, color = Green, modifier = Modifier.padding(top = 4.dp))
        Spacer(Modifier.height(10.dp))
        Text(part.description, fontSize = 14.sp, lineHeight = 21.sp, color = Muted)

        Spacer(Modifier.height(12.dp))
        part.facts.forEach { fact ->
            Row(Modifier.padding(vertical = 3.dp)) {
                Text(fact.label, fontSize = 13.sp, color = Muted, modifier = Modifier.weight(1f))
                Text(
                    fact.value, fontSize = 13.sp, color = DarkGreen,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1.3f)
                )
            }
        }

        Spacer(Modifier.height(12.dp))
        Box(
            Modifier
                .fillMaxWidth()
                .background(PaleGreen, RoundedCornerShape(12.dp))
                .padding(12.dp)
        ) {
            Column {
                Text(
                    "INFO",
                    fontSize = 11.sp, letterSpacing = 1.2.sp,
                    fontWeight = FontWeight.Bold, color = Green
                )
                Spacer(Modifier.height(4.dp))
                Text(part.engineering, fontSize = 14.sp, lineHeight = 20.sp, color = DarkGreen)
            }
        }

        part.inEarthPulse?.let { text ->
            Spacer(Modifier.height(10.dp))
            Text(
                "IN EARTHPULSE",
                fontSize = 11.sp, letterSpacing = 1.2.sp,
                fontWeight = FontWeight.Bold, color = Orange
            )
            Spacer(Modifier.height(4.dp))
            Text(text, fontSize = 13.sp, lineHeight = 19.sp, color = Muted)
        }
    }
}

@Composable
private fun InfoCardBox(content: @Composable () -> Unit) {
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) { content() }
    }
}
