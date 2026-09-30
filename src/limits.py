"""
Limiti di risorse del server (piano gratuito di Render: 512 MB di memoria).

Le elaborazioni pesanti (archivio Landsat, isole di calore, luci notturne)
leggono e tengono in memoria matrici di diversi MB: se l'app le chiede tutte
insieme il server può esaurire la memoria e riavviarsi. Questo semaforo ne
lascia partire al massimo HEAVY_SLOTS alla volta; le altre aspettano il turno.
"""

import threading
from contextlib import contextmanager

HEAVY_SLOTS = 2
_heavy = threading.BoundedSemaphore(HEAVY_SLOTS)


@contextmanager
def heavy_task():
    with _heavy:
        yield
