package com.giovmar.earthpulse

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
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
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.CancellationException
import java.util.Locale

// Lati dell'area per il calore: il dato termico è a 30 m (misurato a 100 m).
val HEAT_SIDE_OPTIONS = listOf(4.0, 8.0, 12.0)
const val HEAT_DEFAULT_SIDE_KM = 8.0

// ------------------------------------------------------------------
// STATO
// ------------------------------------------------------------------

class HeatState {
    var info by mutableStateOf<HeatInfo?>(null)
    var error by mutableStateOf<String?>(null)
    var loading by mutableStateOf(true)

    val bitmaps = mutableStateMapOf<String, ImageBitmap>()
    val failures = mutableStateMapOf<String, String>()
}

/** Avvia subito la ricerca delle giornate estive (in parallelo all'analisi). */
@Composable
fun rememberHeatState(place: SelectedPlace, sideKm: Double): HeatState {
    val state = remember(place, sideKm) { HeatState() }
    LaunchedEffect(place, sideKm) {
        try {
            state.info = EarthPulseApi.fetchHeat(place.latitude, place.longitude, sideKm)
        } catch (e: CancellationException) {
            throw e
        } catch (e: ApiException) {
            state.error = e.message
        } catch (e: Exception) {
            state.error = "Dati sul calore non disponibili: ${e.message ?: e.javaClass.simpleName}"
        } finally {
            state.loading = false
        }
    }
    return state
}

@Composable
private fun rememberHeatImage(state: HeatState, url: String?): ImageBitmap? {
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
// SEZIONE "ISOLE DI CALORE"
// ------------------------------------------------------------------

@Composable
fun HeatSection(
    state: HeatState,
    sideKm: Double,
    shareTitle: String? = null,
    onSideChange: (Double) -> Unit
) {
    Spacer(Modifier.height(24.dp))
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            "Isole di calore",
            fontSize = 19.sp, fontWeight = FontWeight.Bold, color = DarkGreen,
            modifier = Modifier.weight(1f)
        )
        HEAT_SIDE_OPTIONS.forEach { option ->
            HeatChip(
                text = "${option.toInt()} km",
                selected = option == sideKm,
                onClick = { onSideChange(option) },
                modifier = Modifier.padding(start = 6.dp)
            )
        }
    }
    Text(
        "Dove le superfici si scaldano di più d'estate: temperatura da Landsat su " +
            "${sideKm.toInt()} × ${sideKm.toInt()} km attorno al luogo.",
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
                Text("Cerchiamo giornate estive senza nuvole…", fontSize = 13.sp, color = Muted)
            }
        }

        state.error != null -> InfoBox {
            Text(state.error ?: "", fontSize = 13.sp, color = Muted)
        }

        info == null -> InfoBox {
            Text("Nessun dato sul calore per quest'area.", fontSize = 13.sp, color = Muted)
        }

        else -> HeatContent(state, info, shareTitle)
    }
}

@Composable
private fun HeatContent(state: HeatState, info: HeatInfo, shareTitle: String?) {
    // "anomaly" = anomalia estiva tipica; "temperature" = giornata più recente
    var mode by rememberSaveable { mutableStateOf("anomaly") }
    val isAnomaly = mode == "anomaly"

    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        HeatChip("Anomalia estiva", isAnomaly, { mode = "anomaly" })
        HeatChip("Temperatura · ${formatDate(info.latestDate)}", !isAnomaly, { mode = "temperature" })
    }
    Spacer(Modifier.height(10.dp))

    val heatUrl = if (isAnomaly) info.anomalyUrl else info.temperatureUrl
    val heatLabel = if (isAnomaly) "Anomalia estiva" else "Superficie · ${formatDate(info.latestDate)}"
    val heatImage = rememberHeatImage(state, heatUrl)
    val rgbImage = rememberHeatImage(state, info.rgbUrl)
    val rgbLabel = info.rgbDate?.let { "Colori reali · ${formatDate(it)}" } ?: "Colori reali"

    if (info.rgbUrl != null) {
        // A sinistra la città vista dal satellite, a destra il calore.
        BeforeAfterSlider(
            before = rgbImage,
            after = heatImage,
            beforeLabel = rgbLabel,
            afterLabel = heatLabel,
            areaFraction = 0f,
            failure = state.failures[heatUrl] ?: state.failures[info.rgbUrl]
        )
        Text(
            "Trascina la linea bianca: a sinistra la città, a destra il calore.",
            fontSize = 12.sp, color = Muted,
            modifier = Modifier.padding(top = 6.dp)
        )
    } else {
        SingleImage(heatImage, heatLabel, 0f, state.failures[heatUrl])
    }

    val stops = if (isAnomaly) info.anomalyStops else info.temperatureStops
    val labels = (if (isAnomaly) info.anomalyLabels else info.temperatureLabels) + List(3) { "" }
    if (stops.size >= 2) {
        Spacer(Modifier.height(10.dp))
        GradientLegend(
            stops = stops,
            leftLabel = labels[0],
            centerLabel = labels[1],
            rightLabel = labels[2],
            invalidLabel = if (info.waterColor != null) "Mare, laghi, fiumi" else null,
            invalidColor = info.waterColor ?: Color.Transparent
        )
    }

    info.message?.let { message ->
        Spacer(Modifier.height(10.dp))
        InfoBox {
            Column {
                Text(message, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = DarkGreen)
                Text(info.caveat, fontSize = 11.sp, lineHeight = 15.sp, color = Muted,
                    modifier = Modifier.padding(top = 6.dp))
            }
        }
    }

    if (shareTitle != null && heatImage != null) {
        ShareButton {
            ShareContent(
                title = shareTitle,
                subtitle = "Area ${info.sideKm.toInt()} × ${info.sideKm.toInt()} km",
                layerLabel = if (isAnomaly) "Isole di calore" else "Temperatura della superficie",
                before = rgbImage,
                beforeLabel = if (rgbImage != null) rgbLabel else null,
                after = heatImage,
                afterLabel = heatLabel,
                highlight = info.message,
                stops = stops,
                legendLabels = labels.filter { it.isNotBlank() },
                attribution = info.attribution
            )
        }
    }

    Spacer(Modifier.height(10.dp))
    Text(info.caption, fontSize = 12.sp, lineHeight = 17.sp, color = Muted)
    if (info.days.isNotEmpty()) {
        val days = info.days.joinToString(" · ") { day ->
            val median = day.landMedianC?.let { String.format(Locale.ITALIAN, " (%.1f °C)", it) } ?: ""
            formatDate(day.date) + median
        }
        Text(
            "Giornate usate (mediana della terraferma): $days",
            fontSize = 11.sp, lineHeight = 15.sp, color = Muted,
            modifier = Modifier.padding(top = 4.dp)
        )
    }
    Text(info.attribution, fontSize = 10.sp, color = Muted, modifier = Modifier.padding(top = 6.dp))
}

@Composable
private fun HeatChip(
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
