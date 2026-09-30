package com.giovmar.earthpulse

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Spiegazione del metodo di analisi.
 * I valori numerici corrispondono ai parametri di default di
 * /api/v1/ndvi/analysis (api/main.py) e di src/analysis.py.
 */
@Composable
fun MethodologyScreen(onBack: () -> Unit) {
    Column(
        Modifier
            .fillMaxSize()
            .background(Background)
            .statusBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(22.dp)
    ) {
        Text(
            "←  Indietro",
            color = Green,
            modifier = Modifier
                .clickable { onBack() }
                .padding(vertical = 8.dp)
        )

        Spacer(Modifier.height(18.dp))
        Text(
            "COME FUNZIONA",
            color = Green, fontSize = 11.sp, letterSpacing = 1.5.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(Modifier.height(6.dp))
        Text(
            "Metodologia",
            fontSize = 29.sp, fontWeight = FontWeight.Bold, color = DarkGreen
        )
        Text(
            "Il satellite è l'ingrediente, non il prodotto: ecco come " +
                    "trasformiamo le immagini in un'informazione leggibile.",
            fontSize = 14.sp, lineHeight = 21.sp, color = Muted
        )

        MethodSection("1 · I dati") {
            Paragraph(
                "Usiamo immagini Sentinel-2 del programma europeo Copernicus, " +
                        "prodotto Level-2A (riflettanza della superficie, già corretta " +
                        "per l'atmosfera). Le scene sono cercate nel catalogo STAC " +
                        "Earth Search di Element 84."
            )
            Bullet("Risoluzione delle bande usate: 10 m.")
            Bullet("Un passaggio sullo stesso punto ogni 2–5 giorni circa, ma molte immagini sono coperte da nuvole.")
            Bullet("L'area analizzata è un quadrato di circa 1 × 1 km (circa 10.000 pixel) centrato sul punto scelto.")
        }

        MethodSection("2 · L'indice NDVI") {
            Formula("NDVI = (NIR − RED) / (NIR + RED)")
            Paragraph(
                "NIR è la banda B08 (vicino infrarosso), RED è la banda B04 " +
                        "(rosso). La vegetazione fotosinteticamente attiva assorbe il " +
                        "rosso e riflette molto l'infrarosso, quindi ha NDVI alto."
            )
            Paragraph("Valori indicativi, che variano con il tipo di superficie e la stagione:")
            Bullet("sotto 0: acqua, neve, nuvole residue;")
            Bullet("0 – 0,2: suolo nudo, roccia, aree urbane;")
            Bullet("0,2 – 0,5: vegetazione rada, prati, colture giovani;")
            Bullet("oltre 0,5: vegetazione densa (boschi, colture sviluppate).")
            Paragraph("Il valore mostrato è la media dei pixel validi dell'area.")
        }

        MethodSection("3 · Controllo di qualità") {
            Paragraph(
                "Ogni pixel viene verificato con la classificazione della scena " +
                        "(SCL) di Sentinel-2. Escludiamo i pixel senza dati, saturi o " +
                        "difettosi, le ombre delle nuvole, le nuvole a media e alta " +
                        "probabilità, i cirri sottili, la neve e i pixel non classificati."
            )
            Bullet("Una scena è usata solo se almeno il 70% dei pixel dell'area è valido.")
            Bullet("Se in un giorno ci sono più scene, si tiene quella con meno nuvole dichiarate.")
            Bullet("Dal 25 gennaio 2022 i dati Sentinel-2 L2A hanno uno scostamento radiometrico di 1000 (processing baseline 04.00): quando il catalogo non lo ha già rimosso, lo sottraiamo prima di calcolare l'NDVI, così i confronti tra anni diversi restano corretti.")
        }

        MethodSection("4 · Osservazione recente") {
            Paragraph(
                "Cerchiamo la scena valida più recente negli ultimi 45 giorni. " +
                        "La mostriamo come recente solo se ha al massimo 20 giorni; " +
                        "altrimenti l'app avvisa che non rappresenta la situazione attuale."
            )
            Paragraph(
                "Distinguiamo sempre la data di acquisizione (quando il satellite " +
                        "ha ripreso l'area) dalla data di elaborazione (quando è stata " +
                        "calcolata l'analisi)."
            )
        }

        MethodSection("5 · Baseline stagionale") {
            Paragraph(
                "L'NDVI cambia molto con le stagioni, quindi non confrontiamo luglio " +
                        "con gennaio. La baseline usa le osservazioni valide degli ultimi " +
                        "3 anni nella stessa finestra stagionale (±15 giorni dalla stessa " +
                        "data), fino a 3 per anno. Il valore di riferimento è la mediana, " +
                        "meno sensibile ai valori anomali della media."
            )
            Bullet("Servono almeno 3 osservazioni storiche, altrimenti il confronto non viene mostrato.")
            Bullet("Supporto storico: insufficiente (<2), limitato (2–3), buono (4–5), forte (6 o più).")
        }

        MethodSection("6 · Anomalia") {
            Formula("Anomalia % = (NDVI − baseline) / |baseline| × 100")
            Bullet("≤ −8%: marcatamente sotto la baseline;")
            Bullet("da −8% a −5%: sotto la baseline;")
            Bullet("da −5% a 0%: leggermente sotto la baseline;")
            Bullet("da 0% a +5%: vicino alla baseline;")
            Bullet("≥ +5%: sopra la baseline.")
            Paragraph(
                "Se la baseline è inferiore a 0,2 (poca o nessuna vegetazione) la " +
                        "percentuale è poco significativa: mostriamo la differenza assoluta."
            )
        }

        MethodSection("Immagini dall'alto") {
            Paragraph(
                "Per ogni luogo mostriamo un'area di 3 × 3 km da due scene quasi " +
                        "senza nuvole (almeno 95% di pixel validi): la più recente e " +
                        "quella più vicina alla stessa data di un anno prima."
            )
            Bullet("Colori reali: immagine True Color di Sentinel-2 (B04, B03, B02), con lo stesso contrasto per tutte le date. I colori della data precedente sono armonizzati alla più recente (percentili 2–98 di ogni banda) per compensare luce e foschia: è solo una scelta di visualizzazione.")
            Bullet("NDVI: scala di colori fissa, quindi due date sono confrontabili a colpo d'occhio.")
            Bullet("Variazione: NDVI dopo meno NDVI prima, solo dove entrambe le immagini sono valide.")
            Bullet("Le due date sono ricampionate sulla stessa griglia di 10 m, così coincidono pixel per pixel.")
        }

        MethodSection("7 · Limiti") {
            Bullet("L'NDVI non misura direttamente la salute della vegetazione: è legato alla sua risposta spettrale.")
            Bullet("Un'anomalia non dimostra da sola la causa: siccità, tagli, incendi, raccolti, ma anche differenze di osservazione possono produrla.")
            Bullet("Nella vegetazione molto densa l'NDVI tende a saturare e varia poco.")
            Bullet("Un singolo valore anomalo va confermato da osservazioni successive: un calo isolato può dipendere da foschia, geometria di ripresa o tile diversa.")
            Bullet("L'area è un quadrato approssimato e può includere superfici diverse (strade, edifici, acqua).")
            Bullet("I pixel di 10 m mescolano elementi diversi: piccoli cambiamenti possono non essere visibili.")
            Bullet("Nelle mappe di variazione, lungo strade e fiumi possono comparire sottili bordi rossi e verdi: sono dovuti al piccolo disallineamento tra due acquisizioni, non a cambiamenti reali.")
        }

        MethodSection("Fonti e attribuzioni") {
            Bullet("Contiene dati Copernicus Sentinel modificati, elaborati da EarthPulse.")
            Bullet("Catalogo delle immagini: Earth Search (Element 84), dati Sentinel-2 su AWS Open Data.")
            Bullet("Mappa: OpenFreeMap e OpenMapTiles, dati © OpenStreetMap contributors (ODbL). Ricerca dei luoghi: Nominatim e Photon.")
        }

        Spacer(Modifier.height(30.dp))
    }
}

@Composable
private fun MethodSection(title: String, content: @Composable () -> Unit) {
    Spacer(Modifier.height(22.dp))
    Text(title, fontSize = 19.sp, fontWeight = FontWeight.Bold, color = DarkGreen)
    Spacer(Modifier.height(8.dp))
    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) { content() }
    }
}

@Composable
private fun Paragraph(text: String) {
    Text(text, fontSize = 14.sp, lineHeight = 21.sp, color = Muted)
}

@Composable
private fun Bullet(text: String) {
    Row {
        Text("•", fontSize = 14.sp, color = Green, fontWeight = FontWeight.Bold)
        Spacer(Modifier.width(8.dp))
        Text(text, fontSize = 14.sp, lineHeight = 20.sp, color = Muted)
    }
}

@Composable
private fun Formula(text: String) {
    Text(
        text,
        modifier = Modifier
            .fillMaxWidth()
            .background(PaleGreen, RoundedCornerShape(10.dp))
            .padding(horizontal = 12.dp, vertical = 10.dp),
        fontFamily = FontFamily.Monospace,
        fontSize = 14.sp,
        color = DarkGreen,
        fontWeight = FontWeight.SemiBold
    )
}
