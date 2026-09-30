package com.giovmar.earthpulse

import android.Manifest
import android.content.pm.PackageManager
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.TextButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import androidx.compose.runtime.LaunchedEffect
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style
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
    val longitude: Double,
    // Nome del luogo se scelto dalla ricerca; null se scelto toccando la mappa.
    val label: String? = null
)

// Contenitore semplice per conservare mappa e stile
// senza provocare ricomposizioni.
private class MapHolder {
    var map: MapLibreMap? = null
    var style: Style? = null
}

@Composable
fun MapScreen(
    selectedPlace: SelectedPlace?,
    onPlaceSelected: (SelectedPlace) -> Unit,
    onAnalyzeClick: () -> Unit,
    onExamplesClick: () -> Unit,
    onMethodologyClick: () -> Unit,
    onSatelliteClick: () -> Unit = {}
) {
    val currentOnPlaceSelected by rememberUpdatedState(onPlaceSelected)
    val currentSelectedPlace by rememberUpdatedState(selectedPlace)
    val holder = remember { MapHolder() }
    val mapContext = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current

    // MapView di MapLibre, creata una volta per questa schermata.
    val mapView = remember { MapView(mapContext).apply { onCreate(null) } }

    // ---- stato della ricerca ----
    // Nessun autocompletamento: si cerca solo quando l'utente conferma
    // (policy d'uso di Nominatim).
    var query by rememberSaveable { mutableStateOf("") }
    var searching by remember { mutableStateOf(false) }
    var results by remember { mutableStateOf<List<PlaceSearchResult>>(emptyList()) }
    var searchError by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    val focusManager = LocalFocusManager.current

    fun runSearch() {
        val text = query.trim()
        if (text.length < 2 || searching) return
        focusManager.clearFocus()
        searching = true
        searchError = null
        results = emptyList()

        scope.launch {
            try {
                val found = EarthPulseApi.searchPlaces(text)
                results = found
                if (found.isEmpty()) {
                    searchError = "Nessun luogo trovato per \"$text\"."
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: ApiException) {
                searchError = e.message
            } catch (e: Exception) {
                searchError = "Risposta della ricerca non leggibile."
            } finally {
                searching = false
            }
        }
    }

    // ---- "La mia posizione" ----
    val context = LocalContext.current
    var locating by remember { mutableStateOf(false) }

    fun goToMyLocation() {
        if (locating) return
        locating = true
        scope.launch {
            val location = try {
                currentLocation(context)
            } finally {
                locating = false
            }
            if (location == null) {
                Toast.makeText(
                    context,
                    "Posizione non disponibile: attiva la localizzazione e riprova.",
                    Toast.LENGTH_LONG
                ).show()
                return@launch
            }
            val place = SelectedPlace(location.latitude, location.longitude, "La mia posizione")
            currentOnPlaceSelected(place)
            results = emptyList()
            searchError = null
            holder.map?.let { flyTo(it, place.latitude, place.longitude, SELECTION_ZOOM) }
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { grants ->
        if (grants.values.any { it }) {
            goToMyLocation()
        } else {
            Toast.makeText(
                context,
                "Senza il permesso di localizzazione puoi comunque toccare la mappa o cercare un luogo.",
                Toast.LENGTH_LONG
            ).show()
        }
    }

    fun onMyLocationClick() {
        val permissions = arrayOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        )
        val granted = permissions.any {
            ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
        }
        if (granted) goToMyLocation() else permissionLauncher.launch(permissions)
    }

    fun selectResult(result: PlaceSearchResult) {
        val place = SelectedPlace(result.latitude, result.longitude, result.name)
        currentOnPlaceSelected(place)
        query = result.name
        results = emptyList()
        searchError = null
        holder.map?.let { flyTo(it, place.latitude, place.longitude, SELECTION_ZOOM) }
    }

    // Ciclo di vita della MapView collegato a quello dell'app.
    DisposableEffect(lifecycleOwner, mapView) {
        val lifecycle = lifecycleOwner.lifecycle
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_START -> mapView.onStart()
                Lifecycle.Event.ON_RESUME -> mapView.onResume()
                Lifecycle.Event.ON_PAUSE -> mapView.onPause()
                Lifecycle.Event.ON_STOP -> mapView.onStop()
                else -> Unit
            }
        }
        lifecycle.addObserver(observer)
        onDispose {
            lifecycle.removeObserver(observer)
            if (lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) mapView.onPause()
            if (lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED)) mapView.onStop()
            mapView.onDestroy()
            holder.map = null
            holder.style = null
        }
    }

    // Configurazione della mappa (una volta).
    LaunchedEffect(mapView) {
        mapView.getMapAsync { map ->
            holder.map = map

            map.uiSettings.isAttributionEnabled = false   // attribuzione nel pannello
            map.uiSettings.isLogoEnabled = false
            map.uiSettings.isRotateGesturesEnabled = false
            map.uiSettings.isTiltGesturesEnabled = false
            map.setMinZoomPreference(1.5)
            map.setMaxZoomPreference(18.0)

            // Se un luogo era già selezionato (ritorno da un'altra schermata),
            // riparti da lì; altrimenti mostra l'Italia.
            val start = currentSelectedPlace
            map.cameraPosition = CameraPosition.Builder()
                .target(
                    if (start != null) LatLng(start.latitude, start.longitude)
                    else LatLng(41.9, 12.5)
                )
                .zoom(if (start != null) SELECTION_ZOOM else 4.5)
                .build()

            map.setStyle(Style.Builder().fromUri(BASE_MAP_STYLE_URL)) { style ->
                localizeLabels(style)
                addSelectionLayers(style)
                holder.style = style
                showSelection(style, currentSelectedPlace)
            }

            map.addOnMapClickListener { point ->
                val place = SelectedPlace(
                    latitude = point.latitude,
                    longitude = normalizeLongitude(point.longitude)
                )
                currentOnPlaceSelected(place)

                // Da lontano il quadrato di 1 km non si vede:
                // avviciniamo la mappa al punto scelto.
                if (map.cameraPosition.zoom < 11.0) {
                    flyTo(map, place.latitude, place.longitude, SELECTION_ZOOM)
                }
                true
            }
        }
    }

    // Aggiorna punto e quadrato quando cambia il luogo scelto.
    LaunchedEffect(selectedPlace) {
        holder.style?.let { showSelection(it, selectedPlace) }
    }

    Box(Modifier.fillMaxSize()) {

        // ---------------- MAPPA ----------------
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { mapView }
        )

        // ---------------- BARRA SUPERIORE + RICERCA ----------------
        Column(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .fillMaxWidth()
                .statusBarsPadding()
                .padding(16.dp)
        ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
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

            // Com'è fatto il satellite (vista esplosa)
            Surface(
                onClick = onSatelliteClick,
                shape = RoundedCornerShape(16.dp),
                color = Color.White,
                shadowElevation = 4.dp
            ) {
                Text(
                    "🛰",
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 9.dp),
                    fontSize = 18.sp
                )
            }

            Spacer(Modifier.width(8.dp))

            Surface(
                onClick = onMethodologyClick,
                shape = RoundedCornerShape(16.dp),
                color = Color.White,
                shadowElevation = 4.dp
            ) {
                Text(
                    "Metodo",
                    modifier = Modifier.padding(horizontal = 11.dp, vertical = 12.dp),
                    color = Green,
                    fontWeight = FontWeight.SemiBold
                )
            }

            Spacer(Modifier.width(8.dp))

            Surface(
                onClick = onExamplesClick,
                shape = RoundedCornerShape(16.dp),
                color = Color.White,
                shadowElevation = 4.dp
            ) {
                Text(
                    "Storie",
                    modifier = Modifier.padding(horizontal = 11.dp, vertical = 12.dp),
                    color = Green,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }

        Spacer(Modifier.height(10.dp))

        // Campo di ricerca + pulsante "La mia posizione"
        Row(verticalAlignment = Alignment.CenterVertically) {
        Surface(
            modifier = Modifier.weight(1f),
            shape = RoundedCornerShape(16.dp),
            color = Color.White,
            shadowElevation = 4.dp
        ) {
            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("Cerca un luogo (es. Salerno)", color = Muted) },
                singleLine = true,
                shape = RoundedCornerShape(16.dp),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                keyboardActions = KeyboardActions(onSearch = { runSearch() }),
                trailingIcon = {
                    if (searching) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(22.dp),
                            color = Green,
                            strokeWidth = 2.dp
                        )
                    } else {
                        TextButton(
                            onClick = { runSearch() },
                            enabled = query.trim().length >= 2
                        ) {
                            Text("Cerca", color = Green, fontWeight = FontWeight.SemiBold)
                        }
                    }
                },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = Color.White,
                    unfocusedContainerColor = Color.White,
                    focusedBorderColor = Green,
                    unfocusedBorderColor = Color.Transparent,
                    cursorColor = Green
                )
            )
        }

        Spacer(Modifier.width(8.dp))

        Surface(
            onClick = { onMyLocationClick() },
            modifier = Modifier.size(56.dp),
            shape = RoundedCornerShape(16.dp),
            color = Color.White,
            shadowElevation = 4.dp
        ) {
            Box(contentAlignment = Alignment.Center) {
                if (locating) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(22.dp),
                        color = Green,
                        strokeWidth = 2.dp
                    )
                } else {
                    Text("📍", fontSize = 22.sp)
                }
            }
        }
        }

        // Risultati o messaggio di errore
        if (results.isNotEmpty() || searchError != null) {
            Spacer(Modifier.height(8.dp))
            Card(
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
            ) {
                Column(Modifier.fillMaxWidth()) {
                    searchError?.let { message ->
                        Text(
                            message,
                            modifier = Modifier.padding(16.dp),
                            fontSize = 13.sp,
                            color = Orange
                        )
                    }
                    results.forEachIndexed { index, result ->
                        if (index > 0) HorizontalDivider(color = Background)
                        Column(
                            Modifier
                                .fillMaxWidth()
                                .clickable { selectResult(result) }
                                .padding(horizontal = 16.dp, vertical = 12.dp)
                        ) {
                            Text(
                                result.name,
                                fontWeight = FontWeight.SemiBold,
                                color = DarkGreen,
                                fontSize = 15.sp
                            )
                            Text(
                                result.displayName,
                                fontSize = 12.sp,
                                color = Muted,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                    }
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            "Ricerca: Nominatim / Photon · © OpenStreetMap",
                            fontSize = 10.sp,
                            color = Muted,
                            modifier = Modifier.weight(1f)
                        )
                        TextButton(onClick = {
                            results = emptyList()
                            searchError = null
                        }) {
                            Text("Chiudi", color = Green, fontSize = 12.sp)
                        }
                    }
                }
            }
        }
        }

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
                    selectedPlace.label?.let { name ->
                        Text(
                            name,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                            color = DarkGreen,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                    Text(
                        formatCoordinates(selectedPlace),
                        fontSize = if (selectedPlace.label == null) 20.sp else 14.sp,
                        fontWeight = if (selectedPlace.label == null) FontWeight.Bold else FontWeight.Normal,
                        color = if (selectedPlace.label == null) DarkGreen else Muted
                    )
                    Text(
                        "Area di analisi ≈ 1 × 1 km · Sentinel-2 · 10 m",
                        fontSize = 12.sp,
                        color = Muted
                    )
                    Text(
                        "Tocca la mappa per spostare il punto.",
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
                            "Analizza questo luogo",
                            modifier = Modifier.padding(vertical = 4.dp),
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }

                // Attribuzione obbligatoria dei dati OpenStreetMap
                Text(
                    baseMapAttribution(),
                    fontSize = 10.sp,
                    color = Muted,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }
        }
    }
}

/**
 * Quadrato di lato sideKm centrato sul punto.
 * Usa la stessa approssimazione di make_bbox() in api/main.py
 * (1° di latitudine ≈ 111 km), così l'area disegnata coincide
 * con quella analizzata dal backend.
 */
fun analysisSquare(place: SelectedPlace, sideKm: Double): List<Pair<Double, Double>> {
    val halfLat = sideKm / 222.0
    val cosLat = abs(cos(Math.toRadians(place.latitude))).coerceAtLeast(1e-6)
    val halfLon = sideKm / (222.0 * cosLat)

    val south = place.latitude - halfLat
    val north = place.latitude + halfLat
    val west = place.longitude - halfLon
    val east = place.longitude + halfLon

    // Coppie (latitudine, longitudine), anello chiuso.
    return listOf(
        south to west,
        south to east,
        north to east,
        north to west,
        south to west
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
