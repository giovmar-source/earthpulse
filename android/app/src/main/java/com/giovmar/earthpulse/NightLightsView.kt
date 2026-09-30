package com.giovmar.earthpulse

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.CancellationException

// Lati dell'area per le luci notturne: i pixel VIIRS sono ~500 m,
// quindi servono aree molto più grandi delle immagini Sentinel-2.
val NIGHT_SIDE_OPTIONS = listOf(30.0, 60.0, 120.0)
const val NIGHT_DEFAULT_SIDE_KM = 60.0

// ------------------------------------------------------------------
// STATO
// ------------------------------------------------------------------

class NightLightsState {
    var info by mutableStateOf<NightLightsInfo?>(null)
    var error by mutableStateOf<String?>(null)
    var loading by mutableStateOf(true)
    var beforeYear by mutableStateOf<Int?>(null)
    var afterYear by mutableStateOf<Int?>(null)
    var comparison by mutableStateOf<NightLightsComparison?>(null)

    val bitmaps = mutableStateMapOf<String, ImageBitmap>()
    val failures = mutableStateMapOf<String, String>()
}

/** Avvia subito la richiesta degli anni disponibili (in parallelo all'analisi). */
@Composable
fun rememberNightLightsState(place: SelectedPlace, sideKm: Double): NightLightsState {
    val state = remember(place, sideKm) { NightLightsState() }
    LaunchedEffect(place, sideKm) {
        try {
            val info = EarthPulseApi.fetchNightLights(place.latitude, place.longitude, sideKm)
            state.beforeYear = info.defaultBefore
            state.afterYear = info.defaultAfter
            state.info = info
        } catch (e: CancellationException) {
            throw e
        } catch (e: ApiException) {
            state.error = e.message
        } catch (e: Exception) {
            state.error = "Luci notturne non disponibili: ${e.message ?: e.javaClass.simpleName}"
        } finally {
            state.loading = false
        }
    }
    return state
}

@Composable
private fun rememberNightImage(state: NightLightsState, url: String?): ImageBitmap? {
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
// SEZIONE "DI NOTTE"
// ------------------------------------------------------------------

@Composable
fun NightLightsSection(
    state: NightLightsState,
    sideKm: Double,
    onSideChange: (Double) -> Unit
) {
    Spacer(Modifier.height(24.dp))
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            "Di notte",
            fontSize = 19.sp, fontWeight = FontWeight.Bold, color = DarkGreen,
            modifier = Modifier.weight(1f)
        )
        NIGHT_SIDE_OPTIONS.forEach { option ->
            SmallChip(
                text = "${option.toInt()} km",
                selected = option == sideKm,
                onClick = { onSideChange(option) },
                modifier = Modifier.padding(start = 6.dp)
            )
        }
    }
    Text(
        "Luci notturne NASA Black Marble su un'area di ${sideKm.toInt()} × " +
            "${sideKm.toInt()} km attorno al luogo: confronta due anni.",
        fontSize = 12.sp, lineHeight = 17.sp, color = Muted
    )
    Spacer(Modifier.height(10.dp))

    val info = state.info
    when {
        state.loading -> InfoBox {
            Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(
                    modifier = Modifier.size(22.dp), color = Green, strokeWidth = 2.dp
                )
                Spacer(Modifier.width(12.dp))
                Text("Cerchiamo gli anni disponibili…", fontSize = 13.sp, color = Muted)
            }
        }

        state.error != null -> InfoBox {
            Text(state.error ?: "", fontSize = 13.sp, color = Muted)
        }

        info == null || info.years.isEmpty() -> InfoBox {
            Text("Nessun dato di luci notturne per quest'area.", fontSize = 13.sp, color = Muted)
        }

        else -> NightLightsContent(state, info)
    }
}

@Composable
private fun NightLightsContent(state: NightLightsState, info: NightLightsInfo) {
    val before = state.beforeYear ?: info.defaultBefore
    val after = state.afterYear ?: info.defaultAfter

    YearChips("Prima", info.years, before) { state.beforeYear = it; state.comparison = null }
    Spacer(Modifier.height(6.dp))
    YearChips("Dopo", info.years, after) { state.afterYear = it; state.comparison = null }
    Spacer(Modifier.height(10.dp))

    val beforeUrl = info.imageUrl(before)
    val afterUrl = info.imageUrl(after)
    val beforeImage = rememberNightImage(state, beforeUrl)
    val afterImage = rememberNightImage(state, afterUrl)

    BeforeAfterSlider(
        before = beforeImage,
        after = afterImage,
        beforeLabel = "Prima · $before",
        afterLabel = "Dopo · $after",
        areaFraction = 0f,
        failure = state.failures[afterUrl] ?: state.failures[beforeUrl]
    )
    Text(
        if (beforeImage == null || afterImage == null)
            "La prima apertura di un anno richiede circa 10–20 secondi."
        else "Trascina la linea bianca per confrontare i due anni.",
        fontSize = 12.sp, color = Muted,
        modifier = Modifier.padding(top = 6.dp)
    )

    // Numeri del confronto: chiesti quando entrambe le immagini sono pronte
    // (il server ha già i dati in memoria, quindi la risposta è immediata).
    val ready = beforeImage != null && afterImage != null
    LaunchedEffect(ready, before, after) {
        if (!ready || before == after) return@LaunchedEffect
        try {
            state.comparison = EarthPulseApi.fetchNightLightsComparison(
                info.compareUrl(before, after)
            )
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            state.comparison = null   // i numeri sono un extra: nessun errore mostrato
        }
    }

    state.comparison?.let { comparison ->
        Spacer(Modifier.height(10.dp))
        InfoBox {
            Column {
                Text(comparison.message, fontSize = 14.sp, fontWeight = FontWeight.SemiBold,
                    color = DarkGreen)
                val litBefore = comparison.litBefore
                val litAfter = comparison.litAfter
                if (litBefore != null && litAfter != null) {
                    Text(
                        "Terraferma illuminata: ${litBefore.toInt()}% → ${litAfter.toInt()}%",
                        fontSize = 12.sp, color = Muted, modifier = Modifier.padding(top = 4.dp)
                    )
                }
                Text(comparison.caveat, fontSize = 11.sp, lineHeight = 15.sp, color = Muted,
                    modifier = Modifier.padding(top = 6.dp))
            }
        }
    }

    if (info.stops.size >= 2) {
        Spacer(Modifier.height(10.dp))
        val labels = info.legendLabels + List(3) { "" }
        GradientLegend(
            stops = info.stops,
            leftLabel = labels[0],
            centerLabel = labels[1],
            rightLabel = labels[2],
            invalidLabel = if (info.seaColor != null) "Mare" else null,
            invalidColor = info.seaColor ?: Color.Transparent
        )
    }

    Spacer(Modifier.height(10.dp))
    Text(info.caption, fontSize = 12.sp, lineHeight = 17.sp, color = Muted)
    Text(info.attribution, fontSize = 10.sp, color = Muted,
        modifier = Modifier.padding(top = 6.dp))
}

@Composable
private fun YearChips(label: String, years: List<Int>, selected: Int, onSelect: (Int) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(label, fontSize = 12.sp, color = Muted, fontWeight = FontWeight.SemiBold,
            modifier = Modifier.width(44.dp))
        Row(
            Modifier.horizontalScroll(rememberScrollState(years.indexOf(selected).coerceAtLeast(0) * 150)),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            years.forEach { year ->
                SmallChip(year.toString(), year == selected, { onSelect(year) })
            }
        }
    }
}

@Composable
private fun SmallChip(
    text: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        shape = RoundedCornerShape(50),
        color = if (selected) DarkGreen else Color.White,
        modifier = modifier.clickable { onClick() }
    ) {
        Text(
            text,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
            color = if (selected) Color.White else DarkGreen,
            fontSize = 12.sp,
            fontWeight = FontWeight.SemiBold
        )
    }
}
