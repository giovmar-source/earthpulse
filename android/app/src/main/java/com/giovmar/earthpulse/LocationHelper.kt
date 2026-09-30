package com.giovmar.earthpulse

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Looper
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import kotlin.coroutines.resume

/**
 * Posizione attuale del telefono con le API standard di Android
 * (nessuna libreria esterna). Da chiamare solo dopo aver ottenuto
 * il permesso di localizzazione.
 *
 * 1. usa l'ultima posizione nota se ha meno di 2 minuti;
 * 2. altrimenti attende una nuova posizione (GPS o rete) fino a 20 s.
 * Restituisce null se la posizione non è disponibile.
 */
@SuppressLint("MissingPermission")
suspend fun currentLocation(context: Context): Location? {
    val manager = context.getSystemService(Context.LOCATION_SERVICE) as? LocationManager
        ?: return null

    val providers = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
        .filter { runCatching { manager.isProviderEnabled(it) }.getOrDefault(false) }
    if (providers.isEmpty()) return null

    val recent = providers
        .mapNotNull { runCatching { manager.getLastKnownLocation(it) }.getOrNull() }
        .maxByOrNull { it.time }
    if (recent != null && System.currentTimeMillis() - recent.time < 2 * 60 * 1000) {
        return recent
    }

    val fresh = withTimeoutOrNull(20_000) {
        suspendCancellableCoroutine { continuation ->
            val listener = object : LocationListener {
                override fun onLocationChanged(location: Location) {
                    manager.removeUpdates(this)
                    if (continuation.isActive) continuation.resume(location)
                }

                // Metodi obbligatori sulle versioni di Android precedenti alla 11.
                override fun onProviderEnabled(provider: String) {}
                override fun onProviderDisabled(provider: String) {}
                @Deprecated("Richiesto solo per compatibilità")
                override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
            }
            providers.forEach { provider ->
                runCatching {
                    manager.requestLocationUpdates(provider, 0L, 0f, listener, Looper.getMainLooper())
                }
            }
            continuation.invokeOnCancellation { manager.removeUpdates(listener) }
        }
    }

    // Se non arriva una posizione nuova, meglio una vecchia che niente.
    return fresh ?: recent
}
