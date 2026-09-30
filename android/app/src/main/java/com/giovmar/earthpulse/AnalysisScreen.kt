package com.giovmar.earthpulse

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

// ------------------------------------------------------------------
// STATO DELLA SCHERMATA
// ------------------------------------------------------------------

sealed interface AnalysisUiState {
    data object Loading : AnalysisUiState
    data class Error(val message: String) : AnalysisUiState
    data class Success(val analysis: PlaceAnalysis) : AnalysisUiState
}

@Composable
fun AnalysisScreen(
    place: SelectedPlace,
    onBack: () -> Unit,
    onMethodologyClick: () -> Unit
) {
    var attempt by remember { mutableIntStateOf(0) }
    var state by remember(place) {
        mutableStateOf<AnalysisUiState>(AnalysisUiState.Loading)
    }

    // Le immagini "dall'alto" si caricano in parallelo all'analisi.
    var imagerySideKm by rememberSaveable { mutableStateOf(IMAGERY_SIDE_KM) }
    val imagery = rememberImageryState(place, imagerySideKm)

    // Parte all'apertura e a ogni "Riprova".
    LaunchedEffect(place, attempt) {
        state = AnalysisUiState.Loading
        state = try {
            AnalysisUiState.Success(
                EarthPulseApi.analyzePlace(place.latitude, place.longitude)
            )
        } catch (e: CancellationException) {
            throw e // schermata chiusa: nessun aggiornamento
        } catch (e: ApiException) {
            AnalysisUiState.Error(e.message ?: "Errore sconosciuto.")
        } catch (e: Exception) {
            AnalysisUiState.Error(
                "Risposta del server non leggibile: ${e.message ?: e.javaClass.simpleName}"
            )
        }
    }

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
            "ANALISI DEL LUOGO",
            color = Green, fontSize = 11.sp, letterSpacing = 1.5.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(Modifier.height(6.dp))
        Text(
            place.label ?: formatCoordinates(place),
            fontSize = 24.sp, fontWeight = FontWeight.Bold, color = DarkGreen
        )
        if (place.label != null) {
            Text(formatCoordinates(place), fontSize = 13.sp, color = Muted)
        }
        Text(
            "Area ≈ 1 × 1 km · Sentinel-2 L2A · 10 m",
            fontSize = 13.sp, color = Muted
        )
        Spacer(Modifier.height(22.dp))

        when (val s = state) {
            is AnalysisUiState.Loading -> LoadingContent()
            is AnalysisUiState.Error -> ErrorContent(
                message = s.message,
                onRetry = { attempt++ },
                onBack = onBack
            )
            is AnalysisUiState.Success -> {
                ResultContent(
                    analysis = s.analysis,
                    imagery = imagery,
                    imagerySideKm = imagerySideKm,
                    onImagerySideChange = { imagerySideKm = it }
                )
                Spacer(Modifier.height(16.dp))
                OutlinedButton(
                    onClick = onMethodologyClick,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Metodologia completa e limiti  →", color = Green)
                }
            }
        }

        Spacer(Modifier.height(30.dp))
    }
}

// ------------------------------------------------------------------
// CARICAMENTO ED ERRORE
// ------------------------------------------------------------------

@Composable
private fun LoadingContent() {
    var seconds by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(1000)
            seconds++
        }
    }

    Card(
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            CircularProgressIndicator(color = Green)
            Spacer(Modifier.height(16.dp))
            Text(
                "Elaborazione delle immagini satellitari… $seconds s",
                fontWeight = FontWeight.SemiBold, color = DarkGreen
            )
            Spacer(Modifier.height(8.dp))
            Text(
                "Cerchiamo l'osservazione Sentinel-2 valida più recente e le " +
                        "osservazioni dello stesso periodo negli anni precedenti. " +
                        "Di solito servono 20–40 secondi; se il server era " +
                        "inattivo, la prima analisi può richiedere 1–2 minuti.",
                fontSize = 13.sp, lineHeight = 19.sp, color = Muted
            )
        }
    }
}

@Composable
private fun ErrorContent(message: String, onRetry: () -> Unit, onBack: () -> Unit) {
    Card(
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Column(Modifier.padding(22.dp)) {
            Text(
                "Analisi non riuscita",
                fontSize = 20.sp, fontWeight = FontWeight.Bold, color = DarkGreen
            )
            Spacer(Modifier.height(8.dp))
            Text(message, fontSize = 14.sp, lineHeight = 20.sp, color = Muted)
            Spacer(Modifier.height(18.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(
                    onClick = onRetry,
                    colors = ButtonDefaults.buttonColors(containerColor = Green)
                ) { Text("Riprova") }
                OutlinedButton(onClick = onBack) {
                    Text("Torna alla mappa", color = Green)
                }
            }
        }
    }
}

// ------------------------------------------------------------------
// RISULTATO
// ------------------------------------------------------------------

@Composable
private fun ResultContent(
    analysis: PlaceAnalysis,
    imagery: ImageryState,
    imagerySideKm: Double,
    onImagerySideChange: (Double) -> Unit
) {
    HeroCard(analysis)

    if (analysis.messages.isNotEmpty()) {
        Spacer(Modifier.height(14.dp))
        Card(
            shape = RoundedCornerShape(18.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF3E6))
        ) {
            Column(
                Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                analysis.messages.forEach { message ->
                    Text(
                        "⚠  $message",
                        fontSize = 13.sp, lineHeight = 19.sp,
                        color = Color(0xFF8A4B14)
                    )
                }
            }
        }
    }

    // ---------- immagini satellitari ----------
    ImagerySection(imagery, imagerySideKm, onImagerySideChange)

    // ---------- confronto con gli anni precedenti ----------
    if (analysis.baseline.observations.isNotEmpty()) {
        SectionTitle("Rispetto agli anni precedenti")
        val years = analysis.baseline.years
        val yearsText = when {
            years.isEmpty() -> ""
            years.size == 1 -> "nel ${years.first()}"
            else -> "negli anni ${years.first()}–${years.last()}"
        }
        Text(
            "Ogni punto è un'osservazione valida dello stesso periodo " +
                    "(±${analysis.baseline.windowDays} giorni) $yearsText.",
            fontSize = 12.sp, lineHeight = 17.sp, color = Muted
        )
        Spacer(Modifier.height(12.dp))
        NdviRangeChart(analysis.baseline, analysis.latest)
    }

    // ---------- qualità ----------
    SectionTitle("Qualità dei dati")
    InfoCard {
        val latest = analysis.latest
        val q = analysis.quality
        if (latest != null) {
            InfoRow("Pixel validi nell'area", latest.validPercentage?.let { pct(it) } ?: "n.d.")
            InfoRow(
                "Nuvolosità dichiarata (intera scena)",
                latest.cloudCoverPercent?.let { pct(it) } ?: "n.d."
            )
            InfoRow("Scena Sentinel-2", latest.itemId)
        }
        InfoRow(
            "Scene recenti valutate",
            "${q.recentScenesEvaluated} (${q.recentScenesRejected} scartate)"
        )
        InfoRow(
            "Scene storiche valutate",
            "${q.baselineScenesEvaluated} (${q.baselineScenesRejected} scartate)"
        )
        InfoRow(
            "Supporto storico",
            "${analysis.baseline.support} (${analysis.baseline.samples} osservazioni)"
        )
        if (q.technicalErrors > 0) {
            InfoRow("Scene non leggibili", q.technicalErrors.toString())
        }
        Text(
            "Una scena viene scartata se meno del " +
                    "${q.minValidPercentage.toInt()}% dei pixel dell'area è valido " +
                    "(nuvole, ombre, dati mancanti secondo la classificazione SCL).",
            fontSize = 12.sp, lineHeight = 17.sp, color = Muted,
            modifier = Modifier.padding(top = 6.dp)
        )
    }

    // ---------- date ----------
    SectionTitle("Date")
    InfoCard {
        analysis.latest?.let {
            InfoRow("Acquisizione satellitare", formatDate(it.date))
        }
        InfoRow(
            "Periodo cercato",
            "${formatDate(analysis.quality.recentPeriodStart)} – " +
                    formatDate(analysis.quality.recentPeriodEnd)
        )
        InfoRow("Elaborazione", formatDateTime(analysis.processedAt))
        analysis.processingSeconds?.let {
            InfoRow("Tempo di calcolo", String.format(Locale.ITALY, "%.0f s", it))
        }
    }

    // ---------- metodologia ----------
    SectionTitle("Come è calcolato")
    InfoCard {
        Text(
            "L'NDVI confronta la riflettanza nel vicino infrarosso (B08) e nel " +
                    "rosso (B04). La vegetazione densa e attiva riflette molto " +
                    "infrarosso e assorbe il rosso, quindi ha valori alti.",
            fontSize = 13.sp, lineHeight = 19.sp, color = Muted
        )
        Spacer(Modifier.height(8.dp))
        METHODOLOGY_LABELS.forEach { (key, label) ->
            analysis.methodology[key]?.takeIf { it.isNotBlank() }?.let { value ->
                InfoRow(label, value)
            }
        }
        Spacer(Modifier.height(8.dp))
        Text(
            analysis.warning,
            fontSize = 12.sp, lineHeight = 17.sp, color = DarkGreen,
            fontWeight = FontWeight.SemiBold
        )
    }
}

private val METHODOLOGY_LABELS = listOf(
    "source" to "Fonte",
    "formula" to "Formula",
    "spatial_resolution_m" to "Risoluzione (m)",
    "cloud_mask" to "Maschera nuvole",
    "aggregation" to "Aggregazione",
    "latest_selection" to "Osservazione recente",
    "baseline" to "Baseline",
    "anomaly" to "Anomalia"
)

@Composable
private fun HeroCard(analysis: PlaceAnalysis) {
    val latest = analysis.latest
    val comparison = analysis.comparison
    val baseline = analysis.baseline

    Card(
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = DarkGreen)
    ) {
        Column(Modifier.padding(22.dp)) {
            if (latest == null) {
                Text("NESSUNA OSSERVAZIONE RECENTE", color = PaleGreen, fontSize = 11.sp)
                Spacer(Modifier.height(8.dp))
                Text(
                    "Nel periodo cercato non c'è un'immagine con abbastanza " +
                            "pixel validi (nuvole, ombre o dati mancanti).",
                    color = Color.White, fontSize = 15.sp, lineHeight = 21.sp
                )
                return@Column
            }

            Text(
                if (latest.isRecent) "ULTIMA OSSERVAZIONE VALIDA · NDVI"
                else "OSSERVAZIONE NON RECENTE · NDVI",
                color = PaleGreen, fontSize = 11.sp, letterSpacing = 1.sp
            )
            Text(
                String.format(Locale.US, "%.3f", latest.ndviMean),
                color = Color.White, fontSize = 44.sp, fontWeight = FontWeight.Bold
            )
            Text(
                "Acquisita il ${formatDate(latest.date)} · ${daysAgo(latest.daysSinceObservation)}",
                color = PaleGreen, fontSize = 13.sp
            )
            if (!latest.isRecent) {
                Text(
                    "Più vecchia di ${latest.maxDaysForRecent} giorni: " +
                            "non rappresenta la situazione attuale.",
                    color = Color(0xFFE6C99E), fontSize = 13.sp,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }

            Spacer(Modifier.height(16.dp))
            HorizontalDivider(color = Color(0xFF426256))
            Spacer(Modifier.height(14.dp))

            val anomaly = comparison.anomalyPercent
            val delta = comparison.deltaNdvi
            val median = baseline.ndviMedian

            if (median != null && delta != null) {
                Text(
                    if (comparison.percentMeaningful && anomaly != null)
                        String.format(Locale.US, "%+.1f%% rispetto alla baseline stagionale", anomaly)
                    else
                        String.format(Locale.US, "Δ NDVI %+.3f rispetto alla baseline", delta),
                    color = Color(0xFFE6C99E), fontWeight = FontWeight.Bold, fontSize = 15.sp
                )
                Text(
                    comparison.classification.replaceFirstChar { it.uppercase() },
                    color = Color.White, fontSize = 14.sp,
                    modifier = Modifier.padding(top = 2.dp)
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    String.format(
                        Locale.US,
                        "Baseline %.3f · mediana di %d osservazioni · supporto %s",
                        median, baseline.samples, baseline.support
                    ),
                    color = PaleGreen, fontSize = 12.sp
                )
            } else {
                Text(
                    "Confronto con la baseline non disponibile",
                    color = Color(0xFFE6C99E), fontWeight = FontWeight.Bold, fontSize = 15.sp
                )
                Text(
                    "Servono almeno 3 osservazioni valide dello stesso periodo " +
                            "negli anni precedenti (trovate: ${baseline.samples}).",
                    color = PaleGreen, fontSize = 12.sp, lineHeight = 17.sp
                )
            }
        }
    }
}

/**
 * Asse NDVI orizzontale: punti = osservazioni degli anni precedenti,
 * linea arancione = mediana (baseline), cerchio grande = ultima osservazione.
 */
@Composable
private fun NdviRangeChart(baseline: Baseline, latest: LatestObservation?) {
    val values = baseline.observations.map { it.ndviMean } +
            listOfNotNull(latest?.ndviMean, baseline.ndviMedian)

    var lo = (values.minOrNull() ?: 0.0) - 0.03
    var hi = (values.maxOrNull() ?: 1.0) + 0.03
    if (hi - lo < 0.10) {
        val center = (hi + lo) / 2
        lo = center - 0.05
        hi = center + 0.05
    }
    lo = max(lo, -1.0)
    hi = min(hi, 1.0)

    Column {
        Row(verticalAlignment = Alignment.CenterVertically) {
            LegendDot(Green.copy(alpha = 0.45f), 9)
            Text("  Anni precedenti", fontSize = 11.sp, color = Muted)
            Spacer(Modifier.width(12.dp))
            Box(Modifier.size(width = 3.dp, height = 12.dp).background(Orange))
            Text("  Baseline", fontSize = 11.sp, color = Muted)
            Spacer(Modifier.width(12.dp))
            LegendDot(DarkGreen, 12)
            Text("  Ultima", fontSize = 11.sp, color = Muted)
        }
        Spacer(Modifier.height(10.dp))

        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(96.dp)
                .background(Color.White, RoundedCornerShape(16.dp))
                .padding(horizontal = 18.dp, vertical = 12.dp)
        ) {
            val centerY = size.height / 2
            fun x(v: Double): Float =
                (((v - lo) / (hi - lo)).toFloat().coerceIn(0f, 1f)) * size.width

            drawLine(
                color = Background,
                start = Offset(0f, centerY),
                end = Offset(size.width, centerY),
                strokeWidth = 6f
            )

            baseline.ndviMedian?.let { m ->
                drawLine(
                    color = Orange,
                    start = Offset(x(m), 4f),
                    end = Offset(x(m), size.height - 4f),
                    strokeWidth = 5f
                )
            }

            // Leggero scostamento verticale per non sovrapporre i punti vicini.
            baseline.observations.forEachIndexed { i, p ->
                val dy = ((i % 3) - 1) * 14f
                drawCircle(
                    color = Green.copy(alpha = 0.45f),
                    radius = 9f,
                    center = Offset(x(p.ndviMean), centerY + dy)
                )
            }

            latest?.let {
                val c = Offset(x(it.ndviMean), centerY)
                drawCircle(color = DarkGreen, radius = 17f, center = c)
                drawCircle(
                    color = Color.White, radius = 17f, center = c,
                    style = Stroke(width = 4f)
                )
            }
        }

        Spacer(Modifier.height(4.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(String.format(Locale.US, "NDVI %.2f", lo), fontSize = 10.sp, color = Muted)
            Text(String.format(Locale.US, "%.2f", hi), fontSize = 10.sp, color = Muted)
        }
    }
}

// ------------------------------------------------------------------
// COMPONENTI DI SUPPORTO
// ------------------------------------------------------------------

@Composable
private fun SectionTitle(text: String) {
    Spacer(Modifier.height(24.dp))
    Text(text, fontSize = 19.sp, fontWeight = FontWeight.Bold, color = DarkGreen)
    Spacer(Modifier.height(8.dp))
}

@Composable
private fun InfoCard(content: @Composable () -> Unit) {
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) { content() }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth()) {
        Text(label, fontSize = 13.sp, color = Muted, modifier = Modifier.weight(0.45f))
        Spacer(Modifier.width(8.dp))
        Text(
            value, fontSize = 13.sp, color = DarkGreen,
            fontWeight = FontWeight.Medium, modifier = Modifier.weight(0.55f)
        )
    }
}

@Composable
private fun LegendDot(color: Color, sizeDp: Int) {
    Box(Modifier.size(sizeDp.dp).background(color, CircleShape))
}

private fun pct(value: Double): String =
    if (abs(value) < 1) String.format(Locale.ITALY, "%.2f%%", value)
    else String.format(Locale.ITALY, "%.0f%%", value)

private fun daysAgo(days: Int): String = when (days) {
    0 -> "oggi"
    1 -> "ieri"
    else -> "$days giorni fa"
}

private val DATE_FORMAT = DateTimeFormatter.ofPattern("d MMM yyyy", Locale.ITALIAN)
private val DATE_TIME_FORMAT = DateTimeFormatter.ofPattern("d MMM yyyy, HH:mm", Locale.ITALIAN)

internal fun formatDate(isoDate: String): String =
    runCatching { LocalDate.parse(isoDate.take(10)).format(DATE_FORMAT) }
        .getOrDefault(isoDate)

private fun formatDateTime(isoDateTime: String): String =
    runCatching {
        OffsetDateTime.parse(isoDateTime)
            .atZoneSameInstant(ZoneId.systemDefault())
            .format(DATE_TIME_FORMAT)
    }.getOrDefault(isoDateTime)
