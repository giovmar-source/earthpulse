package com.giovmar.earthpulse

import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.Style
import org.maplibre.android.style.expressions.Expression
import org.maplibre.android.style.layers.CircleLayer
import org.maplibre.android.style.layers.FillLayer
import org.maplibre.android.style.layers.LineLayer
import org.maplibre.android.style.layers.PropertyFactory
import org.maplibre.android.style.layers.SymbolLayer
import org.maplibre.android.style.sources.GeoJsonSource

// ------------------------------------------------------------------
// MAPPA DI BASE: OpenFreeMap (vettoriale, gratuita, senza chiave)
// ------------------------------------------------------------------
//
// Le mappe vettoriali contengono i nomi in più lingue (name:it, name:en,
// name:latin...): le etichette sono disegnate dal telefono, quindi
// possiamo scegliere la lingua. Le mappe raster (immagini già disegnate)
// mostrano invece il nome locale, ad esempio in arabo.
const val BASE_MAP_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty"

fun baseMapAttribution(): String =
    "Mappa: OpenFreeMap · © OpenMapTiles · © OpenStreetMap contributors"

private const val SQUARE_SOURCE = "earthpulse-square"
private const val POINT_SOURCE = "earthpulse-point"
private const val EMPTY_GEOJSON = """{"type":"FeatureCollection","features":[]}"""

/**
 * Etichette in italiano; se manca, in inglese; se manca, nella
 * traslitterazione latina; solo come ultima scelta il nome locale.
 * Si applica alle etichette che mostrano nomi (non ai numeri delle strade).
 */
fun localizeLabels(style: Style) {
    val name = Expression.coalesce(
        Expression.get("name:it"),
        Expression.get("name:en"),
        Expression.get("name:latin"),
        Expression.get("name")
    )
    style.layers.forEach { layer ->
        if (layer is SymbolLayer) {
            val field = layer.textField
            val description = (field.expression ?: field.value)?.toString() ?: ""
            if (description.contains("name")) {
                layer.setProperties(PropertyFactory.textField(name))
            }
        }
    }
}

/** Aggiunge alla mappa i livelli del punto scelto e del quadrato di 1 km. */
fun addSelectionLayers(style: Style) {
    style.addSource(GeoJsonSource(SQUARE_SOURCE))
    style.addSource(GeoJsonSource(POINT_SOURCE))

    style.addLayer(
        FillLayer("earthpulse-square-fill", SQUARE_SOURCE).withProperties(
            PropertyFactory.fillColor("#176B50"),
            PropertyFactory.fillOpacity(0.18f)
        )
    )
    style.addLayer(
        LineLayer("earthpulse-square-line", SQUARE_SOURCE).withProperties(
            PropertyFactory.lineColor("#176B50"),
            PropertyFactory.lineWidth(2.5f)
        )
    )
    style.addLayer(
        CircleLayer("earthpulse-point", POINT_SOURCE).withProperties(
            PropertyFactory.circleRadius(8f),
            PropertyFactory.circleColor("#176B50"),
            PropertyFactory.circleStrokeColor("#FFFFFF"),
            PropertyFactory.circleStrokeWidth(3f)
        )
    )
}

/** Aggiorna punto e quadrato (o li nasconde se place è null). */
fun showSelection(style: Style, place: SelectedPlace?) {
    val square = style.getSourceAs<GeoJsonSource>(SQUARE_SOURCE) ?: return
    val point = style.getSourceAs<GeoJsonSource>(POINT_SOURCE) ?: return

    if (place == null) {
        square.setGeoJson(EMPTY_GEOJSON)
        point.setGeoJson(EMPTY_GEOJSON)
        return
    }

    // GeoJSON: coordinate in ordine [longitudine, latitudine]
    val ring = analysisSquare(place, ANALYSIS_SIDE_KM)
        .joinToString(",") { (lat, lon) -> "[$lon,$lat]" }
    square.setGeoJson(
        """{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[$ring]]}}"""
    )
    point.setGeoJson(
        """{"type":"Feature","properties":{},"geometry":{"type":"Point","coordinates":[${place.longitude},${place.latitude}]}}"""
    )
}

/** Sposta la mappa sul punto con un'animazione. */
fun flyTo(map: MapLibreMap, latitude: Double, longitude: Double, zoom: Double = 13.0) {
    map.animateCamera(CameraUpdateFactory.newLatLngZoom(LatLng(latitude, longitude), zoom), 900)
}
