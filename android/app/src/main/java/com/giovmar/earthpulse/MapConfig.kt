package com.giovmar.earthpulse

import org.osmdroid.tileprovider.tilesource.ITileSource
import org.osmdroid.tileprovider.tilesource.OnlineTileSourceBase
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.MapTileIndex

// ------------------------------------------------------------------
// MAPPA DI BASE
// ------------------------------------------------------------------
//
// Chiave gratuita CARTO Basemaps (uso non commerciale: fino a 5 milioni
// di richieste al mese). Si richiede con la sola email su
// https://carto.com/basemaps/  →  incollarla qui tra le virgolette.
//
// Le mappe CARTO Voyager mostrano i nomi in caratteri latini anche dove
// la mappa OpenStreetMap standard li mostra in arabo, cirillico, ecc.
// Se la chiave è vuota l'app usa la mappa OpenStreetMap standard.
const val CARTO_API_KEY = "cb1_44gc_1_27d4c6b63145aae6bc6f9495"

private object CartoVoyagerTileSource : OnlineTileSourceBase(
    "CartoVoyager",
    0,
    20,
    256,
    ".png",
    arrayOf("https://basemaps.cartocdn.com/rastertiles/voyager/"),
    "© OpenStreetMap contributors, © CARTO"
) {
    // Formato: .../voyager/{z}/{x}/{y}@2x.png?key=...
    // @2x = tessere ad alta densità, più nitide sugli schermi dei telefoni.
    override fun getTileURLString(pMapTileIndex: Long): String =
        baseUrl +
                MapTileIndex.getZoom(pMapTileIndex) + "/" +
                MapTileIndex.getX(pMapTileIndex) + "/" +
                MapTileIndex.getY(pMapTileIndex) + "@2x.png?key=" + CARTO_API_KEY
}

/** Mappa di base in uso: CARTO se c'è la chiave, altrimenti OpenStreetMap. */
fun baseMapTileSource(): ITileSource =
    if (CARTO_API_KEY.isNotBlank()) CartoVoyagerTileSource else TileSourceFactory.MAPNIK

/** Attribuzione obbligatoria della mappa in uso. */
fun baseMapAttribution(): String =
    if (CARTO_API_KEY.isNotBlank()) "Mappa © OpenStreetMap contributors, © CARTO"
    else "Mappa © OpenStreetMap contributors"
