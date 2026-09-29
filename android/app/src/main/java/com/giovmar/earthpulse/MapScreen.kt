package com.giovmar.earthpulse

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import org.osmdroid.events.MapEventsReceiver
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.CustomZoomButtonsController
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.MapEventsOverlay
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polygon
import java.util.Locale
import kotlin.math.abs
import kotlin.math.cos

// Lato dell'area analizzata, in km. Deve corrispondere al parametro
// side_km inviato al backend.
const val ANALYSIS_SIDE_KM = 1.0

// Il backend accetta latitudini comprese tra -80 e +80.
private const val MAX_SUPPORTED_LATITUDE = 80.0

// Zoom usato quando l'utente seleziona un punto da molto lontano.
private const val SELECTION_ZOOM = 13.0

data class SelectedPlace(
    val latitude: Double,
    val longitude: Double
)

// Contenitore semplice per conservare il riferimento alla MapView
// senza provocare ricomposizioni.
private class MapHolder {
    var map: MapView? = null
}

@Composable
fun MapScreen(
    selectedPlace: SelectedPlace?,
    onPlaceSelected: (SelectedPlace) -> Unit,
    onAnalyzeClick: () -> Unit,
    onExamplesClick: () -> Unit
) {
    val currentOnPlaceSelected by rememberUpdatedState(onPlaceSelected)
    val holder = remember { MapHolder() }

    // Libera le risorse della mappa quando la schermata viene chiusa.
    DisposableEffect(Unit) {
        onDispose {
            holder.map?.onDetach()
            holder.map = null
        }
    }

    Box(Modifier.fillMaxSize()) {

        // ---------------- MAPPA ----------------
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { context ->
                MapView(context).apply {
                    setTileSource(TileSourceFactory.MAPNIK)
                    setMultiTouchControls(true)
                    zoomController.setVisibility(
                        CustomZoomButtonsController.Visibility.SHOW_AND_FADEOUT
                    )
                    setMinZoomLevel(2.0)
                    setMaxZoomLevel(18.0)
                    setHorizontalMapRepetitionEnabled(true)
                    setVerticalMapRepetitionEnabled(false)

                    // Se un luogo era già selezionato (ritorno dagli esempi),
                    // riparti da lì; altrimenti mostra l'Italia.
                    if (selectedPlace != null) {
                        controller.setZoom(SELECTION_ZOOM)
                        controller.setCenter(
                            GeoPoint(selectedPlace.latitude, selectedPlace.longitude)
                        )
                    } else {
                        controller.setZoom(5.0)
                        controller.setCenter(GeoPoint(41.9, 12.5))
                    }

                    val map = this

                    val receiver = object : MapEventsReceiver {
                        override fun singleTapConfirmedHelper(p: GeoPoint?): Boolean {
                            if (p == null) return false

                            val place = SelectedPlace(
                                latitude = p.latitude,
                                longitude = normalizeLongitude(p.longitude)
                            )
                            currentOnPlaceSelected(place)

                            // Da lontano il quadrato di 1 km non si vede:
                            // avviciniamo la mappa al punto scelto.
                            if (map.zoomLevelDouble < 11.0) {
                                map.controller.animateTo(
                                    GeoPoint(place.latitude, place.longitude),
                                    SELECTION_ZOOM,
                                    800L
                                )
                            }
                            return true
                        }

                        override fun longPressHelper(p: GeoPoint?): Boolean = false
                    }

                    // In posizione 0: riceve i tocchi non gestiti dagli altri overlay.
                    overlays.add(0, MapEventsOverlay(receiver))

                    holder.map = this
                }
            },
            update = { map ->
                showSelection(map, selectedPlace)
            }
        )

        // ---------------- BARRA SUPERIORE ----------------
        Row(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .fillMaxWidth()
                .statusBarsPadding()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                shape = RoundedCornerShape(16.dp),
                color = Color.White,
                shadowElevation = 4.dp
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        Modifier
                            .size(28.dp)
                            .background(Green, RoundedCornerShape(9.dp)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text("◉", color = Color.White, fontSize = 17.sp)
                    }
                    Spacer(Modifier.width(8.dp))
                    Text(
                        "EarthPulse",
                        fontWeight = FontWeight.Bold,
                        color = DarkGreen,
                        fontSize = 17.sp
                    )
                }
            }

            Spacer(Modifier.weight(1f))

            Surface(
                onClick = onExamplesClick,
                shape = RoundedCornerShape(16.dp),
                color = Color.White,
                shadowElevation = 4.dp
            ) {
                Text(
                    "Esempi",
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                    color = Green,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }

        // ---------------- ATTRIBUZIONE OSM (obbligatoria) ----------------
        Text(
            "© OpenStreetMap contributors",
            modifier = Modifier
                .align(Alignment.TopEnd)
                .statusBarsPadding()
                .padding(top = 78.dp, end = 16.dp)
                .background(Color.White.copy(alpha = 0.85f), RoundedCornerShape(6.dp))
                .padding(horizontal = 6.dp, vertical = 2.dp),
            fontSize = 10.sp,
            color = Muted
        )

        // ---------------- PANNELLO INFERIORE ----------------
        Card(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(16.dp),
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 6.dp)
        ) {
            Column(
                modifier = Modifier.padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                if (selectedPlace == null) {
                    Text(
                        "Scegli un luogo",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        color = DarkGreen
                    )
                    Text(
                        "Tocca un punto della mappa. Analizzeremo un'area di " +
                                "circa 1 × 1 km intorno al punto scelto.",
                        fontSize = 14.sp,
                        lineHeight = 20.sp,
                        color = Muted
                    )
                } else {
                    val supported =
                        abs(selectedPlace.latitude) <= MAX_SUPPORTED_LATITUDE

                    Text(
                        "LUOGO SELEZIONATO",
                        color = Green,
                        fontSize = 10.sp,
                        letterSpacing = 1.4.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        formatCoordinates(selectedPlace),
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        color = DarkGreen
                    )
                    Text(
                        "Area di analisi ≈ 1 × 1 km · Sentinel-2 · 10 m",
                        fontSize = 12.sp,
                        color = Muted
                    )

                    if (!supported) {
                        Text(
                            "Latitudine fuori dall'intervallo supportato (±80°).",
                            fontSize = 12.sp,
                            color = Orange
                        )
                    }

                    Spacer(Modifier.height(6.dp))

                    Button(
                        onClick = onAnalyzeClick,
                        enabled = supported,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Green)
                    ) {
                        Text(
                            "Analizza vegetazione (NDVI)",
                            modifier = Modifier.padding(vertical = 4.dp),
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }
            }
        }
    }
}

/**
 * Disegna segnaposto e quadrato dell'area di analisi.
 * Viene chiamata ogni volta che cambia il luogo selezionato.
 */
private fun showSelection(map: MapView, place: SelectedPlace?) {
    map.overlays.removeAll { it is Marker || it is Polygon }

    if (place != null) {
        val point = GeoPoint(place.latitude, place.longitude)

        val area = Polygon(map).apply {
            points = analysisSquare(place, ANALYSIS_SIDE_KM)
            fillPaint.color = android.graphics.Color.argb(45, 23, 107, 80)
            outlinePaint.color = android.graphics.Color.rgb(23, 107, 80)
            outlinePaint.strokeWidth = 4f
            // false: il tocco passa alla mappa, così si può
            // scegliere un nuovo punto anche dentro il quadrato.
            setOnClickListener { _, _, _ -> false }
        }

        val marker = Marker(map).apply {
            position = point
            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
            // Nessuna finestra informativa al tocco del segnaposto.
            setOnMarkerClickListener { _, _ -> true }
        }

        map.overlays.add(area)
        map.overlays.add(marker)
    }

    map.invalidate()
}

/**
 * Quadrato di lato sideKm centrato sul punto.
 * Usa la stessa approssimazione di make_bbox() in api/main.py
 * (1° di latitudine ≈ 111 km), così l'area disegnata coincide
 * con quella analizzata dal backend.
 */
fun analysisSquare(place: SelectedPlace, sideKm: Double): List<GeoPoint> {
    val halfLat = sideKm / 222.0
    val cosLat = abs(cos(Math.toRadians(place.latitude))).coerceAtLeast(1e-6)
    val halfLon = sideKm / (222.0 * cosLat)

    val south = place.latitude - halfLat
    val north = place.latitude + halfLat
    val west = place.longitude - halfLon
    val east = place.longitude + halfLon

    return listOf(
        GeoPoint(south, west),
        GeoPoint(south, east),
        GeoPoint(north, east),
        GeoPoint(north, west),
        GeoPoint(south, west)
    )
}

/** Riporta la longitudine nell'intervallo [-180, 180). */
private fun normalizeLongitude(longitude: Double): Double {
    var value = (longitude + 180.0) % 360.0
    if (value < 0) value += 360.0
    return value - 180.0
}

fun formatCoordinates(place: SelectedPlace): String {
    val ns = if (place.latitude >= 0) "N" else "S"
    val ew = if (place.longitude >= 0) "E" else "O"
    return String.format(
        Locale.US,
        "%.4f° %s, %.4f° %s",
        abs(place.latitude), ns,
        abs(place.longitude), ew
    )
}
