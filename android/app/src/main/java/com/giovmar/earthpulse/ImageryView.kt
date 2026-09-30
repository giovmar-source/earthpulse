package com.giovmar.earthpulse

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.CancellationException

// ------------------------------------------------------------------
// STATO: scene e immagini scaricate
// ------------------------------------------------------------------

enum class ImageryLayer(val label: String) {
    RGB("Colori reali"),
    NDVI("NDVI"),
    CHANGE("Variazione")
}

class ImageryState {
    var scenes by mutableStateOf<ImageryScenes?>(null)
    var error by mutableStateOf<String?>(null)
    var loading by mutableStateOf(true)

    // Immagini già scaricate (per url) ed eventuali errori.
    val bitmaps = mutableStateMapOf<String, ImageBitmap>()
    val failures = mutableStateMapOf<String, String>()
}

/**
 * Avvia subito la ricerca delle scene, in parallelo all'analisi NDVI,
 * così le immagini arrivano insieme (o prima) del risultato numerico.
 */
@Composable
fun rememberImageryState(place: SelectedPlace, sideKm: Double = IMAGERY_SIDE_KM): ImageryState {
    val state = remember(place, sideKm) { ImageryState() }

    LaunchedEffect(place, sideKm) {
        try {
            state.scenes = EarthPulseApi.fetchImageryScenes(place.latitude, place.longitude, sideKm)
        } catch (e: CancellationException) {
            throw e
        } catch (e: ApiException) {
            state.error = e.message
        } catch (e: Exception) {
            state.error = "Immagini non disponibili: ${e.message ?: e.javaClass.simpleName}"
        } finally {
            state.loading = false
        }
    }
    return state
}

/** Scarica (una sola volta) l'immagine indicata e la restituisce quando è pronta. */
@Composable
private fun rememberImage(state: ImageryState, url: String?): ImageBitmap? {
    LaunchedEffect(url) {
        if (url == null || state.bitmaps.containsKey(url) || state.failures.containsKey(url)) {
            return@LaunchedEffect
        }
        try {
            state.bitmaps[url] = EarthPulseApi.fetchImage(url)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            state.failures[url] = e.message ?: "errore"
        }
    }
    return url?.let { state.bitmaps[it] }
}

// ------------------------------------------------------------------
// SEZIONE "DALL'ALTO"
// ------------------------------------------------------------------

@Composable
fun ImagerySection(
    state: ImageryState,
    sideKm: Double = IMAGERY_SIDE_KM,
    onSideChange: ((Double) -> Unit)? = null
) {
    Spacer(Modifier.height(24.dp))
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            "Dall'alto",
            fontSize = 19.sp, fontWeight = FontWeight.Bold, color = DarkGreen,
            modifier = Modifier.weight(1f)
        )
        // Dimensione dell'area mostrata
        if (onSideChange != null) {
            listOf(1.0, 2.0, 3.0).forEach { option ->
                val selected = option == sideKm
                Surface(
                    shape = RoundedCornerShape(50),
                    color = if (selected) Green else Color.White,
                    modifier = Modifier
                        .padding(start = 6.dp)
                        .clickable { onSideChange(option) }
                ) {
                    Text(
                        "${option.toInt()} km",
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                        color = if (selected) Color.White else DarkGreen,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
        }
    }
    Text(
        if (sideKm <= 1.0)
            "Immagini Sentinel-2 dell'area analizzata (1 × 1 km). Ogni pixel " +
                    "è 10 m: l'immagine è ingrandita, non più dettagliata."
        else
            "Immagini Sentinel-2 di un'area di ${sideKm.toInt()} × ${sideKm.toInt()} km. " +
                    "Il riquadro tratteggiato è l'area di 1 km analizzata.",
        fontSize = 12.sp, lineHeight = 17.sp, color = Muted
    )
    Spacer(Modifier.height(10.dp))

    val scenes = state.scenes
    val after = scenes?.after

    when {
        state.loading -> InfoBox {
            Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(
                    modifier = Modifier.size(22.dp), color = Green, strokeWidth = 2.dp
                )
                Spacer(Modifier.width(12.dp))
                Text(
                    "Cerchiamo immagini senza nuvole…",
                    fontSize = 13.sp, color = Muted
                )
            }
        }

        state.error != null -> InfoBox {
            Text(state.error ?: "", fontSize = 13.sp, color = Muted)
        }

        scenes == null || after == null -> InfoBox {
            Text(
                "Nessuna immagine abbastanza nitida (senza nuvole) nel periodo recente.",
                fontSize = 13.sp, color = Muted
            )
        }

        else -> ImageryContent(state, scenes, after)
    }
}

@Composable
internal fun ImageryContent(
    state: ImageryState,
    scenes: ImageryScenes,
    after: SceneImages,
    showAnalysisArea: Boolean = true
) {
    val before = scenes.before
    var selectedLayer by rememberSaveable { mutableStateOf(ImageryLayer.RGB) }

    val available = buildList {
        add(ImageryLayer.RGB)
        add(ImageryLayer.NDVI)
        if (after.diffUrl != null) add(ImageryLayer.CHANGE)
    }
    val layer = if (selectedLayer in available) selectedLayer else ImageryLayer.RGB

    // Selettore del livello
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        available.forEach { option ->
            val selected = option == layer
            Surface(
                shape = RoundedCornerShape(50),
                color = if (selected) DarkGreen else Color.White,
                modifier = Modifier.clickable { selectedLayer = option }
            ) {
                Text(
                    option.label,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                    color = if (selected) Color.White else DarkGreen,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
    }
    Spacer(Modifier.height(10.dp))

    // Riquadro dell'area analizzata (1 km): solo per l'analisi di un luogo.
    val areaFraction =
        if (showAnalysisArea) (ANALYSIS_SIDE_KM / scenes.sideKm).toFloat() else 0f
    val beforeLabel = before?.let { "Prima · ${formatDate(it.date)}" }
    val afterLabel = "Dopo · ${formatDate(after.date)}"

    when (layer) {
        ImageryLayer.RGB, ImageryLayer.NDVI -> {
            val afterUrl = if (layer == ImageryLayer.RGB) after.rgbUrl else after.ndviUrl
            val beforeUrl = before?.let { if (layer == ImageryLayer.RGB) it.rgbUrl else it.ndviUrl }
            val afterImage = rememberImage(state, afterUrl)
            val beforeImage = rememberImage(state, beforeUrl)

            if (before != null && beforeLabel != null) {
                BeforeAfterSlider(
                    before = beforeImage,
                    after = afterImage,
                    beforeLabel = beforeLabel,
                    afterLabel = afterLabel,
                    areaFraction = areaFraction,
                    failure = state.failures[afterUrl] ?: beforeUrl?.let { state.failures[it] }
                )
                Text(
                    "Trascina la linea bianca per confrontare le due date.",
                    fontSize = 12.sp, color = Muted,
                    modifier = Modifier.padding(top = 6.dp)
                )
            } else {
                SingleImage(afterImage, afterLabel, areaFraction, state.failures[afterUrl])
            }

            if (layer == ImageryLayer.NDVI) {
                Spacer(Modifier.height(10.dp))
                GradientLegend(
                    stops = scenes.ndviStops,
                    leftLabel = "Suolo, acqua",
                    centerLabel = "Vegetazione rada",
                    rightLabel = "Vegetazione densa"
                )
            }
        }

        ImageryLayer.CHANGE -> {
            val url = after.diffUrl
            val image = rememberImage(state, url)
            SingleImage(
                image,
                before?.let { "${formatDate(it.date)} → ${formatDate(after.date)}" } ?: afterLabel,
                areaFraction,
                url?.let { state.failures[it] }
            )
            Spacer(Modifier.height(10.dp))
            GradientLegend(
                stops = scenes.diffStops,
                leftLabel = "NDVI in calo",
                centerLabel = "Stabile",
                rightLabel = "NDVI in aumento"
            )
        }
    }

    Spacer(Modifier.height(10.dp))
    Text(
        when (layer) {
            ImageryLayer.RGB ->
                "Come l'occhio vedrebbe l'area dallo spazio (bande B04, B03, B02). " +
                        "I colori della data precedente sono armonizzati a quelli della " +
                        "più recente (luce, foschia): solo per la visualizzazione, " +
                        "NDVI e variazione usano i dati originali."
            ImageryLayer.NDVI ->
                "Indice di vegetazione pixel per pixel (10 m). In grigio i pixel " +
                        "esclusi: nuvole, ombre, neve o dati mancanti."
            ImageryLayer.CHANGE ->
                "Differenza di NDVI tra le due date, solo dove entrambe le immagini " +
                        "sono valide. Un calo non indica da solo la causa: stagione, " +
                        "sfalci, siccità, tagli o incendi possono produrlo. Lungo " +
                        "strade e fiumi possono comparire sottili bordi rossi e verdi " +
                        "dovuti al piccolo disallineamento tra le acquisizioni."
        },
        fontSize = 12.sp, lineHeight = 17.sp, color = Muted
    )

    scenes.messages.forEach { message ->
        Text("⚠  $message", fontSize = 12.sp, color = Color(0xFF8A4B14),
            modifier = Modifier.padding(top = 6.dp))
    }

    Text(
        scenes.attribution,
        fontSize = 10.sp, color = Muted,
        modifier = Modifier.padding(top = 6.dp)
    )
}

// ------------------------------------------------------------------
// COMPONENTI GRAFICI
// ------------------------------------------------------------------

/** Due immagini sovrapposte: a sinistra della linea "prima", a destra "dopo". */
@Composable
private fun BeforeAfterSlider(
    before: ImageBitmap?,
    after: ImageBitmap?,
    beforeLabel: String,
    afterLabel: String,
    areaFraction: Float,
    failure: String?
) {
    var fraction by remember { mutableFloatStateOf(0.5f) }

    Box(
        Modifier
            .fillMaxWidth()
            .aspectRatio(1f)
            .clip(RoundedCornerShape(16.dp))
            .background(Color(0xFF1B2A24))
            .pointerInput(Unit) {
                detectTapGestures { offset ->
                    fraction = (offset.x / size.width).coerceIn(0f, 1f)
                }
            }
            .pointerInput(Unit) {
                detectHorizontalDragGestures { change, _ ->
                    change.consume()
                    fraction = (change.position.x / size.width).coerceIn(0f, 1f)
                }
            }
    ) {
        if (after != null) {
            Image(
                bitmap = after,
                contentDescription = afterLabel,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop
            )
        }
        if (before != null) {
            Image(
                bitmap = before,
                contentDescription = beforeLabel,
                modifier = Modifier
                    .fillMaxSize()
                    .drawWithContent {
                        clipRect(right = size.width * fraction) {
                            this@drawWithContent.drawContent()
                        }
                    },
                contentScale = ContentScale.Crop
            )
        }

        ImageStatus(ready = before != null && after != null, failure = failure)
        AnalysisAreaOverlay(areaFraction)

        // Linea e maniglia del cursore
        Canvas(Modifier.fillMaxSize()) {
            val x = size.width * fraction
            drawLine(Color.White, Offset(x, 0f), Offset(x, size.height), strokeWidth = 5f)
            drawCircle(Color.White, radius = 24f, center = Offset(x, size.height / 2))
            drawCircle(
                DarkGreen, radius = 24f, center = Offset(x, size.height / 2),
                style = Stroke(width = 4f)
            )
        }

        CornerLabel(beforeLabel, Modifier.align(Alignment.TopStart))
        CornerLabel(afterLabel, Modifier.align(Alignment.TopEnd))
    }
}

@Composable
private fun SingleImage(
    image: ImageBitmap?,
    label: String,
    areaFraction: Float,
    failure: String?
) {
    Box(
        Modifier
            .fillMaxWidth()
            .aspectRatio(1f)
            .clip(RoundedCornerShape(16.dp))
            .background(Color(0xFF1B2A24))
    ) {
        if (image != null) {
            Image(
                bitmap = image,
                contentDescription = label,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop
            )
        }
        ImageStatus(ready = image != null, failure = failure)
        AnalysisAreaOverlay(areaFraction)
        CornerLabel(label, Modifier.align(Alignment.TopStart))
    }
}

@Composable
private fun ImageStatus(ready: Boolean, failure: String?) {
    if (ready) return
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        if (failure != null) {
            Text(
                "Immagine non disponibile:\n$failure",
                color = Color.White, fontSize = 12.sp,
                modifier = Modifier.padding(24.dp)
            )
        } else {
            CircularProgressIndicator(color = Color.White)
        }
    }
}

/** Riquadro tratteggiato dell'area analizzata (1 km), al centro. */
@Composable
private fun AnalysisAreaOverlay(areaFraction: Float) {
    // Nessun riquadro se disattivato o se l'immagine coincide con l'area.
    if (areaFraction <= 0f || areaFraction >= 0.99f) return
    Canvas(Modifier.fillMaxSize()) {
        val side = size.minDimension * areaFraction
        drawRect(
            color = Color.White,
            topLeft = Offset((size.width - side) / 2, (size.height - side) / 2),
            size = Size(side, side),
            style = Stroke(
                width = 3f,
                pathEffect = PathEffect.dashPathEffect(floatArrayOf(14f, 10f))
            )
        )
    }
}

@Composable
private fun CornerLabel(text: String, modifier: Modifier) {
    Text(
        text,
        modifier = modifier
            .padding(8.dp)
            .background(Color.Black.copy(alpha = 0.55f), RoundedCornerShape(8.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        color = Color.White,
        fontSize = 11.sp,
        fontWeight = FontWeight.SemiBold
    )
}

@Composable
private fun GradientLegend(
    stops: List<ColorStop>,
    leftLabel: String,
    centerLabel: String,
    rightLabel: String
) {
    if (stops.size < 2) return
    val min = stops.first().value
    val max = stops.last().value
    val colorStops = stops.map { stop ->
        ((stop.value - min) / (max - min)).coerceIn(0f, 1f) to stop.color
    }.toTypedArray()

    Column {
        Box(
            Modifier
                .fillMaxWidth()
                .height(12.dp)
                .clip(RoundedCornerShape(6.dp))
                .background(Brush.horizontalGradient(*colorStops))
        )
        Spacer(Modifier.height(4.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(leftLabel, fontSize = 11.sp, color = Muted)
            Text(centerLabel, fontSize = 11.sp, color = Muted)
            Text(rightLabel, fontSize = 11.sp, color = Muted)
        }
        Row(verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.padding(top = 4.dp)) {
            Box(
                Modifier
                    .size(10.dp)
                    .background(Color(0xFFB4B4B4), RoundedCornerShape(2.dp))
            )
            Text("  Non valido (nuvole, ombre, dati mancanti)", fontSize = 11.sp, color = Muted)
        }
    }
}

@Composable
private fun InfoBox(content: @Composable () -> Unit) {
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Box(
            Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) { content() }
    }
}
