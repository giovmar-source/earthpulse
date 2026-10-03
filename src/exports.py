"""
Esportazioni per chi lavora con i dati.

- GeoTIFF: valori di un indice (float32, NaN = nessun dato) sulla griglia UTM a
  10 m della scena Sentinel-2 scelta, georeferenziato, con fonte e data nei metadati:
  si apre in QGIS o ArcGIS.
- PDF: "scheda del luogo" con i numeri che l'utente ha sul pannello, le fonti di
  ogni sezione e l'avviso sui limiti dei dati. Il sito invia le sezioni già
  calcolate (niente nuove elaborazioni sul server).

Nel PDF si usa il carattere Helvetica: i simboli fuori dalla codifica Windows-1252
(pedici come in NO₂, il segno meno tipografico, emoji) vengono sostituiti o tolti.
"""

from __future__ import annotations

import io
import os
from datetime import datetime, timezone

import numpy as np

PRODUCT_NAME = os.environ.get("PRODUCT_NAME", "EarthPulse")
REPLACE = {"₂": "2", "₃": "3", "₄": "4", "₅": "5", "−": "-", "⁻": "-", "→": "->", "≈": "~", "≥": ">=", "≤": "<=",
           " ": " ", " ": " ", " ": " "}


# ------------------------------------------------------------------
# GeoTIFF
# ------------------------------------------------------------------

def index_geotiff(values: np.ndarray, valid: np.ndarray, grid, tags: dict) -> bytes:
    from rasterio.io import MemoryFile
    data = np.where(valid, values, np.nan).astype("float32")
    with MemoryFile() as memfile:
        with memfile.open(driver="GTiff", width=grid.width, height=grid.height, count=1, dtype="float32",
                          crs=grid.crs, transform=grid.transform, nodata=float("nan"),
                          compress="deflate", tiled=True, blockxsize=256, blockysize=256) as ds:
            ds.write(data, 1)
            ds.update_tags(**{k: str(v) for k, v in tags.items()})
        return memfile.read()


# ------------------------------------------------------------------
# PDF
# ------------------------------------------------------------------

def safe(text) -> str:
    text = str(text if text is not None else "")
    for a, b in REPLACE.items():
        text = text.replace(a, b)
    return text.encode("cp1252", "ignore").decode("cp1252")


def _escape(text: str) -> str:
    return safe(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def place_report(payload: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, leading=12.5)
    small = ParagraphStyle("small", parent=body, fontSize=7.8, leading=10, textColor=colors.HexColor("#555555"))
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22,
                        alignment=0, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15,
                        spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#0b5d3b"))

    place = payload.get("place") or {}
    lat, lon = float(place.get("lat", 0)), float(place.get("lon", 0))
    coords = f"{abs(lat):.4f}° {'N' if lat >= 0 else 'S'}, {abs(lon):.4f}° {'E' if lon >= 0 else 'O'}"
    created = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    story = [
        Paragraph(_escape(f"{PRODUCT_NAME} · Scheda del luogo"), small),
        Paragraph(_escape(place.get("name") or coords), h1),
        Paragraph(_escape(" · ".join(p for p in (place.get("context"), coords) if p)), body),
        Paragraph(_escape(f"Generata il {created}"), small),
        Spacer(1, 4 * mm),
    ]
    for section in payload.get("sections") or []:
        story.append(Paragraph(_escape(section.get("title", "")), h2))
        facts = [[Paragraph(_escape(k), body), Paragraph(f"<b>{_escape(v)}</b>", body)]
                 for k, v in (section.get("facts") or []) if v not in (None, "")]
        if facts:
            table = Table(facts, colWidths=[70 * mm, 100 * mm])
            table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(table)
        for note in section.get("notes") or []:
            story.append(Spacer(1, 1.5 * mm))
            story.append(Paragraph(_escape(note), body))
        if section.get("attribution"):
            story.append(Spacer(1, 1 * mm))
            story.append(Paragraph(_escape(section["attribution"]), small))
    story += [
        Spacer(1, 6 * mm),
        Paragraph(_escape(
            "Avvertenza: valori ricavati da dati satellitari e modelli, con le risoluzioni e i limiti descritti "
            f"nella Metodologia di {PRODUCT_NAME}. Non sostituiscono misure sul campo né documenti ufficiali. "
            "Le organizzazioni che forniscono i dati non approvano né sponsorizzano questo prodotto."), small),
    ]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawString(18 * mm, 10 * mm, safe(f"{PRODUCT_NAME} · {coords} · {created}"))
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Pagina {doc.page}")
        canvas.restoreState()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm,
                            title=safe(f"{PRODUCT_NAME} · {place.get('name') or coords}"), author=PRODUCT_NAME)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
