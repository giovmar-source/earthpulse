
package com.giovmar.earthpulse

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import android.os.Bundle
import androidx.activity.compose.BackHandler
import androidx.compose.runtime.saveable.rememberSaveable
import org.maplibre.android.MapLibre
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke

import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONObject

internal val Green = Color(0xFF176B50)
internal val DarkGreen = Color(0xFF103C32)
internal val Background = Color(0xFFF5F7F4)
internal val Muted = Color(0xFF718078)
internal val PaleGreen = Color(0xFFE3F3E9)
internal val Orange = Color(0xFFD98239)

data class NdviObservation(
    val date: String,
    val ndvi: Double?,
    val baseline: Double?,
    val anomalyPercent: Double?,
    val historicalObservations: Int
)

data class ForestData(
    val placeName: String,
    val targetDate: String,
    val comparisonDate: String,
    val ndvi: Double,
    val baseline: Double,
    val anomalyPercent: Double,
    val historicalObservations: Int,
    val observations: List<NdviObservation>
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // MapLibre (mappa vettoriale) va inizializzata prima di creare le mappe.
        MapLibre.getInstance(this)

        setContent {
            MaterialTheme {
                EarthPulseApp()
            }
        }
    }
}

private fun loadForestData(context: android.content.Context): ForestData {
    val summaryText = context.assets.open("forest_demo.json")
        .bufferedReader().use { it.readText() }

    val seriesText = context.assets.open("forest_demo_timeseries.json")
        .bufferedReader().use { it.readText() }

    val summary = JSONObject(summaryText)
    val series = JSONObject(seriesText)
    val change = summary.getJSONObject("change_detection")

    val observationsJson = series.getJSONArray("observations")
    val observations = (0 until observationsJson.length()).map { i ->
        val item = observationsJson.getJSONObject(i)

        NdviObservation(
            date = item.getString("date"),
            ndvi = item.optNullableDouble("ndvi"),
            baseline = item.optNullableDouble("baseline_ndvi"),
            anomalyPercent = item.optNullableDouble("anomaly_percent"),
            historicalObservations =
                item.optInt("historical_observations", 0)
        )
    }

    return ForestData(
        placeName = summary.optString("place_name", "Forest Demo"),
        targetDate = summary.getString("target_date"),
        comparisonDate = summary.getString("comparison_date"),
        ndvi = summary.getDouble("ndvi"),
        baseline = summary.getDouble("baseline_ndvi"),
        anomalyPercent = summary.getDouble("anomaly_percent"),
        historicalObservations =
            summary.optInt("historical_observations", 0),
        observations = observations
    )
}

private fun JSONObject.optNullableDouble(key: String): Double? {
    if (isNull(key) || !has(key)) return null
    return optDouble(key).takeIf { it.isFinite() }
}

enum class Screen { MAP, ANALYSIS, STORIES, STORY, EXAMPLES, FOREST_DEMO, METHODOLOGY, SATELLITE }

@Composable
fun EarthPulseApp() {
    val context = LocalContext.current

    var data by remember { mutableStateOf<ForestData?>(null) }
    var error by remember { mutableStateOf<String?>(null) }

    // rememberSaveable: lo stato sopravvive alla rotazione dello schermo.
    var screen by rememberSaveable { mutableStateOf(Screen.MAP) }
    var selectedLat by rememberSaveable { mutableStateOf<Double?>(null) }
    var selectedLon by rememberSaveable { mutableStateOf<Double?>(null) }
    var selectedLabel by rememberSaveable { mutableStateOf<String?>(null) }
    var selectedStoryId by rememberSaveable { mutableStateOf<String?>(null) }

    // Schermata a cui tornare quando si chiude la Metodologia.
    var methodologyFrom by rememberSaveable { mutableStateOf(Screen.MAP) }
    fun openMethodology() {
        methodologyFrom = screen
        screen = Screen.METHODOLOGY
    }

    // Risveglia il server Render in background all'apertura dell'app.
    LaunchedEffect(Unit) {
        EarthPulseApi.wakeUp()
    }

    LaunchedEffect(Unit) {
        try {
            data = loadForestData(context)
        } catch (e: Exception) {
            error = e.message ?: "Errore nella lettura dei JSON"
        }
    }

    // Tasto/gesto "indietro" di Android.
    BackHandler(enabled = screen != Screen.MAP) {
        screen = when (screen) {
            Screen.STORY -> Screen.STORIES
            Screen.EXAMPLES -> Screen.STORIES
            Screen.FOREST_DEMO -> Screen.EXAMPLES
            Screen.METHODOLOGY -> methodologyFrom
            else -> Screen.MAP
        }
    }

    val lat = selectedLat
    val lon = selectedLon
    val selectedPlace =
        if (lat != null && lon != null) SelectedPlace(lat, lon, selectedLabel) else null

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Background
    ) {
        if (screen == Screen.MAP) {
            MapScreen(
                selectedPlace = selectedPlace,
                onPlaceSelected = { place ->
                    selectedLat = place.latitude
                    selectedLon = place.longitude
                    selectedLabel = place.label
                },
                onAnalyzeClick = { screen = Screen.ANALYSIS },
                onExamplesClick = { screen = Screen.STORIES },
                onMethodologyClick = { openMethodology() },
                onSatelliteClick = { screen = Screen.SATELLITE }
            )
        } else if (screen == Screen.SATELLITE) {
            SatelliteScreen(onBack = { screen = Screen.MAP })
        } else if (screen == Screen.ANALYSIS && selectedPlace != null) {
            AnalysisScreen(
                place = selectedPlace,
                onBack = { screen = Screen.MAP },
                onMethodologyClick = { openMethodology() }
            )
        } else if (screen == Screen.METHODOLOGY) {
            MethodologyScreen(onBack = { screen = methodologyFrom })
        } else if (screen == Screen.STORIES) {
            StoriesListScreen(
                onBack = { screen = Screen.MAP },
                onStoryClick = { id ->
                    selectedStoryId = id
                    screen = Screen.STORY
                },
                onForestDemoClick = { screen = Screen.EXAMPLES }
            )
        } else if (screen == Screen.STORY && selectedStoryId != null) {
            StoryDetailScreen(
                storyId = selectedStoryId ?: "",
                onBack = { screen = Screen.STORIES }
            )
        } else {
            val currentData = data

            when {
                error != null -> Column(
                    modifier = Modifier.padding(24.dp),
                    verticalArrangement = Arrangement.Center
                ) {
                    Text("Impossibile caricare i dati",
                        fontSize = 22.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(8.dp))
                    Text(error ?: "", color = Muted)
                    Text(
                        "Controlla che entrambi i JSON siano in app/src/main/assets.",
                        color = Muted
                    )
                }

                currentData == null -> Box(
                    Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = Green)
                }

                screen == Screen.FOREST_DEMO -> ForestDetailScreen(
                    data = currentData,
                    onBack = { screen = Screen.EXAMPLES }
                )

                else -> HomeScreen(
                    data = currentData,
                    onForestClick = { screen = Screen.FOREST_DEMO },
                    onBackToMap = { screen = Screen.MAP }
                )
            }
        }
    }
}

@Composable
fun HomeScreen(
    data: ForestData,
    onForestClick: () -> Unit,
    onBackToMap: () -> Unit
) {
    Column(
        Modifier.fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 22.dp, vertical = 26.dp)
    ) {
        Text(
            "←  Mappa",
            color = Green,
            modifier = Modifier
                .clickable { onBackToMap() }
                .padding(vertical = 8.dp)
        )
        Spacer(Modifier.height(12.dp))

        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(42.dp)
                    .background(Green, RoundedCornerShape(14.dp)),
                contentAlignment = Alignment.Center
            ) {
                Text("◉", color = Color.White, fontSize = 27.sp)
            }
            Spacer(Modifier.width(11.dp))
            Column {
                Text("EarthPulse", fontSize = 22.sp,
                    fontWeight = FontWeight.Bold, color = DarkGreen)
                Text("EARTH OBSERVATION", fontSize = 9.sp,
                    letterSpacing = 1.5.sp, color = Muted)
            }
            Spacer(Modifier.weight(1f))
            Text("BETA", color = Green, fontWeight = FontWeight.Bold)
        }

        Spacer(Modifier.height(34.dp))

        Text("The Earth is\nalways changing.",
            fontSize = 34.sp, lineHeight = 39.sp,
            fontWeight = FontWeight.Bold, color = DarkGreen)

        Spacer(Modifier.height(12.dp))

        Text(
            "Satellites help us understand what is happening " +
                    "to the places that matter.",
            fontSize = 15.sp, lineHeight = 23.sp, color = Muted
        )

        Spacer(Modifier.height(25.dp))

        Card(
            modifier = Modifier.fillMaxWidth().clickable { onForestClick() },
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = DarkGreen)
        ) {
            Column(Modifier.padding(20.dp)) {
                Text("FEATURED PLACE", color = PaleGreen,
                    fontSize = 10.sp, letterSpacing = 1.4.sp)
                Spacer(Modifier.height(15.dp))
                Text(data.placeName, fontSize = 25.sp,
                    fontWeight = FontWeight.Bold, color = Color.White)
                Text("Southern Italy · Sentinel-2",
                    color = PaleGreen, fontSize = 13.sp)

                Spacer(Modifier.height(22.dp))
                Text("HISTORICAL EXAMPLE · NDVI", color = PaleGreen, fontSize = 10.sp)
                Text("%.3f".format(java.util.Locale.US, data.ndvi),
                    fontSize = 36.sp, fontWeight = FontWeight.Bold,
                    color = Color.White)
                Text("Observed on ${data.targetDate} · precomputed, not live data",
                    color = PaleGreen, fontSize = 12.sp)

                Spacer(Modifier.height(16.dp))
                HorizontalDivider(color = Color(0xFF426256))
                Spacer(Modifier.height(12.dp))

                Text(
                    "Baseline: %.3f  ·  %+.1f%%".format(
                        java.util.Locale.US,
                        data.baseline,
                        data.anomalyPercent
                    ),
                    color = Color(0xFFE6C99E), fontSize = 13.sp
                )
                Spacer(Modifier.height(12.dp))
                Text("View analysis  →", color = Color.White,
                    fontWeight = FontWeight.SemiBold)
            }
        }

        Spacer(Modifier.height(28.dp))
        Text("Explore places", fontSize = 21.sp,
            fontWeight = FontWeight.Bold, color = DarkGreen)
        Spacer(Modifier.height(15.dp))

        PlaceCard("🌲", "Forest Demo",
            "Vegetation index · NDVI · 2023–2025", "HISTORICAL EXAMPLE", true,
            onForestClick)

        Spacer(Modifier.height(10.dp))
        PlaceCard("🔥", "Post-fire Demo",
            "Vegetation recovery", "COMING SOON", false, null)

        Spacer(Modifier.height(10.dp))
        PlaceCard("🏙️", "Urban Demo",
            "Urban vegetation", "COMING SOON", false, null)

        Spacer(Modifier.height(25.dp))
        Card(colors = CardDefaults.cardColors(containerColor = PaleGreen),
            shape = RoundedCornerShape(18.dp)) {
            Column(Modifier.padding(16.dp)) {
                Text("Evidence, not assumptions",
                    fontWeight = FontWeight.Bold, color = DarkGreen)
                Spacer(Modifier.height(6.dp))
                Text(
                    "A change in NDVI does not, by itself, " +
                            "identify its cause.",
                    fontSize = 13.sp, color = Muted
                )
            }
        }

        Spacer(Modifier.height(22.dp))
        Text("POWERED BY SENTINEL-2 · COPERNICUS",
            modifier = Modifier.fillMaxWidth(),
            color = Muted, fontSize = 9.sp)
    }
}

@Composable
fun PlaceCard(
    emoji: String,
    title: String,
    subtitle: String,
    status: String,
    enabled: Boolean,
    onClick: (() -> Unit)?
) {
    Card(
        modifier = Modifier.fillMaxWidth().then(
            if (enabled && onClick != null)
                Modifier.clickable { onClick() }
            else Modifier
        ),
        shape = RoundedCornerShape(19.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Row(Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(48.dp)
                    .background(Background, RoundedCornerShape(14.dp)),
                contentAlignment = Alignment.Center
            ) { Text(emoji, fontSize = 24.sp) }

            Spacer(Modifier.width(13.dp))
            Column(Modifier.weight(1f)) {
                Text(title, fontWeight = FontWeight.Bold,
                    color = DarkGreen, fontSize = 15.sp)
                Text(subtitle, color = Muted, fontSize = 12.sp)
                Spacer(Modifier.height(6.dp))
                Text(status, color = if (enabled) Green else Color(0xFFD98239),
                    fontSize = 9.sp, fontWeight = FontWeight.Bold)
            }
            if (enabled) Text("→", color = Green, fontSize = 22.sp)
        }
    }
}

@Composable
fun ForestDetailScreen(data: ForestData, onBack: () -> Unit) {
    Column(
        Modifier.fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(22.dp)
    ) {
        Text("←  Back to places",
            color = Green,
            modifier = Modifier.clickable { onBack() }.padding(vertical = 8.dp))

        Spacer(Modifier.height(24.dp))
        Text("FOREST DEMO", color = Green,
            fontSize = 11.sp, letterSpacing = 1.5.sp)
        Spacer(Modifier.height(8.dp))
        Text("Vegetation analysis", fontSize = 29.sp,
            fontWeight = FontWeight.Bold, color = DarkGreen)
        Text("Sentinel-2 · L2A · 10 m resolution",
            fontSize = 13.sp, color = Muted)

        Spacer(Modifier.height(22.dp))

        Card(shape = RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = DarkGreen)) {
            Column(Modifier.padding(22.dp)) {
                Text("OBSERVED NDVI · HISTORICAL EXAMPLE", color = PaleGreen, fontSize = 11.sp)
                Text("%.3f".format(java.util.Locale.US, data.ndvi),
                    color = Color.White, fontSize = 43.sp,
                    fontWeight = FontWeight.Bold)
                Text("Observed on ${data.targetDate} · precomputed, not live data",
                    color = PaleGreen, fontSize = 13.sp)
                Spacer(Modifier.height(18.dp))
                Text(
                    "%+.1f%% vs historical baseline".format(
                        java.util.Locale.US, data.anomalyPercent
                    ),
                    color = Color(0xFFE6C99E),
                    fontWeight = FontWeight.Bold, fontSize = 15.sp
                )
                Text(
                    "Baseline NDVI: %.3f".format(
                        java.util.Locale.US, data.baseline
                    ),
                    color = Color.White, fontSize = 13.sp
                )
            }
        }

        Spacer(Modifier.height(24.dp))
        Text("NDVI over time", fontSize = 20.sp,
            fontWeight = FontWeight.Bold, color = DarkGreen)
        Text("2025 · observed values and historical baseline",
            fontSize = 12.sp, color = Muted)

        Spacer(Modifier.height(12.dp))
        NdviChart(data.observations)
        // BEFORE / AFTER
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = "Before / After",
                style = MaterialTheme.typography.titleLarge,
                color = DarkGreen
            )

            Text(
                text = "Confronto dell'NDVI tra due date di luglio 2025.",
                style = MaterialTheme.typography.bodyMedium,
                color = Muted
            )

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 24.dp, bottom = 24.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(Color.White)
                    .padding(18.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "How do we know?",
                    style = MaterialTheme.typography.titleLarge,
                    color = DarkGreen
                )

                Text(
                    text = "Da dove arrivano i dati",
                    style = MaterialTheme.typography.titleMedium,
                    color = Green
                )

                Text(
                    text = "L'analisi utilizza osservazioni del satellite Sentinel-2, " +
                            "prodotto Level-2A (L2A), che fornisce dati di riflettanza " +
                            "della superficie terrestre.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Muted
                )

                HorizontalDivider(color = Background)

                Text(
                    text = "Come calcoliamo l'NDVI",
                    style = MaterialTheme.typography.titleMedium,
                    color = Green
                )

                Text(
                    text = "L'NDVI è un indicatore basato sulla risposta della " +
                            "vegetazione nel rosso e nel vicino infrarosso.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Muted
                )

                Text(
                    text = "NDVI = (NIR - RED) / (NIR + RED)",
                    style = MaterialTheme.typography.titleMedium,
                    color = DarkGreen
                )

                Text(
                    text = "In questa analisi utilizziamo B08 per il vicino " +
                            "infrarosso (NIR) e B04 per il rosso (RED). " +
                            "La risoluzione spaziale delle bande è di 10 metri.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Muted
                )

                HorizontalDivider(color = Background)

                Text(
                    text = "Qualità dei dati",
                    style = MaterialTheme.typography.titleMedium,
                    color = Green
                )

                Text(
                    text = "La classificazione SCL di Sentinel-2 viene utilizzata " +
                            "per individuare pixel da escludere a causa di nuvole, " +
                            "ombre e altre condizioni non valide. Le osservazioni " +
                            "con una percentuale di pixel validi inferiore al 70% " +
                            "sono escluse dall'analisi storica.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Muted
                )

                HorizontalDivider(color = Background)

                Text(
                    text = "Cosa possiamo concludere?",
                    style = MaterialTheme.typography.titleMedium,
                    color = Green
                )

                Text(
                    text = "Una variazione dell'NDVI segnala un cambiamento " +
                            "nella risposta spettrale della superficie. Può dipendere " +
                            "dalla vegetazione, ma anche da condizioni ambientali, " +
                            "differenze di osservazione o pixel non confrontabili. " +
                            "Non dimostra da sola la presenza di un incendio, " +
                            "di un danno o di una causa specifica.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Muted
                )

                Text(
                    text = "Periodo analizzato: giugno–agosto 2023–2025. " +
                            "Questa demo utilizza dati storici, non un monitoraggio " +
                            "in tempo reale.",
                    style = MaterialTheme.typography.bodySmall,
                    color = Muted
                )
            }

            // Immagine precedente
            Text(
                text = "15 luglio 2025 · Prima",
                style = MaterialTheme.typography.titleMedium,
                color = DarkGreen
            )

            AssetImage(
                fileName = "visuals/forest_demo_ndvi_2025-07-15.png",
                contentDescription = "Mappa NDVI della foresta del 15 luglio 2025",
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.White)
            )

            // Immagine successiva
            Text(
                text = "17 luglio 2025 · Dopo",
                style = MaterialTheme.typography.titleMedium,
                color = DarkGreen
            )

            AssetImage(
                fileName = "visuals/forest_demo_ndvi_2025-07-17.png",
                contentDescription = "Mappa NDVI della foresta del 17 luglio 2025",
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.White)
            )

            // Mappa delle differenze
            Text(
                text = "Mappa delle variazioni",
                style = MaterialTheme.typography.titleMedium,
                color = DarkGreen
            )

            AssetImage(
                fileName = "visuals/forest_demo_ndvi_difference.png",
                contentDescription = "Mappa delle differenze NDVI tra le due date",
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.White)
            )

            Text(
                text = "Le variazioni dell'NDVI indicano differenze nella risposta " +
                        "spettrale della vegetazione. Da sole non dimostrano la presenza " +
                        "di danni né ne identificano la causa.",
                style = MaterialTheme.typography.bodySmall,
                color = Muted
            )
        }

        Spacer(Modifier.height(24.dp))
        Text("What does this mean?", fontSize = 20.sp,
            fontWeight = FontWeight.Bold, color = DarkGreen)
        Spacer(Modifier.height(8.dp))
        Text(
            "The observed NDVI was approximately " +
                    "%.1f%% ".format(java.util.Locale.US, data.anomalyPercent) +
                    "different from the historical baseline for this date. " +
                    "This indicates a difference in the vegetation index, " +
                    "not proof of a specific cause.",
            fontSize = 14.sp, lineHeight = 22.sp, color = Muted
        )

        Spacer(Modifier.height(24.dp))
        Text("DATA & METHODOLOGY", color = Green,
            fontSize = 11.sp, letterSpacing = 1.2.sp,
            fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(10.dp))
        Text(
            "Satellite: Sentinel-2\n" +
                    "Product: Level-2A\n" +
                    "Red band: B04\n" +
                    "Near-infrared band: B08\n" +
                    "Cloud mask: SCL\n" +
                    "NDVI = (NIR − RED) / (NIR + RED)\n" +
                    "Historical observations: ${data.historicalObservations}",
            fontSize = 13.sp, lineHeight = 23.sp, color = DarkGreen
        )
    }
}

@Composable
fun NdviChart(observations: List<NdviObservation>) {
    val valid = observations.filter {
        it.ndvi != null && it.baseline != null
    }

    if (valid.size < 2) {
        Text("Not enough observations to draw the chart.", color = Muted)
        return
    }

    val minValue = 0.70f
    val maxValue = 1.00f

    Column {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(10.dp).background(Green, CircleShape))
            Spacer(Modifier.width(6.dp))
            Text("Observed NDVI", fontSize = 11.sp, color = Muted)
            Spacer(Modifier.width(16.dp))
            Box(Modifier.size(10.dp).background(Orange, CircleShape))
            Spacer(Modifier.width(6.dp))
            Text("Baseline", fontSize = 11.sp, color = Muted)
        }

        Spacer(Modifier.height(10.dp))

        Canvas(
            modifier = Modifier.fillMaxWidth().height(190.dp)
                .background(Color.White, RoundedCornerShape(16.dp))
                .padding(12.dp)
        ) {
            val left = 8f
            val right = size.width - 8f
            val top = 8f
            val bottom = size.height - 8f
            val chartHeight = bottom - top
            val chartWidth = right - left

            fun y(value: Double): Float {
                val fraction = (
                        (value.toFloat() - minValue) /
                                (maxValue - minValue)
                        ).coerceIn(0f, 1f)
                return bottom - fraction * chartHeight
            }

            // Baseline values
            val baselinePath = Path()
            valid.forEachIndexed { index, item ->
                val x = left + chartWidth * index /
                        (valid.size - 1).toFloat()
                val yy = y(item.baseline!!)
                if (index == 0) baselinePath.moveTo(x, yy)
                else baselinePath.lineTo(x, yy)
            }

            drawPath(
                path = baselinePath,
                color = Orange,
                style = Stroke(width = 3f)
            )

            // Observed NDVI values
            val ndviPath = Path()
            valid.forEachIndexed { index, item ->
                val x = left + chartWidth * index /
                        (valid.size - 1).toFloat()
                val yy = y(item.ndvi!!)
                if (index == 0) ndviPath.moveTo(x, yy)
                else ndviPath.lineTo(x, yy)
            }

            drawPath(
                path = ndviPath,
                color = Green,
                style = Stroke(width = 4f)
            )
        }

        Spacer(Modifier.height(5.dp))
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(valid.first().date, fontSize = 10.sp, color = Muted)
            Text(valid.last().date, fontSize = 10.sp, color = Muted)
        }
    }
}

@Composable
private fun AssetImage(
    fileName: String,
    contentDescription: String,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current

    val bitmap = remember(fileName) {
        runCatching {
            context.assets.open(fileName).use { stream ->
                BitmapFactory.decodeStream(stream)?.asImageBitmap()
            }
        }.getOrNull()
    }

    if (bitmap != null) {
        Image(
            bitmap = bitmap,
            contentDescription = contentDescription,
            modifier = modifier,
            contentScale = ContentScale.Fit
        )
    } else {
        Text(
            text = "Immagine non disponibile",
            color = Muted,
            modifier = modifier.padding(12.dp)
        )
    }
}