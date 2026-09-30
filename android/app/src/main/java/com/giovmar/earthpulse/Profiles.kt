package com.giovmar.earthpulse

import android.content.Context
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// ------------------------------------------------------------------
// PROFILI "PER CHI LAVORA"
// ------------------------------------------------------------------
//
// Ogni profilo decide: quali livelli mostrare per primi, quali sezioni
// suggerire e un consiglio pratico per ciascun livello. I testi indicano
// cosa osservare, senza promettere diagnosi: ogni segnale va verificato
// sul posto.

enum class ExtraSection(val label: String) {
    NIGHT("Luci notturne"),
    HEAT("Isole di calore"),
    ARCHIVE("Com'era dal 1984")
}

enum class Profile(
    val label: String,
    val icon: String,
    val intro: String,
    val layers: List<String>,
    val sections: List<ExtraSection>,
    val tips: Map<String, String>
) {
    ALL(
        "Tutti", "🌍",
        "",
        emptyList(),
        emptyList(),
        emptyMap()
    ),
    FARMER(
        "Agricoltura", "🌾",
        "Vigore delle colture (Vegetazione), clorofilla (Clorofilla) e acqua nelle foglie " +
            "(Umidità). La scheda in alto confronta con la stessa stagione degli anni scorsi; " +
            "con \"Scegli le date\" segui il campo nel corso della stagione.",
        listOf("ndvi", "ndre", "ndmi", "rgb", "diff"),
        listOf(ExtraSection.ARCHIVE),
        mapOf(
            "ndvi" to "Zone più chiare dentro lo stesso campo possono indicare crescita " +
                "irregolare, ristagni o fallanze: da verificare sul posto.",
            "ndre" to "Più utile a coltura sviluppata: un calo rispetto al resto del campo può " +
                "segnalare carenza di azoto o stress. Pixel di 20 m: meglio su appezzamenti di " +
                "qualche ettaro.",
            "ndmi" to "Valori bassi in piena stagione indicano foglie con meno acqua: un segnale " +
                "di stress idrico utile per decidere dove e quando irrigare.",
            "diff" to "Un calo improvviso tra due date può essere un raccolto o uno sfalcio, non " +
                "per forza un problema."
        )
    ),
    CIVIL_PROTECTION(
        "Protezione civile", "🚒",
        "Acqua fuori posto, frane e incendi: con \"Scegli le date\" confronta una data prima e " +
            "una dopo l'evento. Le nuvole bloccano la vista: durante le alluvioni servirebbe " +
            "il radar, che vede attraverso le nuvole.",
        listOf("ndwi", "rgb", "diff", "ndti", "ndvi"),
        listOf(ExtraSection.ARCHIVE),
        mapOf(
            "ndwi" to "Aree blu nuove fuori dagli alvei, tra una data prima e una dopo l'evento, " +
                "possono indicare allagamenti. Sotto la mappa trovi gli ettari d'acqua.",
            "diff" to "Cali di vegetazione forti e netti su un versante possono indicare frane " +
                "o incendi.",
            "ndti" to "Acqua molto torbida dopo piogge intense indica trasporto di fango e " +
                "sedimenti nei fiumi e alle foci.",
            "rgb" to "Il colore reale serve a confermare ciò che mostrano gli indici: fango, " +
                "bruciato, acqua stagnante."
        )
    ),
    FORESTRY(
        "Boschi e parchi", "🌲",
        "Stato dei boschi, tagli e incendi. Con l'archivio dal 1984 vedi i cambiamenti di " +
            "lungo periodo, come l'avanzata o la perdita del bosco.",
        listOf("ndvi", "ndmi", "diff", "rgb", "ndre"),
        listOf(ExtraSection.ARCHIVE),
        mapOf(
            "ndmi" to "Valori bassi in estate indicano vegetazione più secca: un indizio, non " +
                "una previsione, di maggiore rischio d'incendio.",
            "diff" to "Chiazze di calo nette e geometriche sono spesso tagli; aree ampie e " +
                "irregolari possono essere incendi o schianti da vento.",
            "ndvi" to "Nel bosco fitto l'NDVI è quasi sempre alto: guarda soprattutto i cali " +
                "rispetto agli anni precedenti."
        )
    ),
    MUNICIPALITY(
        "Comuni", "🏙️",
        "Consumo di suolo, verde urbano e calore. Le isole di calore mostrano dove la città " +
            "si scalda di più; l'archivio mostra come è cresciuta dal 1984.",
        listOf("ndbi", "ndvi", "rgb", "diff"),
        listOf(ExtraSection.HEAT, ExtraSection.ARCHIVE, ExtraSection.NIGHT),
        mapOf(
            "ndbi" to "Superfici impermeabili: confronta anni diversi per vedere nuove " +
                "costruzioni. Anche il suolo nudo e i cantieri danno valori alti.",
            "ndvi" to "Il verde urbano (parchi, viali alberati) abbassa la temperatura: " +
                "confrontalo con la mappa delle isole di calore.",
            "diff" to "Un calo di vegetazione in città spesso indica un nuovo cantiere o " +
                "un'area verde persa."
        )
    ),
    WATER(
        "Acque", "💧",
        "Estensione di laghi e invasi in ettari, alghe e torbidità, e neve in montagna come " +
            "riserva d'acqua. Con \"Scegli le date\" confronta stagioni secche e piovose.",
        listOf("ndwi", "ndci", "ndti", "ndsi", "rgb"),
        listOf(ExtraSection.ARCHIVE),
        mapOf(
            "ndwi" to "Gli ettari d'acqua sotto la mappa misurano quanto è cambiato lo specchio " +
                "d'acqua tra le due date.",
            "ndci" to "Valori alti e in aumento d'estate possono segnalare fioriture algali: " +
                "da verificare con campionamenti.",
            "ndti" to "Acqua torbida vicino alle immissioni o dopo le piogge indica sedimenti " +
                "in arrivo nell'invaso.",
            "ndsi" to "La neve sui bacini a monte è una riserva d'acqua per la primavera: " +
                "confronta con gli inverni precedenti."
        )
    );

    /** Livelli dati riordinati: prima quelli del profilo, poi gli altri. */
    fun <T> sortLayers(layers: List<T>, key: (T) -> String): List<T> {
        if (this.layers.isEmpty()) return layers
        val rank = this.layers.withIndex().associate { it.value to it.index }
        return layers.sortedBy { rank[key(it)] ?: Int.MAX_VALUE }
    }
}

// ------------------------------------------------------------------
// MEMORIA DEL PROFILO (resta anche chiudendo l'app)
// ------------------------------------------------------------------

private const val PREFS = "earthpulse"
private const val PROFILE_KEY = "profile"

fun loadProfile(context: Context): Profile {
    val name = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        .getString(PROFILE_KEY, null)
    return Profile.entries.firstOrNull { it.name == name } ?: Profile.ALL
}

fun saveProfile(context: Context, profile: Profile) {
    context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        .edit().putString(PROFILE_KEY, profile.name).apply()
}

@Composable
fun rememberProfileState(): ProfileHolder {
    val context = LocalContext.current
    return remember { ProfileHolder(context.applicationContext) }
}

class ProfileHolder(private val context: Context) {
    var profile by mutableStateOf(loadProfile(context))
        private set

    fun select(value: Profile) {
        profile = value
        saveProfile(context, value)
    }
}

// ------------------------------------------------------------------
// INTERFACCIA
// ------------------------------------------------------------------

/** Riga di scelta del profilo e scheda "Per te". */
@Composable
fun ProfileSection(
    holder: ProfileHolder,
    imagery: ImageryState? = null,
    onOpenSection: (ExtraSection) -> Unit
) {
    Text(
        "PER CHI LAVORA",
        color = Green, fontSize = 11.sp, letterSpacing = 1.5.sp,
        fontWeight = FontWeight.Bold
    )
    Spacer(Modifier.height(6.dp))
    Row(
        Modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Profile.entries.forEach { option ->
            val selected = option == holder.profile
            Surface(
                shape = RoundedCornerShape(50),
                color = if (selected) DarkGreen else Color.White,
                modifier = Modifier.clickable { holder.select(option) }
            ) {
                Text(
                    "${option.icon} ${option.label}",
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                    color = if (selected) Color.White else DarkGreen,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
    }

    val profile = holder.profile
    if (profile != Profile.ALL) {
        Spacer(Modifier.height(10.dp))
        InfoBox {
            Column {
                Text(
                    "${profile.icon}  Per te · ${profile.label}",
                    fontSize = 15.sp, fontWeight = FontWeight.Bold, color = DarkGreen
                )
                // Riepilogo: i numeri che contano per il profilo, ora e prima
                imagery?.let { ProfileSummary(profile, it) }
                Text(
                    profile.intro,
                    fontSize = 13.sp, lineHeight = 19.sp, color = Muted,
                    modifier = Modifier.padding(top = 8.dp)
                )
                if (profile.sections.isNotEmpty()) {
                    Spacer(Modifier.height(8.dp))
                    Row(
                        Modifier.horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        profile.sections.forEach { section ->
                            OutlinedButton(
                                onClick = { onOpenSection(section) },
                                shape = RoundedCornerShape(14.dp)
                            ) {
                                Text("↓ ${section.label}", color = Green, fontSize = 13.sp)
                            }
                        }
                    }
                }
            }
        }
    }
    Spacer(Modifier.height(16.dp))
}

/** Consiglio del profilo per il livello mostrato (se c'è). */
@Composable
fun ProfileTip(profile: Profile, layerKey: String) {
    val tip = profile.tips[layerKey] ?: return
    Spacer(Modifier.height(10.dp))
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = PaleGreen
    ) {
        Column(Modifier.padding(12.dp)) {
            Text(
                "${profile.icon}  PER ${profile.label.uppercase()}",
                fontSize = 11.sp, letterSpacing = 1.sp,
                fontWeight = FontWeight.Bold, color = Green
            )
            Text(
                tip,
                fontSize = 13.sp, lineHeight = 19.sp, color = DarkGreen,
                modifier = Modifier.padding(top = 4.dp)
            )
        }
    }
}

// ------------------------------------------------------------------
// RIEPILOGO DEL PROFILO
// ------------------------------------------------------------------

/** Indici riassunti per ogni profilo (al massimo 3, nell'area di 1 km). */
private val Profile.summaryKeys: List<String>
    get() = layers.filter { it in STAT_INDEX_KEYS }.take(3)

@Composable
private fun ProfileSummary(profile: Profile, imagery: ImageryState) {
    val base = imagery.scenes ?: return
    val scenes = imagery.effectiveScenes(base)
    val after = scenes.after ?: return
    val before = scenes.before
    val labels = scenes.layers.associateBy { it.key }

    Column(Modifier.padding(top = 10.dp)) {
        Text(
            "Area di 1 km · ${formatDate(after.date)}" +
                (before?.let { " rispetto al ${formatDate(it.date)}" } ?: ""),
            fontSize = 11.sp, color = Muted
        )
        if (profile == Profile.WATER) {
            val water = rememberWaterStat(imagery, after.images["stat_water"])
            val waterBefore = rememberWaterStat(imagery, before?.images?.get("stat_water"))
            SummaryRow(
                name = "Acqua (area mostrata)",
                value = water?.let { hectares(it.waterHa) },
                change = if (water != null && waterBefore != null && waterBefore.waterHa > 0.5)
                    String.format(java.util.Locale.ITALIAN, "%+.0f%%",
                        100.0 * (water.waterHa - waterBefore.waterHa) / waterBefore.waterHa)
                else null
            )
        }
        profile.summaryKeys.forEach { key ->
            val layer = labels[key]
            val code = layer?.formula?.substringBefore("=")?.trim()
            val name = (layer?.label ?: key.uppercase()) + (code?.let { " ($it)" } ?: "")
            val now = rememberIndexStat(imagery, after.images["stat_index"]?.replace("{index}", key))
            val then = rememberIndexStat(imagery, before?.images?.get("stat_index")?.replace("{index}", key))
            val nowValue = now?.median
            val thenValue = then?.median
            SummaryRow(
                name = name,
                value = when {
                    now == null -> null
                    nowValue == null -> if (key in WATER_ONLY_KEYS) "niente acqua" else "nuvole"
                    else -> decimal(nowValue)
                },
                change = if (nowValue != null && thenValue != null) {
                    val delta = nowValue - thenValue
                    val trend = when {
                        delta > 0.03 -> "↑"
                        delta < -0.03 -> "↓"
                        else -> "="
                    }
                    String.format(java.util.Locale.ITALIAN, "%+.2f %s", delta, trend)
                } else null
            )
        }
    }
}

@Composable
private fun SummaryRow(name: String, value: String?, change: String?) {
    Row(
        Modifier.padding(top = 6.dp),
        verticalAlignment = androidx.compose.ui.Alignment.CenterVertically
    ) {
        Text(name, fontSize = 13.sp, color = DarkGreen, modifier = Modifier.weight(1f))
        Text(
            value ?: "…",
            fontSize = 15.sp, fontWeight = FontWeight.Bold, color = DarkGreen
        )
        Text(
            change ?: "",
            fontSize = 12.sp, color = Green,
            modifier = Modifier.padding(start = 8.dp).width(72.dp)
        )
    }
}
