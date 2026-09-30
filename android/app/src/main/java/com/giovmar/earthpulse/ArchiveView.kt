package com.giovmar.earthpulse

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.CancellationException

// Lati dell'area per l'archivio Landsat (pixel di 30 m).
val ARCHIVE_SIDE_OPTIONS = listOf(3.0, 6.0, 12.0)
const val ARCHIVE_DEFAULT_SIDE_KM = 6.0

// ------------------------------------------------------------------
// STATO
// ------------------------------------------------------------------

class ArchiveState {
    var info by mutableStateOf<ArchiveInfo?>(null)
    var error by mutableStateOf<String?>(null)
    var loading by mutableStateOf(true)
    var beforeYear by mutableStateOf<Int?>(null)
    var afterYear by mutableStateOf<Int?>(null)

    val bitmaps = mutableStateMapOf<String, ImageBitmap>()
    val failures = mutableStateMapOf<String, String>()
}

@Composable
fun rememberArchiveState(place: SelectedPlace, sideKm: Double, active: Boolean = true): ArchiveState {
    val state = remember(place, sideKm) { ArchiveState() }
    LaunchedEffect(place, sideKm, active) {
        // Si carica solo quando l'utente apre la sezione (meno carico sul server).
        if (!active) return@LaunchedEffect
        state.loading = true
        try {
            val info = EarthPulseApi.fetchArchive(place.latitude, place.longitude, sideKm)
            state.beforeYear = info.defaultBefore
            state.afterYear = info.defaultAfter
            state.info = info
        } catch (e: CancellationException) {
            throw e
        } catch (e: ApiException) {
            state.error = e.message
        } catch (e: Exception) {
            state.error = "Archivio non disponibile: ${e.message ?: e.javaClass.simpleName}"
        } finally {
            state.loading = false
        }
    }
    return state
}

@Composable
private fun rememberArchiveImage(state: ArchiveState, url: String?): ImageBitmap? {
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
// SEZIONE "NEL TEMPO"
// ------------------------------------------------------------------

@Composable
fun ArchiveSection(
    state: ArchiveState,
    sideKm: Double,
    shareTitle: String? = null,
    active: Boolean = true,
    onActivate: () -> Unit = {},
    onSideChange: (Double) -> Unit
) {
    Spacer(Modifier.height(24.dp))
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            "Nel tempo",
            fontSize = 19.sp, fontWeight = FontWeight.Bold, color = DarkGreen,
            modifier = Modifier.weight(1f)
        )
        ARCHIVE_SIDE_OPTIONS.forEach { option ->
            SmallChip(
                text = "${option.toInt()} km",
                selected = option == sideKm,
                onClick = { onSideChange(option) },
                modifier = Modifier.padding(start = 6.dp)
            )
        }
    }
    Text(
        "Com'era quest'area dal 1984 a oggi, con l'archivio Landsat " +
            "(${sideKm.toInt()} × ${sideKm.toInt()} km).",
        fontSize = 12.sp, lineHeight = 17.sp, color = Muted
    )
    Spacer(Modifier.height(10.dp))

    val info = state.info
    when {
        !active -> androidx.compose.material3.OutlinedButton(
            onClick = onActivate,
            shape = androidx.compose.foundation.shape.RoundedCornerShape(14.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Mostra com'era dal 1984", color = Green)
        }

        state.loading -> InfoBox {
            Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(
                    modifier = Modifier.size(22.dp), color = Green, strokeWidth = 2.dp
                )
                Spacer(Modifier.width(12.dp))
                Text("Sfogliamo 40 anni di archivio…", fontSize = 13.sp, color = Muted)
            }
        }

        state.error != null -> InfoBox {
            Text(state.error ?: "", fontSize = 13.sp, color = Muted)
        }

        info == null || info.years.isEmpty() -> InfoBox {
            Text("Nessuna immagine d'archivio per quest'area.", fontSize = 13.sp, color = Muted)
        }

        else -> ArchiveContent(state, info, shareTitle)
    }
}

@Composable
private fun ArchiveContent(state: ArchiveState, info: ArchiveInfo, shareTitle: String?) {
    val layers = info.layers
    if (layers.isEmpty()) return
    var layerKey by rememberSaveable { mutableStateOf(layers.first().key) }
    val layer = layers.firstOrNull { it.key == layerKey } ?: layers.first()

    Row(
        Modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        layers.forEach { option ->
            SmallChip(option.label, option.key == layer.key, { layerKey = option.key })
        }
    }
    Spacer(Modifier.height(8.dp))

    val before = state.beforeYear ?: info.defaultBefore
    val after = state.afterYear ?: info.defaultAfter
    YearChips("Prima", info.years, before) { state.beforeYear = it }
    Spacer(Modifier.height(6.dp))
    YearChips("Dopo", info.years, after) { state.afterYear = it }
    Spacer(Modifier.height(10.dp))

    val beforeUrl = info.imageUrl(before, layer.key)
    val afterUrl = info.imageUrl(after, layer.key)
    val beforeImage = rememberArchiveImage(state, beforeUrl)
    val afterImage = rememberArchiveImage(state, afterUrl)
    val beforeLabel = "Prima · $before"
    val afterLabel = "Dopo · $after"

    BeforeAfterSlider(
        before = beforeImage,
        after = afterImage,
        beforeLabel = beforeLabel,
        afterLabel = afterLabel,
        areaFraction = 0f,
        failure = state.failures[afterUrl] ?: state.failures[beforeUrl]
    )
    Text(
        "$before: ${info.sensors[before] ?: "Landsat"} · $after: ${info.sensors[after] ?: "Landsat"}",
        fontSize = 12.sp, color = Muted,
        modifier = Modifier.padding(top = 6.dp)
    )

    if (layer.stops.size >= 2) {
        Spacer(Modifier.height(10.dp))
        val labels = layer.legendLabels + List(3) { "" }
        GradientLegend(
            stops = layer.stops,
            leftLabel = labels[0],
            centerLabel = labels[1],
            rightLabel = labels[2]
        )
    }

    if (shareTitle != null && beforeImage != null && afterImage != null) {
        ShareButton {
            ShareContent(
                title = shareTitle,
                subtitle = "Archivio Landsat · ${info.sideKm.toInt()} × ${info.sideKm.toInt()} km",
                layerLabel = layer.label,
                before = beforeImage,
                beforeLabel = beforeLabel,
                after = afterImage,
                afterLabel = afterLabel,
                highlight = "${kotlin.math.abs(after - before)} anni di cambiamenti visti dallo spazio",
                stops = layer.stops,
                legendLabels = layer.legendLabels,
                attribution = info.attribution
            )
        }
    }

    Spacer(Modifier.height(10.dp))
    Text(layer.caption, fontSize = 12.sp, lineHeight = 17.sp, color = Muted)
    layer.formula?.let {
        Text(it, fontSize = 12.sp, color = DarkGreen, fontFamily = FontFamily.Monospace,
            modifier = Modifier.padding(top = 4.dp))
    }
    Text(info.caption, fontSize = 11.sp, lineHeight = 15.sp, color = Muted,
        modifier = Modifier.padding(top = 6.dp))
    Text(info.attribution, fontSize = 10.sp, color = Muted, modifier = Modifier.padding(top = 6.dp))
}
