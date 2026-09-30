package com.giovmar.earthpulse

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.runtime.rememberCoroutineScope
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
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

// ------------------------------------------------------------------
// STATO: scene e immagini scaricate
// ------------------------------------------------------------------


class ImageryState {
    var scenes by mutableStateOf<ImageryScenes?>(null)
    var error by mutableStateOf<String?>(null)
    var loading by mutableStateOf(true)

    // Immagini già scaricate (per url) ed eventuali errori.
    val bitmaps = mutableStateMapOf<String, ImageBitmap>()
    val failures = mutableStateMapOf<String, String>()
    // Numeri dei livelli (es. superficie d'acqua) per url
    val waterStats = mutableStateMapOf<String, WaterStat>()
    val indexStats = mutableStateMapOf<String, IndexStat>()
    val indexStatFailures = mutableStateMapOf<String, Boolean>()

    // Linea del tempo e date scelte dall'utente.
    var timeline by mutableStateOf<ImageryTimeline?>(null)
    var timelineLoading by mutableStateOf(false)
    var timelineError by mutableStateOf<String?>(null)
    var customBeforeId by mutableStateOf<String?>(null)
    var customAfterId by mutableStateOf<String?>(null)
}

/**
 * Scene da mostrare: quelle scelte sulla linea del tempo se l'utente
 * ha selezionato due date valide, altrimenti quelle proposte dal backend.
 */
fun ImageryState.effectiveScenes(base: ImageryScenes): ImageryScenes {
    val line = timeline ?: return base
    val b = line.scenes.firstOrNull { it.scene.itemId == customBeforeId }?.scene ?: return base
    val a = line.scenes.firstOrNull { it.scene.itemId == customAfterId }?.scene ?: return base
    if (b.date >= a.date) return base

    fun fill(template: String) =
        template.replace("{before}", b.itemId).replace("{after}", a.itemId)

    val afterImages = a.images.toMutableMap()
    line.pairTemplates["diff"]?.let { afterImages["diff"] = fill(it) }
    if (base.layers.any { it.key == "dnbr" }) {
        line.pairTemplates["dnbr"]?.let { afterImages["dnbr"] = fill(it) }
    }
    val beforeImages = b.images.toMutableMap()
    line.pairTemplates["rgb_before"]?.let { beforeImages["rgb"] = fill(it) }

    val years = listOf(b.date, a.date).map { it.take(4) }.distinct().joinToString(", ")
    return base.copy(
        before = b.copy(images = beforeImages),
        after = a.copy(images = afterImages),
        messages = emptyList(),
        attribution = "Contiene dati Copernicus Sentinel modificati ($years)"
    )
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
    onSideChange: ((Double) -> Unit)? = null,
    shareTitle: String? = null,
    profile: Profile = Profile.ALL
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

        else -> ImageryContent(
            state, scenes, after,
            shareTitle = shareTitle,
            shareSubtitle = "Sentinel-2 · area ${sideKm.toInt()} × ${sideKm.toInt()} km",
            profile = profile
        )
    }
}

@Composable
internal fun ImageryContent(
    state: ImageryState,
    baseScenes: ImageryScenes,
    baseAfter: SceneImages,
    showAnalysisArea: Boolean = true,
    showDatePicker: Boolean = true,
    // Condivisione: titolo della scheda (null = nessun pulsante)
    shareTitle: String? = null,
    shareSubtitle: String = "Sentinel-2",
    shareHighlight: String? = null,
    // Profilo "Per chi lavora": ordine dei livelli e consigli pratici
    profile: Profile = Profile.ALL
) {
    // Date scelte sulla linea del tempo (se presenti).
    val scenes = state.effectiveScenes(baseScenes)
    val after = scenes.after ?: baseAfter
    val before = scenes.before

    // Livelli descritti dal backend, limitati a quelli con un'immagine.
    val allLayers = scenes.layers
        .ifEmpty { fallbackLayers(scenes) }
        .filter { after.images.containsKey(it.key) }
        .let { list -> profile.sortLayers(list) { it.key } }
    if (allLayers.isEmpty()) return

    // Con un profilo si vedono solo i suoi livelli; gli altri con "Tutti i livelli".
    var showAll by rememberSaveable(profile) { mutableStateOf(false) }
    val profileLayers = allLayers.filter { it.key in profile.layers }
    val layers = if (profile == Profile.ALL || showAll || profileLayers.isEmpty()) allLayers
                 else profileLayers

    // Cambiando profilo si parte dal suo livello principale.
    var selectedKey by rememberSaveable(profile) { mutableStateOf(layers.first().key) }
    val layer = layers.firstOrNull { it.key == selectedKey } ?: layers.first()

    // Selettore del livello (scorrevole: i livelli possono essere molti)
    Row(
        Modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        layers.forEach { option ->
            val selected = option.key == layer.key
            Surface(
                shape = RoundedCornerShape(50),
                color = if (selected) DarkGreen else Color.White,
                modifier = Modifier.clickable { selectedKey = option.key }
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
        if (profile != Profile.ALL && profileLayers.isNotEmpty() && profileLayers.size < allLayers.size) {
            Surface(
                shape = RoundedCornerShape(50),
                color = PaleGreen,
                modifier = Modifier.clickable { showAll = !showAll }
            ) {
                Text(
                    if (showAll) "Solo ${profile.icon}" else "Tutti i livelli ▸",
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                    color = Green,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
    }
    Spacer(Modifier.height(10.dp))

    // Valore dell'indice scelto nell'area analizzata (1 km): prima e dopo.
    if (showAnalysisArea && layer.key in STAT_INDEX_KEYS) {
        IndexValueCard(
            state = state,
            layer = layer,
            afterTemplate = after.images["stat_index"],
            beforeTemplate = before?.images?.get("stat_index"),
            beforeDate = before?.date
        )
        Spacer(Modifier.height(10.dp))
    }

    if (showDatePicker) {
        DatePicker(state, baseScenes)
        Spacer(Modifier.height(10.dp))
    }

    // Riquadro dell'area analizzata (1 km): solo per l'analisi di un luogo.
    val areaFraction =
        if (showAnalysisArea) (ANALYSIS_SIDE_KM / scenes.sideKm).toFloat() else 0f
    val beforeLabel = before?.let { "Prima · ${formatDate(it.date)}" }
    val afterLabel = "Dopo · ${formatDate(after.date)}"

    val afterUrl = after.images[layer.key]
    val beforeUrl = before?.images?.get(layer.key)

    if (layer.mode == "compare" && beforeUrl != null && beforeLabel != null) {
        val afterImage = rememberImage(state, afterUrl)
        val beforeImage = rememberImage(state, beforeUrl)
        BeforeAfterSlider(
            before = beforeImage,
            after = afterImage,
            beforeLabel = beforeLabel,
            afterLabel = afterLabel,
            areaFraction = areaFraction,
            failure = afterUrl?.let { state.failures[it] } ?: state.failures[beforeUrl]
        )
        Text(
            "Trascina la linea bianca per confrontare le due date.",
            fontSize = 12.sp, color = Muted,
            modifier = Modifier.padding(top = 6.dp)
        )
        if (shareTitle != null && beforeImage != null && afterImage != null) {
            ShareButton {
                ShareContent(
                    title = shareTitle,
                    subtitle = shareSubtitle,
                    layerLabel = layer.label,
                    before = beforeImage,
                    beforeLabel = beforeLabel,
                    after = afterImage,
                    afterLabel = afterLabel,
                    highlight = shareHighlight,
                    stops = layer.stops,
                    legendLabels = layer.legendLabels,
                    attribution = scenes.attribution
                )
            }
        }
    } else {
        val label = if (layer.mode == "single" && before != null)
            "${formatDate(before.date)} → ${formatDate(after.date)}"
        else afterLabel
        val singleImage = rememberImage(state, afterUrl)
        SingleImage(
            singleImage,
            label,
            areaFraction,
            afterUrl?.let { state.failures[it] }
        )
        if (shareTitle != null && singleImage != null) {
            ShareButton {
                ShareContent(
                    title = shareTitle,
                    subtitle = shareSubtitle,
                    layerLabel = layer.label,
                    after = singleImage,
                    afterLabel = label,
                    highlight = shareHighlight,
                    stops = layer.stops,
                    legendLabels = layer.legendLabels,
                    attribution = scenes.attribution
                )
            }
        }
    }

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

    if (layer.stat == "water") {
        WaterStatLine(state, after.images["stat_water"], before?.images?.get("stat_water"))
    }

    Spacer(Modifier.height(10.dp))
    Text(layer.caption, fontSize = 12.sp, lineHeight = 17.sp, color = Muted)
    layer.formula?.let { formula ->
        Text(
            formula,
            fontSize = 12.sp, color = DarkGreen,
            fontFamily = FontFamily.Monospace,
            modifier = Modifier.padding(top = 4.dp)
        )
    }
    ProfileTip(profile, layer.key)

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

/** Livelli minimi se il backend non li descrive (versioni precedenti). */
private fun fallbackLayers(scenes: ImageryScenes): List<ImageryLayerInfo> = listOf(
    ImageryLayerInfo("rgb", "Colori reali", "compare",
        "Come l'occhio vedrebbe l'area dallo spazio (bande B04, B03, B02).",
        null, emptyList(), emptyList()),
    ImageryLayerInfo("ndvi", "Vegetazione", "compare",
        "NDVI pixel per pixel. In grigio i pixel esclusi (nuvole, ombre, dati mancanti).",
        null, scenes.ndviStops, listOf("Suolo, acqua", "Vegetazione rada", "Vegetazione densa")),
    ImageryLayerInfo("diff", "Variazione", "single",
        "Differenza di NDVI tra le due date, solo dove entrambe sono valide.",
        null, scenes.diffStops, listOf("NDVI in calo", "Stabile", "NDVI in aumento"))
)

// ------------------------------------------------------------------
// SCELTA DELLE DATE (linea del tempo)
// ------------------------------------------------------------------

@Composable
private fun DatePicker(state: ImageryState, baseScenes: ImageryScenes) {
    val scope = rememberCoroutineScope()
    var open by remember { mutableStateOf(false) }
    val shown = state.effectiveScenes(baseScenes)
    val canLoad = !baseScenes.latitude.isNaN() && !baseScenes.longitude.isNaN()

    fun loadTimeline() {
        if (state.timeline != null || state.timelineLoading || !canLoad) return
        state.timelineLoading = true
        state.timelineError = null
        scope.launch {
            try {
                state.timeline = EarthPulseApi.fetchTimeline(
                    baseScenes.latitude, baseScenes.longitude, baseScenes.sideKm
                )
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                state.timelineError = e.message ?: "Linea del tempo non disponibile."
            } finally {
                state.timelineLoading = false
            }
        }
    }

    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            listOfNotNull(shown.before?.date, shown.after?.date)
                .joinToString("  →  ") { formatDate(it) },
            fontSize = 13.sp, color = DarkGreen, fontWeight = FontWeight.SemiBold,
            modifier = Modifier.weight(1f)
        )
        if (canLoad) {
            Text(
                if (open) "Chiudi" else "Scegli le date",
                color = Green, fontSize = 13.sp, fontWeight = FontWeight.SemiBold,
                modifier = Modifier
                    .clickable {
                        open = !open
                        if (open) loadTimeline()
                    }
                    .padding(vertical = 6.dp, horizontal = 4.dp)
            )
        }
    }

    if (!open) return

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        modifier = Modifier.padding(top = 6.dp)
    ) {
        Column(Modifier.fillMaxWidth().padding(12.dp)) {
            val line = state.timeline
            when {
                state.timelineLoading -> Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp), color = Green, strokeWidth = 2.dp
                    )
                    Spacer(Modifier.width(10.dp))
                    Text(
                        "Cerchiamo una scena nitida per ogni stagione degli ultimi 5 anni… " +
                                "(fino a un minuto)",
                        fontSize = 12.sp, color = Muted
                    )
                }

                state.timelineError != null -> Text(
                    state.timelineError ?: "", fontSize = 12.sp, color = Muted
                )

                line == null || line.scenes.size < 2 -> Text(
                    "Non ci sono abbastanza scene nitide per scegliere le date.",
                    fontSize = 12.sp, color = Muted
                )

                else -> {
                    val beforeDate = line.scenes
                        .firstOrNull { it.scene.itemId == state.customBeforeId }?.scene?.date

                    Text("Prima", fontSize = 12.sp, color = Muted, fontWeight = FontWeight.SemiBold)
                    DateChips(
                        scenes = line.scenes.dropLast(1),
                        selectedId = state.customBeforeId,
                        enabled = { true },
                        onSelect = { id ->
                            state.customBeforeId = id
                            // Se il "dopo" non è più successivo, lo si azzera.
                            val chosen = line.scenes.first { it.scene.itemId == id }.scene.date
                            val afterScene = line.scenes
                                .firstOrNull { it.scene.itemId == state.customAfterId }?.scene
                            if (afterScene != null && afterScene.date <= chosen) {
                                state.customAfterId = null
                            }
                        }
                    )
                    Spacer(Modifier.height(8.dp))
                    Text("Dopo", fontSize = 12.sp, color = Muted, fontWeight = FontWeight.SemiBold)
                    DateChips(
                        scenes = line.scenes.drop(1),
                        selectedId = state.customAfterId,
                        enabled = { scene -> beforeDate == null || scene.date > beforeDate },
                        onSelect = { id -> state.customAfterId = id }
                    )
                    Spacer(Modifier.height(8.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            if (state.customBeforeId != null && state.customAfterId != null)
                                "Confronto personalizzato attivo."
                            else "Scegli una data \"prima\" e una \"dopo\".",
                            fontSize = 12.sp, color = Muted,
                            modifier = Modifier.weight(1f)
                        )
                        if (state.customBeforeId != null || state.customAfterId != null) {
                            Text(
                                "Ripristina",
                                color = Green, fontSize = 12.sp, fontWeight = FontWeight.SemiBold,
                                modifier = Modifier
                                    .clickable {
                                        state.customBeforeId = null
                                        state.customAfterId = null
                                    }
                                    .padding(6.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun DateChips(
    scenes: List<TimelineScene>,
    selectedId: String?,
    enabled: (SceneImages) -> Boolean,
    onSelect: (String) -> Unit
) {
    Row(
        Modifier
            .horizontalScroll(rememberScrollState())
            .padding(top = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        scenes.forEach { entry ->
            val selected = entry.scene.itemId == selectedId
            val active = enabled(entry.scene)
            Surface(
                shape = RoundedCornerShape(50),
                color = when {
                    selected -> Green
                    active -> Background
                    else -> Color(0xFFEDEDED)
                },
                modifier = Modifier.clickable(enabled = active) { onSelect(entry.scene.itemId) }
            ) {
                Column(Modifier.padding(horizontal = 10.dp, vertical = 5.dp)) {
                    Text(
                        entry.label,
                        fontSize = 12.sp, fontWeight = FontWeight.SemiBold,
                        color = when {
                            selected -> Color.White
                            active -> DarkGreen
                            else -> Muted
                        }
                    )
                }
            }
        }
    }
}

// ------------------------------------------------------------------
// COMPONENTI GRAFICI
// ------------------------------------------------------------------

/** Due immagini sovrapposte: a sinistra della linea "prima", a destra "dopo". */
@Composable
internal fun BeforeAfterSlider(
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
internal fun SingleImage(
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
internal fun GradientLegend(
    stops: List<ColorStop>,
    leftLabel: String,
    centerLabel: String,
    rightLabel: String,
    invalidLabel: String? = "Non valido (nuvole, ombre, dati mancanti)",
    invalidColor: Color = Color(0xFFB4B4B4)
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
        if (invalidLabel != null) {
            Row(verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(top = 4.dp)) {
                Box(
                    Modifier
                        .size(10.dp)
                        .background(invalidColor, RoundedCornerShape(2.dp))
                )
                Text("  $invalidLabel", fontSize = 11.sp, color = Muted)
            }
        }
    }
}

@Composable
internal fun InfoBox(content: @Composable () -> Unit) {
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

// ------------------------------------------------------------------
// SUPERFICIE D'ACQUA (livello "Acqua")
// ------------------------------------------------------------------

@Composable
internal fun rememberWaterStat(state: ImageryState, url: String?): WaterStat? {
    LaunchedEffect(url) {
        if (url == null || state.waterStats.containsKey(url)) return@LaunchedEffect
        try {
            state.waterStats[url] = EarthPulseApi.fetchWaterStat(url)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            // Il numero è un di più: se non arriva, la mappa resta comunque.
        }
    }
    return url?.let { state.waterStats[it] }
}

internal fun hectares(value: Double): String =
    if (value >= 100) String.format(java.util.Locale.ITALIAN, "%,.0f ha", value)
    else String.format(java.util.Locale.ITALIAN, "%.1f ha", value)

@Composable
private fun WaterStatLine(state: ImageryState, afterUrl: String?, beforeUrl: String?) {
    val after = rememberWaterStat(state, afterUrl) ?: return
    val before = rememberWaterStat(state, beforeUrl)
    val text = if (before != null && before.waterHa > 0.5) {
        val change = 100.0 * (after.waterHa - before.waterHa) / before.waterHa
        "Superficie d'acqua nell'area: ${hectares(before.waterHa)} → ${hectares(after.waterHa)} " +
            String.format(java.util.Locale.ITALIAN, "(%+.0f%%)", change)
    } else {
        "Superficie d'acqua nell'area: ${hectares(after.waterHa)}"
    }
    val cloudy = listOfNotNull(after.observedPercentage, before?.observedPercentage).any { it < 90.0 }
    Spacer(Modifier.height(10.dp))
    InfoBox {
        Column {
            Text(text, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = DarkGreen)
            if (cloudy) {
                Text(
                    "Parte dell'area era coperta da nuvole: il confronto è indicativo.",
                    fontSize = 11.sp, color = Muted, modifier = Modifier.padding(top = 4.dp)
                )
            }
        }
    }
}

// ------------------------------------------------------------------
// VALORE DELL'INDICE NELL'AREA DI 1 KM
// ------------------------------------------------------------------

internal val STAT_INDEX_KEYS = setOf("ndvi", "ndwi", "ndmi", "ndbi", "ndre", "ndsi", "ndci", "ndti")
internal val WATER_ONLY_KEYS = setOf("ndci", "ndti")

@Composable
internal fun rememberIndexStat(state: ImageryState, url: String?): IndexStat? {
    LaunchedEffect(url) {
        if (url == null || state.indexStats.containsKey(url) || state.indexStatFailures.containsKey(url)) {
            return@LaunchedEffect
        }
        try {
            state.indexStats[url] = EarthPulseApi.fetchIndexStat(url)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            state.indexStatFailures[url] = true
        }
    }
    return url?.let { state.indexStats[it] }
}

internal fun decimal(value: Double): String =
    String.format(java.util.Locale.ITALIAN, "%.2f", value)

@Composable
private fun IndexValueCard(
    state: ImageryState,
    layer: ImageryLayerInfo,
    afterTemplate: String?,
    beforeTemplate: String?,
    beforeDate: String?
) {
    val afterUrl = afterTemplate?.replace("{index}", layer.key) ?: return
    val beforeUrl = beforeTemplate?.replace("{index}", layer.key)
    val after = rememberIndexStat(state, afterUrl)
    val before = rememberIndexStat(state, beforeUrl)
    // Nome breve dell'indice dalla formula ("NDRE = ..." -> "NDRE")
    val code = layer.formula?.substringBefore("=")?.trim()?.takeIf { it.isNotEmpty() }
    val title = if (code != null) "${layer.label} ($code)" else layer.label

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = DarkGreen)
    ) {
        Column(Modifier.fillMaxWidth().padding(16.dp)) {
            Text(
                "${title.uppercase()} · AREA DI 1 KM",
                color = Color.White.copy(alpha = 0.75f), fontSize = 11.sp,
                letterSpacing = 1.sp, fontWeight = FontWeight.Bold
            )
            val value = after?.median
            when {
                after == null && !state.indexStatFailures.containsKey(afterUrl) -> Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(top = 8.dp)
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp), color = Color.White, strokeWidth = 2.dp
                    )
                    Spacer(Modifier.width(10.dp))
                    Text("Calcolo del valore…", color = Color.White, fontSize = 13.sp)
                }

                value == null -> Text(
                    if (layer.key in WATER_ONLY_KEYS)
                        "Nell'area di 1 km non c'è acqua libera: l'indice non si applica."
                    else "Troppi pochi pixel validi (nuvole o dati mancanti).",
                    color = Color.White, fontSize = 13.sp,
                    modifier = Modifier.padding(top = 8.dp)
                )

                else -> {
                    Text(
                        decimal(value),
                        color = Color.White, fontSize = 34.sp, fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                    after?.date?.let {
                        Text("Mediana dei pixel validi · ${formatDate(it)}",
                            color = Color.White.copy(alpha = 0.8f), fontSize = 12.sp)
                    }
                    val previous = before?.median
                    if (previous != null && beforeDate != null) {
                        val delta = value - previous
                        val trend = when {
                            delta > 0.03 -> "in aumento"
                            delta < -0.03 -> "in calo"
                            else -> "stabile"
                        }
                        Text(
                            "Prima (${formatDate(beforeDate)}): ${decimal(previous)} · " +
                                String.format(java.util.Locale.ITALIAN, "%+.2f", delta) + " $trend",
                            color = Color(0xFFF2C98A), fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.padding(top = 8.dp)
                        )
                    }
                }
            }
        }
    }
}
