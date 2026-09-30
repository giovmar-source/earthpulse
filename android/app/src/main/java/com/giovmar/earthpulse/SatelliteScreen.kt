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

private enum class SatView(val label: String, val image: Int, val caption: String) {
    EXTERIOR(
        "Esterno", R.drawable.sentinel2_exterior,
        "Sentinel-2 in orbita: a sinistra lo strumento nella coperta isolante dorata, " +
            "a destra la piattaforma con l'ala del pannello solare."
    ),
    INTERIOR(
        "Interno", R.drawable.sentinel2_interior,
        "Vista interna, con le pareti della piattaforma aperte: al centro il serbatoio, " +
            "a destra la struttura dello strumento con i sensori stellari sopra."
    )
}

private fun SatPart.spot(view: SatView): Offset? =
    if (view == SatView.EXTERIOR) exterior else interior

private val PARTS: List<SatPart> = listOf(
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
// SCHERMATA
// ------------------------------------------------------------------

@Composable
fun SatelliteScreen(onBack: () -> Unit) {
    var view by rememberSaveable { mutableStateOf(SatView.EXTERIOR) }
    var selected by rememberSaveable { mutableStateOf<Int?>(null) }

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
            "COM'È FATTO SENTINEL-2",
            color = Green, fontSize = 11.sp, letterSpacing = 1.5.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(Modifier.height(6.dp))
        Text(
            "Il satellite dietro le immagini",
            fontSize = 24.sp, fontWeight = FontWeight.Bold, color = DarkGreen
        )
        Text(
            "Tocca un numero sull'immagine; passa alla vista interna per vedere dentro.",
            fontSize = 13.sp, color = Muted
        )
        Spacer(Modifier.height(12.dp))

        // Esterno / Interno
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SatView.entries.forEach { option ->
                val isSelected = option == view
                Surface(
                    shape = RoundedCornerShape(50),
                    color = if (isSelected) DarkGreen else Color.White,
                    modifier = Modifier.clickable { view = option }
                ) {
                    Text(
                        option.label,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                        color = if (isSelected) Color.White else DarkGreen,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
        }
        Spacer(Modifier.height(10.dp))

        SatelliteImage(
            view = view,
            selected = selected,
            onSpotClick = { number -> selected = if (selected == number) null else number }
        )
        Text(
            view.caption,
            fontSize = 12.sp, lineHeight = 17.sp, color = Muted,
            modifier = Modifier.padding(top = 6.dp)
        )
        Text(
            "Immagine: ESA/ATG medialab · Licenza standard ESA",
            fontSize = 10.sp, color = Muted,
            modifier = Modifier.padding(top = 2.dp)
        )

        // Elenco delle parti (comprende quelle non visibili nella vista scelta)
        Spacer(Modifier.height(12.dp))
        Row(
            Modifier.horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            PARTS.forEach { part ->
                val isSelected = part.number == selected
                Surface(
                    shape = RoundedCornerShape(50),
                    color = if (isSelected) DarkGreen else Color.White,
                    modifier = Modifier.clickable {
                        selected = if (isSelected) null else part.number
                        // Se la parte si vede solo nell'altra vista, passiamo a quella.
                        if (!isSelected && part.spot(view) == null) {
                            SatView.entries.firstOrNull { part.spot(it) != null }
                                ?.let { view = it }
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
        val part = PARTS.firstOrNull { it.number == selected }
        if (part == null) OverviewCard() else PartCard(part)

        Spacer(Modifier.height(16.dp))
        Text(
            "Fonti dei dati: ESA (Sentinel-2 operations; SentiWiki, S2 Mission) ed eoPortal " +
                "(Copernicus: Sentinel-2). Immagini: ESA/ATG medialab.",
            fontSize = 11.sp, lineHeight = 15.sp, color = Muted
        )
        Spacer(Modifier.height(30.dp))
    }
}

/** Immagine ESA con i punti numerati sopra (posizioni in frazioni 0..1). */
@Composable
private fun SatelliteImage(view: SatView, selected: Int?, onSpotClick: (Int) -> Unit) {
    BoxWithConstraints(
        Modifier
            .fillMaxWidth()
            .aspectRatio(16f / 9f)
            .clip(RoundedCornerShape(16.dp))
            .background(Color.Black)
    ) {
        Image(
            painter = painterResource(view.image),
            contentDescription = "Sentinel-2, vista ${view.label.lowercase()}",
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Fit
        )
        val spotSize = 28.dp
        PARTS.forEach { part ->
            val spot = part.spot(view) ?: return@forEach
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
private fun OverviewCard() {
    InfoCardBox {
        Text("Visione d'insieme", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = DarkGreen)
        Spacer(Modifier.height(6.dp))
        Text(OVERVIEW_TEXT, fontSize = 14.sp, lineHeight = 21.sp, color = Muted)
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
