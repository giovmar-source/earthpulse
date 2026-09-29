package com.giovmar.earthpulse

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.net.URLEncoder
import java.util.Locale

// ------------------------------------------------------------------
// CONFIGURAZIONE DEL BACKEND
// ------------------------------------------------------------------
//
// Backend pubblicato su Render (HTTPS): funziona ovunque, senza PC acceso.
// Piano gratuito: dopo 15 minuti di inattività il server si addormenta
// e la prima richiesta attende circa un minuto in più.
private const val REMOTE_BACKEND_URL = "https://earthpulse-api-tk6r.onrender.com"

// Backend sul PC, per sviluppare e provare modifiche al codice Python.
// Richiede uvicorn avviato e il tunnel adb:
//     adb reverse tcp:8000 tcp:8000
private const val LOCAL_BACKEND_URL = "http://127.0.0.1:8000"

// false = Render (uso normale); true = backend sul PC (sviluppo).
const val USE_LOCAL_BACKEND = false

val BACKEND_BASE_URL: String =
    if (USE_LOCAL_BACKEND) LOCAL_BACKEND_URL else REMOTE_BACKEND_URL

// L'analisi richiede ~20 s, ma il risveglio del server gratuito
// aggiunge circa un minuto: lasciamo un margine ampio.
private const val CONNECT_TIMEOUT_MS = 15_000
private const val ANALYSIS_READ_TIMEOUT_MS = 180_000
private const val SEARCH_READ_TIMEOUT_MS = 90_000
private const val WAKE_UP_READ_TIMEOUT_MS = 90_000


// ------------------------------------------------------------------
// MODELLI DEI DATI (specchio del JSON di /api/v1/ndvi/analysis)
// ------------------------------------------------------------------

data class LatestObservation(
    val date: String,
    val acquisitionDateTime: String,
    val itemId: String,
    val ndviMean: Double,
    val validPercentage: Double?,
    val cloudCoverPercent: Double?,
    val daysSinceObservation: Int,
    val isRecent: Boolean,
    val maxDaysForRecent: Int
)

data class BaselinePoint(
    val date: String,
    val ndviMean: Double
)

data class Baseline(
    val ndviMedian: Double?,
    val ndviMin: Double?,
    val ndviMax: Double?,
    val samples: Int,
    val support: String,
    val years: List<Int>,
    val windowDays: Int,
    val observations: List<BaselinePoint>
)

data class Comparison(
    val deltaNdvi: Double?,
    val anomalyPercent: Double?,
    val percentMeaningful: Boolean,
    val classification: String
)

data class AnalysisQuality(
    val minValidPercentage: Double,
    val recentPeriodStart: String,
    val recentPeriodEnd: String,
    val recentScenesFound: Int,
    val recentScenesEvaluated: Int,
    val recentScenesRejected: Int,
    val baselineScenesFound: Int,
    val baselineScenesEvaluated: Int,
    val baselineScenesRejected: Int,
    val technicalErrors: Int
)

data class PlaceAnalysis(
    val status: String,
    val referenceDate: String,
    val processedAt: String,
    val latest: LatestObservation?,
    val baseline: Baseline,
    val comparison: Comparison,
    val messages: List<String>,
    val quality: AnalysisQuality,
    val methodology: Map<String, String>,
    val warning: String,
    val processingSeconds: Double?
)

data class PlaceSearchResult(
    val name: String,
    val displayName: String,
    val latitude: Double,
    val longitude: Double
)

/** Errore con un messaggio già comprensibile per l'utente. */
class ApiException(message: String) : Exception(message)


// ------------------------------------------------------------------
// CHIAMATE AL BACKEND
// ------------------------------------------------------------------

object EarthPulseApi {

    /**
     * "Sveglia" il server all'apertura dell'app, così il risveglio
     * avviene mentre l'utente sceglie il luogo. Gli errori sono ignorati.
     */
    suspend fun wakeUp() {
        runCatching { getJson("$BACKEND_BASE_URL/health", WAKE_UP_READ_TIMEOUT_MS) }
    }

    suspend fun analyzePlace(
        latitude: Double,
        longitude: Double,
        sideKm: Double = ANALYSIS_SIDE_KM
    ): PlaceAnalysis {
        val url = String.format(
            Locale.US,
            "%s/api/v1/ndvi/analysis?lat=%.6f&lon=%.6f&side_km=%.2f",
            BACKEND_BASE_URL, latitude, longitude, sideKm
        )
        val json = getJson(url, ANALYSIS_READ_TIMEOUT_MS)
        return parseAnalysis(JSONObject(json))
    }

    suspend fun searchPlaces(query: String): List<PlaceSearchResult> {
        val encoded = URLEncoder.encode(query.trim(), "UTF-8")
        val url = "$BACKEND_BASE_URL/api/v1/geocode?q=$encoded&limit=5"
        val root = JSONObject(getJson(url, SEARCH_READ_TIMEOUT_MS))
        val results = root.getJSONArray("results")
        return (0 until results.length()).map { i ->
            val r = results.getJSONObject(i)
            PlaceSearchResult(
                name = r.optString("name"),
                displayName = r.optString("display_name"),
                latitude = r.getDouble("latitude"),
                longitude = r.getDouble("longitude")
            )
        }
    }

    /** GET su un thread di rete; traduce i problemi in ApiException. */
    private suspend fun getJson(url: String, readTimeoutMs: Int): String =
        withContext(Dispatchers.IO) {
            val connection = (URL(url).openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = readTimeoutMs
                setRequestProperty("Accept", "application/json")
            }
            try {
                // Fase 1: connessione. Se fallisce, il backend non è
                // raggiungibile (server spento o tunnel adb non attivo).
                try {
                    connection.connect()
                } catch (e: IOException) {
                    throw ApiException(
                        if (USE_LOCAL_BACKEND)
                            "Impossibile contattare il backend ($BACKEND_BASE_URL). " +
                                    "Controlla che uvicorn sia avviato sul PC e che il " +
                                    "tunnel sia attivo (adb reverse tcp:8000 tcp:8000)."
                        else
                            "Impossibile contattare il server EarthPulse. " +
                                    "Controlla la connessione a internet e riprova."
                    )
                }

                // Fase 2: attesa della risposta (calcolo sul server).
                val code = connection.responseCode
                if (code in 200..299) {
                    connection.inputStream.bufferedReader().use { it.readText() }
                } else {
                    val body = connection.errorStream
                        ?.bufferedReader()?.use { it.readText() }
                    throw ApiException(describeHttpError(code, body))
                }
            } catch (e: ApiException) {
                throw e
            } catch (e: SocketTimeoutException) {
                throw ApiException(
                    "Il server non ha risposto in tempo. L'elaborazione delle " +
                            "immagini satellitari può essere lenta: riprova."
                )
            } catch (e: IOException) {
                throw ApiException(
                    "Connessione con il backend interrotta: ${e.message ?: "errore di rete"}."
                )
            } finally {
                connection.disconnect()
            }
        }

    private fun describeHttpError(code: Int, body: String?): String {
        // FastAPI restituisce {"detail": "..."} oppure {"detail": [...]}
        val detail = runCatching {
            val d = JSONObject(body ?: "").opt("detail")
            when (d) {
                is String -> d
                is JSONObject -> d.optString("message", d.toString())
                is JSONArray -> d.optJSONObject(0)?.optString("msg")
                else -> null
            }
        }.getOrNull()

        val prefix = when (code) {
            400, 422 -> "Richiesta non valida"
            404 -> "Dati non trovati"
            502 -> "Servizio satellitare non raggiungibile"
            else -> "Errore del server ($code)"
        }
        return if (detail.isNullOrBlank()) prefix else "$prefix: $detail"
    }
}


// ------------------------------------------------------------------
// LETTURA DEL JSON
// ------------------------------------------------------------------

private fun JSONObject.optDoubleOrNull(key: String): Double? =
    if (!has(key) || isNull(key)) null
    else optDouble(key).takeIf { it.isFinite() }

private fun parseAnalysis(root: JSONObject): PlaceAnalysis {
    val latestJson = root.optJSONObject("latest_observation")
    val latest = latestJson?.let { o ->
        LatestObservation(
            date = o.getString("date"),
            acquisitionDateTime = o.optString("acquisition_datetime"),
            itemId = o.optString("item_id"),
            ndviMean = o.getDouble("ndvi_mean"),
            validPercentage = o.optDoubleOrNull("valid_percentage"),
            cloudCoverPercent = o.optDoubleOrNull("cloud_cover_percent"),
            daysSinceObservation = o.optInt("days_since_observation"),
            isRecent = o.optBoolean("is_recent"),
            maxDaysForRecent = o.optInt("max_days_for_recent", 20)
        )
    }

    val b = root.getJSONObject("baseline")
    val obsJson = b.optJSONArray("observations") ?: JSONArray()
    val yearsJson = b.optJSONArray("years") ?: JSONArray()
    val baseline = Baseline(
        ndviMedian = b.optDoubleOrNull("ndvi_median"),
        ndviMin = b.optDoubleOrNull("ndvi_min"),
        ndviMax = b.optDoubleOrNull("ndvi_max"),
        samples = b.optInt("samples"),
        support = b.optString("support"),
        years = (0 until yearsJson.length()).map { yearsJson.getInt(it) },
        windowDays = b.optInt("window_days"),
        observations = (0 until obsJson.length()).mapNotNull { i ->
            val p = obsJson.getJSONObject(i)
            p.optDoubleOrNull("ndvi_mean")?.let { BaselinePoint(p.getString("date"), it) }
        }
    )

    val c = root.getJSONObject("comparison")
    val comparison = Comparison(
        deltaNdvi = c.optDoubleOrNull("delta_ndvi"),
        anomalyPercent = c.optDoubleOrNull("anomaly_percent"),
        percentMeaningful = c.optBoolean("percent_meaningful"),
        classification = c.optString("classification")
    )

    val q = root.getJSONObject("quality")
    val period = q.optJSONObject("recent_period") ?: JSONObject()
    val quality = AnalysisQuality(
        minValidPercentage = q.optDouble("min_valid_percentage", 70.0),
        recentPeriodStart = period.optString("start_date"),
        recentPeriodEnd = period.optString("end_date"),
        recentScenesFound = q.optInt("recent_scenes_found"),
        recentScenesEvaluated = q.optInt("recent_scenes_evaluated"),
        recentScenesRejected = q.optInt("recent_scenes_rejected_quality"),
        baselineScenesFound = q.optInt("baseline_scenes_found"),
        baselineScenesEvaluated = q.optInt("baseline_scenes_evaluated"),
        baselineScenesRejected = q.optInt("baseline_scenes_rejected_quality"),
        technicalErrors = q.optJSONArray("errors")?.length() ?: 0
    )

    val messagesJson = root.optJSONArray("messages") ?: JSONArray()
    val methodologyJson = root.optJSONObject("methodology") ?: JSONObject()

    return PlaceAnalysis(
        status = root.optString("status"),
        referenceDate = root.optString("reference_date"),
        processedAt = root.optString("processed_at"),
        latest = latest,
        baseline = baseline,
        comparison = comparison,
        messages = (0 until messagesJson.length()).map { messagesJson.getString(it) },
        quality = quality,
        methodology = methodologyJson.keys().asSequence()
            .associateWith { methodologyJson.optString(it) },
        warning = root.optString("warning"),
        processingSeconds = root.optDoubleOrNull("processing_seconds")
    )
}
