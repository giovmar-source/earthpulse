"""
Piani del prodotto e limiti. Un solo punto da cambiare per prezzi e limiti.

Scelte già prese (docs/ANALISI_PROGETTO.md): si limitano le analisi al giorno,
le esportazioni, i luoghi salvati e gli avvisi; NON la dimensione delle aree né
l'età dei dati. I prezzi sono ancora da decidere.

"Analisi" = un luogo diverso analizzato nel giorno (aprire più sezioni dello
stesso luogo conta una volta sola).
"""

PLANS = {
    "anonymous": {
        "label": "Senza account", "price": None,
        "limits": {"places_per_day": 5, "exports_per_day": 0, "saved_places": 0, "alerts": 0},
    },
    "free": {
        "label": "Gratis", "price": "0 €",
        "limits": {"places_per_day": 15, "exports_per_day": 3, "saved_places": 3, "alerts": 0},
        "features": ["Tutte le analisi e i dati", "15 luoghi al giorno", "3 esportazioni PDF o GeoTIFF al giorno",
                     "3 luoghi salvati"],
    },
    "pro": {
        "label": "Pro", "price": "da definire (mensile)",
        "limits": {"places_per_day": 300, "exports_per_day": 100, "saved_places": 100, "alerts": 25},
        "features": ["Analisi senza limiti pratici (300 luoghi al giorno)", "100 esportazioni al giorno",
                     "100 luoghi salvati", "25 avvisi automatici via email (incendi, acqua nuova)"],
    },
    "institutional": {
        "label": "Istituzionale", "price": "su preventivo",
        "limits": {"places_per_day": 3000, "exports_per_day": 1000, "saved_places": 2000, "alerts": 300},
        "features": ["Per università, enti pubblici e aziende", "Licenza per più persone",
                     "Limiti molto ampi e avvisi per tutto il territorio di interesse", "Supporto diretto"],
    },
}

PUBLIC_PLANS = ("free", "pro", "institutional")


def limits(plan: str) -> dict:
    return PLANS.get(plan, PLANS["free"])["limits"]
