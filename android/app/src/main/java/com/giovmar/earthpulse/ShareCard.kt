package com.giovmar.earthpulse

import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Shader
import android.graphics.Typeface
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import android.text.TextUtils
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

// ------------------------------------------------------------------
// SCHEDA DA CONDIVIDERE
// ------------------------------------------------------------------
//
// Un'immagine 1080 x 1350 (formato 4:5, adatto ai social) con titolo,
// le due immagini prima/dopo (o una sola), un messaggio, la legenda e
// l'attribuzione dei dati. Si crea sul telefono con le immagini già
// scaricate e si condivide con il menu di sistema di Android.

data class ShareContent(
    val title: String,
    val subtitle: String,
    val layerLabel: String,
    val after: ImageBitmap,
    val afterLabel: String,
    val before: ImageBitmap? = null,
    val beforeLabel: String? = null,
    val highlight: String? = null,
    val stops: List<ColorStop> = emptyList(),
    val legendLabels: List<String> = emptyList(),
    val attribution: String
)

private const val CARD_W = 1080
private const val CARD_H = 1350
private const val MARGIN = 60f

/** Pulsante "Condividi" riutilizzabile: costruisce la scheda solo al tocco. */
@Composable
fun ShareButton(label: String = "Condividi questo confronto", content: () -> ShareContent?) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var busy by remember { mutableStateOf(false) }

    OutlinedButton(
        onClick = {
            val data = content() ?: return@OutlinedButton
            busy = true
            scope.launch {
                try {
                    val file = withContext(Dispatchers.Default) {
                        val bitmap = buildShareCard(data)
                        saveForSharing(context, bitmap)
                    }
                    shareImage(context, file, "${data.title} · ${data.layerLabel} — EarthPulse")
                } catch (e: Exception) {
                    android.widget.Toast.makeText(
                        context, "Condivisione non riuscita: ${e.message ?: "errore"}",
                        android.widget.Toast.LENGTH_LONG
                    ).show()
                } finally {
                    busy = false
                }
            }
        },
        enabled = !busy,
        shape = RoundedCornerShape(14.dp),
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 10.dp)
    ) {
        Text(if (busy) "Preparo l'immagine…" else "↗  $label", color = Green)
    }
}

fun buildShareCard(data: ShareContent): Bitmap {
    val bitmap = Bitmap.createBitmap(CARD_W, CARD_H, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    canvas.drawColor(DarkGreen.toArgb())

    val white = android.graphics.Color.WHITE
    val mutedLight = android.graphics.Color.rgb(170, 200, 185)
    val accent = android.graphics.Color.rgb(120, 214, 160)
    val bold = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)

    var y = MARGIN + 10f

    // Marchio
    val brand = textPaint(28f, accent, bold).apply { letterSpacing = 0.2f }
    canvas.drawText("EARTHPULSE", MARGIN, y + 28f, brand)
    y += 60f

    // Titolo e sottotitolo (a capo automatico, max 2 righe)
    y += drawWrapped(canvas, data.title, textPaint(56f, white, bold), y, maxLines = 2)
    y += 8f
    y += drawWrapped(
        canvas, "${data.subtitle} · ${data.layerLabel}",
        textPaint(32f, mutedLight), y, maxLines = 2
    )
    y += 30f

    // Immagini
    val contentWidth = CARD_W - 2 * MARGIN
    val before = data.before
    if (before != null) {
        val gap = 20f
        val side = (contentWidth - gap) / 2
        drawImage(canvas, before, RectF(MARGIN, y, MARGIN + side, y + side), data.beforeLabel)
        drawImage(
            canvas, data.after,
            RectF(MARGIN + side + gap, y, MARGIN + 2 * side + gap, y + side), data.afterLabel
        )
        y += side + 30f
    } else {
        val side = 620f
        val left = (CARD_W - side) / 2
        drawImage(canvas, data.after, RectF(left, y, left + side, y + side), data.afterLabel)
        y += side + 30f
    }

    // Legenda (se il livello ha una scala di colori)
    if (data.stops.size >= 2) {
        drawLegend(canvas, data.stops, data.legendLabels, y, mutedLight)
        y += 80f
    }

    // Messaggio principale
    data.highlight?.takeIf { it.isNotBlank() }?.let { text ->
        y += drawWrapped(canvas, text, textPaint(38f, white, bold), y, maxLines = 3)
    }

    // Attribuzione in fondo
    val footer = textPaint(22f, mutedLight)
    val footerLayout = staticLayout(
        "${data.attribution}\nCreato con EarthPulse", footer,
        contentWidth.toInt(), maxLines = 3
    )
    canvas.save()
    canvas.translate(MARGIN, CARD_H - MARGIN - footerLayout.height)
    footerLayout.draw(canvas)
    canvas.restore()

    return bitmap
}

private fun textPaint(size: Float, color: Int, typeface: Typeface = Typeface.DEFAULT) =
    TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
        textSize = size
        this.color = color
        this.typeface = typeface
    }

private fun staticLayout(text: String, paint: TextPaint, width: Int, maxLines: Int): StaticLayout =
    StaticLayout.Builder.obtain(text, 0, text.length, paint, width)
        .setAlignment(Layout.Alignment.ALIGN_NORMAL)
        .setMaxLines(maxLines)
        .setEllipsize(TextUtils.TruncateAt.END)
        .build()

/** Disegna un testo che va a capo; restituisce l'altezza occupata. */
private fun drawWrapped(canvas: Canvas, text: String, paint: TextPaint, top: Float, maxLines: Int): Float {
    val layout = staticLayout(text, paint, (CARD_W - 2 * MARGIN).toInt(), maxLines)
    canvas.save()
    canvas.translate(MARGIN, top)
    layout.draw(canvas)
    canvas.restore()
    return layout.height.toFloat()
}

private fun drawImage(canvas: Canvas, image: ImageBitmap, rect: RectF, label: String?) {
    val source = image.asAndroidBitmap()
    val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
    canvas.save()
    val clip = android.graphics.Path().apply { addRoundRect(rect, 24f, 24f, android.graphics.Path.Direction.CW) }
    canvas.clipPath(clip)
    canvas.drawBitmap(source, null, rect, paint)
    canvas.restore()

    if (label != null) {
        val textPaint = textPaint(26f, android.graphics.Color.WHITE, Typeface.create(Typeface.DEFAULT, Typeface.BOLD))
        val width = textPaint.measureText(label)
        val pill = RectF(rect.left + 14f, rect.top + 14f, rect.left + 14f + width + 28f, rect.top + 14f + 46f)
        canvas.drawRoundRect(pill, 14f, 14f, Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = android.graphics.Color.argb(150, 0, 0, 0)
        })
        canvas.drawText(label, pill.left + 14f, pill.top + 32f, textPaint)
    }
}

private fun drawLegend(canvas: Canvas, stops: List<ColorStop>, labels: List<String>, top: Float, textColor: Int) {
    val left = MARGIN
    val right = CARD_W - MARGIN
    val min = stops.first().value
    val max = stops.last().value
    val colors = stops.map { it.color.toArgb() }.toIntArray()
    val positions = stops.map { ((it.value - min) / (max - min)).coerceIn(0f, 1f) }.toFloatArray()
    val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        shader = LinearGradient(left, 0f, right, 0f, colors, positions, Shader.TileMode.CLAMP)
    }
    canvas.drawRoundRect(RectF(left, top, right, top + 22f), 11f, 11f, paint)

    val labelPaint = textPaint(24f, textColor)
    val shown = labels.filter { it.isNotBlank() }.take(3)
    shown.forEachIndexed { index, text ->
        val width = labelPaint.measureText(text)
        val x = when {
            shown.size == 1 -> left
            index == 0 -> left
            index == shown.lastIndex -> right - width
            else -> (left + right) / 2 - width / 2
        }
        canvas.drawText(text, x, top + 58f, labelPaint)
    }
}

private fun saveForSharing(context: Context, bitmap: Bitmap): File {
    val dir = File(context.cacheDir, "shared").apply { mkdirs() }
    val file = File(dir, "earthpulse_confronto.png")
    file.outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
    return file
}

private fun shareImage(context: Context, file: File, text: String) {
    val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "image/png"
        putExtra(Intent.EXTRA_STREAM, uri)
        putExtra(Intent.EXTRA_TEXT, text)
        clipData = ClipData.newRawUri(null, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    context.startActivity(Intent.createChooser(intent, "Condividi con…"))
}
