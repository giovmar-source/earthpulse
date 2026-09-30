package com.giovmar.earthpulse

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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.CancellationException

// Emoji per categoria: un segnale visivo semplice, senza dipendenze.
private fun categoryIcon(category: String): String = when {
    category.contains("Incendio", ignoreCase = true) -> "🔥"
    category.contains("Vulcano", ignoreCase = true) -> "🌋"
    category.contains("Terremoto", ignoreCase = true) -> "🌊"
    category.contains("Alluvione", ignoreCase = true) -> "🌧️"
    category.contains("Siccità", ignoreCase = true) -> "☀️"
    else -> "🛰️"
}

// ------------------------------------------------------------------
// ELENCO DELLE STORIE
// ------------------------------------------------------------------

@Composable
fun StoriesListScreen(
    onBack: () -> Unit,
    onStoryClick: (String) -> Unit,
    onForestDemoClick: () -> Unit
) {
    var stories by remember { mutableStateOf<List<StorySummary>?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var attempt by remember { mutableIntStateOf(0) }

    LaunchedEffect(attempt) {
        error = null
        try {
            stories = EarthPulseApi.fetchStories()
        } catch (e: CancellationException) {
            throw e
        } catch (e: ApiException) {
            error = e.message
        } catch (e: Exception) {
            error = "Elenco delle storie non leggibile: ${e.message}"
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
        BackLink("←  Mappa", onBack)

        Spacer(Modifier.height(18.dp))
        Text(
            "STORIE DAL SATELLITE",
            color = Green, fontSize = 11.sp, letterSpacing = 1.5.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(Modifier.height(6.dp))
        Text(
            "Eventi reali, visti da Sentinel-2",
            fontSize = 27.sp, lineHeight = 32.sp,
            fontWeight = FontWeight.Bold, color = DarkGreen
        )
        Text(
            "Incendi, eruzioni, alluvioni, siccità e terremoti: le stesse " +
                    "immagini prima e dopo, con quello che possiamo e non possiamo concludere.",
            fontSize = 14.sp, lineHeight = 20.sp, color = Muted
        )
        Spacer(Modifier.height(18.dp))

        val list = stories
        when {
            error != null -> Card(
                shape = RoundedCornerShape(18.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Column(Modifier.padding(16.dp)) {
                    Text(error ?: "", fontSize = 13.sp, color = Muted)
                    Spacer(Modifier.height(10.dp))
                    Button(
                        onClick = { attempt++ },
                        colors = ButtonDefaults.buttonColors(containerColor = Green)
                    ) { Text("Riprova") }
                }
            }

            list == null -> Box(
                Modifier
                    .fillMaxWidth()
                    .padding(30.dp),
                contentAlignment = Alignment.Center
            ) { CircularProgressIndicator(color = Green) }

            else -> Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                list.forEach { story ->
                    StoryCard(story) { onStoryClick(story.id) }
                }
            }
        }

        // Demo storica già presente nell'app (dati locali)
        Spacer(Modifier.height(22.dp))
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .clickable { onForestDemoClick() },
            shape = RoundedCornerShape(18.dp),
            colors = CardDefaults.cardColors(containerColor = PaleGreen)
        ) {
            Column(Modifier.padding(16.dp)) {
                Text(
                    "Analisi storica: bosco vicino a Salerno",
                    fontWeight = FontWeight.Bold, color = DarkGreen
                )
                Text(
                    "Serie NDVI 2023–2025 e baseline stagionale, calcolate offline.  →",
                    fontSize = 12.sp, color = Muted
                )
            }
        }
        Spacer(Modifier.height(30.dp))
    }
}

@Composable
private fun StoryCard(story: StorySummary, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Row(Modifier.padding(16.dp)) {
            Box(
                Modifier
                    .size(48.dp)
                    .background(Background, RoundedCornerShape(14.dp)),
                contentAlignment = Alignment.Center
            ) { Text(categoryIcon(story.category), fontSize = 24.sp) }

            Spacer(Modifier.width(13.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    story.category.uppercase() + " · " + formatDate(story.eventDate),
                    fontSize = 10.sp, color = Green,
                    fontWeight = FontWeight.Bold, letterSpacing = 0.8.sp
                )
                Text(
                    story.title,
                    fontSize = 17.sp, fontWeight = FontWeight.Bold, color = DarkGreen
                )
                Text(
                    "${story.place} · ${story.country}",
                    fontSize = 12.sp, color = Muted
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    story.summary,
                    fontSize = 13.sp, lineHeight = 18.sp, color = Muted,
                    maxLines = 3, overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}

// ------------------------------------------------------------------
// DETTAGLIO DI UNA STORIA
// ------------------------------------------------------------------

@Composable
fun StoryDetailScreen(
    storyId: String,
    onBack: () -> Unit
) {
    var story by remember(storyId) { mutableStateOf<StoryDetail?>(null) }
    var error by remember(storyId) { mutableStateOf<String?>(null) }
    var attempt by remember { mutableIntStateOf(0) }

    // Stato delle immagini (cache dei PNG già scaricati).
    val imagery = remember(storyId) { ImageryState() }

    LaunchedEffect(storyId, attempt) {
        error = null
        try {
            val detail = EarthPulseApi.fetchStory(storyId)
            imagery.scenes = detail.scenes
            imagery.loading = false
            story = detail
        } catch (e: CancellationException) {
            throw e
        } catch (e: ApiException) {
            error = e.message
        } catch (e: Exception) {
            error = "Storia non leggibile: ${e.message}"
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
        BackLink("←  Storie", onBack)
        Spacer(Modifier.height(14.dp))

        val detail = story
        when {
            error != null -> Card(
                shape = RoundedCornerShape(18.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Column(Modifier.padding(16.dp)) {
                    Text(error ?: "", fontSize = 13.sp, color = Muted)
                    Spacer(Modifier.height(10.dp))
                    Button(
                        onClick = { attempt++ },
                        colors = ButtonDefaults.buttonColors(containerColor = Green)
                    ) { Text("Riprova") }
                }
            }

            detail == null -> Column(
                Modifier
                    .fillMaxWidth()
                    .padding(30.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                CircularProgressIndicator(color = Green)
                Spacer(Modifier.height(12.dp))
                Text(
                    "Carichiamo le immagini satellitari… (fino a un minuto se il server era inattivo)",
                    fontSize = 13.sp, color = Muted
                )
            }

            else -> StoryContent(detail, imagery)
        }
        Spacer(Modifier.height(30.dp))
    }
}

@Composable
private fun StoryContent(story: StoryDetail, imagery: ImageryState) {
    val s = story.summary
    val uriHandler = LocalUriHandler.current

    Text(
        "${categoryIcon(s.category)}  ${s.category.uppercase()} · ${formatDate(s.eventDate)}",
        color = Green, fontSize = 11.sp, letterSpacing = 1.sp, fontWeight = FontWeight.Bold
    )
    Spacer(Modifier.height(6.dp))
    Text(s.title, fontSize = 28.sp, lineHeight = 33.sp,
        fontWeight = FontWeight.Bold, color = DarkGreen)
    Text("${s.place} · ${s.country}", fontSize = 13.sp, color = Muted)
    Spacer(Modifier.height(12.dp))
    Text(s.summary, fontSize = 15.sp, lineHeight = 22.sp, color = DarkGreen)
    Spacer(Modifier.height(18.dp))

    val scenes = story.scenes
    val after = scenes.after
    if (after != null) {
        ImageryContent(
            imagery, scenes, after, showAnalysisArea = false,
            shareTitle = s.title,
            shareSubtitle = "${s.place} · ${s.country}",
            shareHighlight = s.summary
        )
    } else {
        Text(
            scenes.messages.joinToString("\n").ifBlank { "Immagini non disponibili." },
            fontSize = 13.sp, color = Muted
        )
    }

    StorySection("Cosa osservare") {
        Text(story.whatToLook, fontSize = 14.sp, lineHeight = 21.sp, color = Muted)
    }

    if (story.facts.isNotEmpty()) {
        StorySection("In sintesi") {
            story.facts.forEach { fact ->
                Row(Modifier.padding(vertical = 2.dp)) {
                    Text("•", color = Green, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.width(8.dp))
                    Text(fact, fontSize = 14.sp, lineHeight = 20.sp, color = Muted)
                }
            }
        }
    }

    StorySection("Cosa non possiamo concludere") {
        Text(story.caveat, fontSize = 14.sp, lineHeight = 21.sp, color = Muted)
        story.diffNote?.let { note ->
            Spacer(Modifier.height(8.dp))
            Text(
                "⚠  $note",
                fontSize = 13.sp, lineHeight = 19.sp, color = Color(0xFF8A4B14)
            )
        }
    }

    if (story.sources.isNotEmpty()) {
        StorySection("Fonti") {
            story.sources.forEach { source ->
                Text(
                    source.title,
                    fontSize = 13.sp, lineHeight = 19.sp, color = Green,
                    textDecoration = TextDecoration.Underline,
                    modifier = Modifier
                        .padding(vertical = 3.dp)
                        .clickable {
                            runCatching { uriHandler.openUri(source.url) }
                        }
                )
            }
        }
    }
}

@Composable
private fun StorySection(title: String, content: @Composable () -> Unit) {
    Spacer(Modifier.height(22.dp))
    Text(title, fontSize = 18.sp, fontWeight = FontWeight.Bold, color = DarkGreen)
    Spacer(Modifier.height(8.dp))
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

@Composable
private fun BackLink(text: String, onClick: () -> Unit) {
    Text(
        text,
        color = Green,
        modifier = Modifier
            .clickable { onClick() }
            .padding(vertical = 8.dp)
    )
}
