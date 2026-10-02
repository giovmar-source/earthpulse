"""
Catalogo delle mappe di "Oltre la Terra": per ogni corpo celeste, da dove
vengono le immagini e i dati, in che formato sono e come vanno colorati.

Due tipi di mappe:
- "trek": mosaici di immagini (o mappe qualitative) dalle tessere WMTS di
  NASA Solar System Treks, unite dal server in un'unica mappa 2048 × 1024;
- "grid": dati numerici originali dal Planetary Data System (PDS) della NASA,
  di pubblico dominio. Il server li legge, li colora con una scala nota e può
  dire il valore in ogni punto: la legenda ha numeri veri.

Formati delle griglie ("source"):
- img: raster binario (dtype, righe × colonne, fattore di scala);
- cells: tabella di testo con i limiti di ogni cella (lat min/max, lon min/max, valore);
- points: tabella di testo con il centro di ogni cella (lat, lon, valore).
Le longitudini possono partire da −180 o da 0: il server porta tutto a −180…180
(bordo sinistro della mappa = 180° ovest), con il nord in alto.
"""

PDS = "https://pds-geosciences.wustl.edu"
LP = f"{PDS}/missions/lunarp/reduced"

# Scale di colori (dal basso all'alto)
TOPO = [(110, 40, 150), (60, 90, 220), (70, 190, 230), (90, 200, 110),
        (240, 230, 110), (230, 140, 70), (190, 70, 60), (255, 255, 255)]
SEQUENTIAL = [(68, 1, 84), (70, 50, 126), (54, 92, 141), (39, 127, 142),
              (31, 161, 135), (74, 193, 109), (160, 218, 57), (253, 231, 37)]
DIVERGING = [(33, 102, 172), (67, 147, 195), (146, 197, 222), (209, 229, 240),
             (247, 247, 247), (253, 219, 199), (244, 165, 130), (214, 96, 77), (178, 24, 43)]

NASA_PDS = "NASA, PDS Geosciences Node · pubblico dominio"

BODIES = {
    # ------------------------------------------------------------------ Luna
    "moon": {
        "radius_km": 1737.4,
        "layers": {
            "elevation": {
                "kind": "grid", "label": "Altitudine", "unit": "m", "digits": 0, "legend_unit": "km",
                "source": {"format": "img", "url": f"{PDS}/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_4.img",
                           "dtype": "<i2", "shape": (720, 1440), "scale": 0.5, "lon0": 0},
                "colors": TOPO, "stops": [-8000, -4000, -2000, 0, 2000, 4000, 6000, 10000],
                "label_scale": 0.001, "hillshade": True,
                "reference": "rispetto al raggio medio di 1737,4 km",
                "caption": ("Altitudine misurata dall'altimetro laser LOLA. Il punto più basso è nel "
                            "bacino Polo Sud–Aitken, il più grande cratere da impatto della Luna."),
                "attribution": f"Altitudine: LRO LOLA (LDEM_4), {NASA_PDS}",
            },
            "thorium": {
                "kind": "grid", "label": "Torio", "unit": "ppm", "digits": 1,
                "source": {"format": "cells", "url": f"{LP}/thoriumhd.txt", "res": 0.5,
                           "columns": (0, 1, 2, 3, 4)},
                "colors": SEQUENTIAL, "stops": "auto",
                "caption": ("Torio in superficie, in parti per milione, dallo spettrometro a raggi gamma "
                            "di Lunar Prospector. Le concentrazioni alte segnano le rocce KREEP "
                            "(potassio, terre rare, fosforo), raccolte soprattutto attorno all'Oceanus "
                            "Procellarum: un indizio della storia vulcanica della faccia visibile."),
                "attribution": f"Torio: Lunar Prospector GRS (Lawrence et al.), {NASA_PDS}",
            },
            "iron": {
                "kind": "grid", "label": "Ferro", "unit": "% FeO", "digits": 1,
                "source": {"format": "cells", "url": f"{LP}/ironhd.txt", "res": 0.5,
                           "columns": (0, 1, 2, 3, 4)},
                "colors": SEQUENTIAL, "stops": "auto",
                "caption": ("Ossido di ferro (FeO, percentuale in peso) da Lunar Prospector. I mari, "
                            "colate di basalto, sono ricchi di ferro; gli altopiani chiari, fatti di "
                            "anortosite, ne hanno poco."),
                "attribution": f"Ferro: Lunar Prospector GRS (Lawrence et al.), {NASA_PDS}",
            },
            "hydrogen": {
                "kind": "grid", "label": "Idrogeno", "unit": "ppm", "digits": 0,
                "source": {"format": "cells", "url": f"{LP}/hydrogenhd.txt", "res": 0.5,
                           "columns": (0, 1, 2, 3, 4)},
                "colors": SEQUENTIAL, "stops": "auto",
                "caption": ("Idrogeno nel primo metro di suolo, in parti per milione, dallo spettrometro "
                            "a neutroni di Lunar Prospector. L'aumento ai poli è compatibile con ghiaccio "
                            "d'acqua nei crateri sempre in ombra. Risoluzione di decine di km: i singoli "
                            "crateri non si distinguono."),
                "attribution": f"Idrogeno: Lunar Prospector NS (Lawrence, Feldman et al.), {NASA_PDS}",
            },
            "gravity": {
                "kind": "grid", "label": "Gravità", "unit": "mGal", "digits": 0,
                "source": {"format": "img", "url": f"{PDS}/grail/grail-l-lgrs-5-rdr-v1/grail_1001/rsdmap/gggrx_0660pm_anom_l320.img",
                           "dtype": "<f4", "shape": (721, 1440), "scale": 1.0, "lon0": -180},
                "colors": DIVERGING, "stops": "auto_diverging",
                "caption": ("Anomalia di gravità in aria libera misurata dalle sonde gemelle GRAIL: "
                            "rosso dove la gravità è più forte della media, blu dove è più debole. I "
                            "\"mascon\" rossi sotto i grandi mari circolari sono masse dense sepolte."),
                "attribution": f"Gravità: GRAIL GRGM660PRIM (NASA/GSFC), {NASA_PDS}",
            },
        },
    },
    # ------------------------------------------------------------------ Marte
    "mars": {
        "radius_km": 3389.5,
        "layers": {
            "elevation": {
                "kind": "grid", "label": "Altitudine", "unit": "m", "digits": 0, "legend_unit": "km",
                "source": {"format": "img", "url": f"{PDS}/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg004/megt90n000cb.img",
                           "dtype": ">i2", "shape": (720, 1440), "scale": 1.0, "lon0": 0},
                "colors": TOPO, "stops": [-8000, -4000, -2000, 0, 2000, 4000, 8000, 21000],
                "label_scale": 0.001, "hillshade": True,
                "reference": "rispetto all'areoide (il \"livello del mare\" di Marte)",
                "caption": ("Altitudine misurata dall'altimetro laser MOLA: le pianure basse del nord e "
                            "gli altopiani craterizzati del sud differiscono di alcuni chilometri. In "
                            "bianco i vulcani di Tharsis e l'Olympus Mons."),
                "attribution": f"Altitudine: MGS MOLA (MEGDR), {NASA_PDS}",
            },
            "water": {
                "kind": "grid", "label": "Acqua nel suolo", "unit": "% in peso", "digits": 1,
                "source": {"format": "points", "url": f"{PDS}/ody/ody-m-grs-5-elements-v1/odgm_xxxx/data/smoothed/h2o_sr_5x5.tab",
                           "res": 5.0, "columns": (0, 1, 2), "nodata_above": 9000},
                "colors": SEQUENTIAL, "stops": "auto",
                "caption": ("Acqua (sotto forma di ghiaccio o legata ai minerali) nel primo metro di "
                            "suolo, in percentuale del peso, dallo spettrometro a raggi gamma di Mars "
                            "Odyssey. Celle di 5°. Le alte latitudini sono escluse dalla mappa (in "
                            "grigio): lì il ghiaccio è così abbondante da falsare la misura degli altri elementi."),
                "attribution": f"Acqua: Mars Odyssey GRS (Boynton et al. 2007), {NASA_PDS}",
            },
            "thermal_inertia": {
                "kind": "grid", "label": "Inerzia termica", "unit": "J m⁻² K⁻¹ s⁻½", "digits": 0,
                "source": {"format": "img", "url": f"{PDS}/mgs/mgs-m-tes-special-v1/global_ti_60n_50s_8ppd.img",
                           "dtype": "<f4", "shape": (882, 2880), "scale": 1.0, "lon0": -180,
                           "lat_top": 60.125, "valid_min": 1, "valid_max": 5000},
                "colors": SEQUENTIAL, "stops": "auto",
                "caption": ("Quanto il suolo resiste ai cambi di temperatura tra giorno e notte, dallo "
                            "spettrometro TES. Valori bassi: polvere fine e soffice; valori alti: "
                            "sabbia grossa, suolo cementato, roccia affiorante. Tra 60° N e 50° S."),
                "attribution": f"Inerzia termica: MGS TES (Christensen et al.), {NASA_PDS}",
            },
            "magnetism": {
                "kind": "grid", "label": "Magnetismo della crosta", "unit": "nT", "digits": 0,
                "source": {"format": "points", "url": "https://mgs-mager.gsfc.nasa.gov/publications/grl_28_connerney/data/grl_28_connerney_map_data.txt",
                           "res": 1.0, "columns": (4, 5, 0), "min_columns": 6, "zero_is_nodata_beyond": 85},
                "colors": DIVERGING, "stops": "auto_diverging",
                "caption": ("Componente verticale del campo magnetico a 400 km di quota (magnetometro di "
                            "Mars Global Surveyor). Marte oggi non ha un campo globale, ma le rocce "
                            "antiche del sud conservano un magnetismo fossile a strisce."),
                "attribution": "Magnetismo: MGS MAG/ER (Connerney et al. 2001), NASA/GSFC · pubblico dominio",
                "note_point": "a 400 km di quota",
            },
            "night_ir": {
                "kind": "trek", "label": "Roccia o polvere",
                "trek_body": "Mars", "trek_id": "THEMIS_NightIR_ControlledMosaics_100m_v2_oct2018", "ext": "png",
                "legend": {"gradient": ["#141414", "#f0f0f0"],
                           "labels": ["Polvere e sabbia fine", "Roccia e suolo compatto"]},
                "caption": ("Immagine all'infrarosso termico ripresa di notte: le superfici che trattengono "
                            "il calore (roccia, suolo cementato) appaiono chiare, quelle che si raffreddano "
                            "subito (polvere, sabbia fine) scure."),
                "attribution": "THEMIS-IR notte: NASA/JPL/ASU (Mars Odyssey), tramite NASA Solar System Treks",
            },
        },
    },
    # ------------------------------------------------------------------ Mercurio
    "mercury": {
        "radius_km": 2439.4,
        "layers": {
            "photo": {
                "kind": "trek", "label": "Immagine",
                "trek_body": "Mercury", "trek_id": "Mercury_MESSENGER_MDIS_Basemap_MD3Color_Mosaic_Global_665m", "ext": "jpg",
                "attribution": "Immagine: NASA/JHUAPL/Carnegie (MESSENGER MDIS), tramite NASA Solar System Treks",
            },
            "enhanced": {
                "kind": "trek", "label": "Colori potenziati",
                "trek_body": "Mercury", "trek_id": "Mercury_MESSENGER_MDIS_Basemap_EnhancedColor_Mosaic_Global_665m", "ext": "jpg",
                "caption": ("Falsi colori ottenuti combinando più lunghezze d'onda (componenti principali): "
                            "esaltano le differenze di composizione. Le pianure lisce appaiono color "
                            "ocra, i materiali scuri e poveri di riflettanza in blu. Non sono colori reali."),
                "attribution": "Colori potenziati: NASA/JHUAPL/Carnegie (MESSENGER MDIS), tramite NASA Solar System Treks",
            },
            "magnesium": {
                "kind": "grid", "label": "Magnesio", "unit": "Mg/Si", "digits": 2,
                "source": {"format": "img", "url": f"{PDS}/messenger/mess-h-xrs-3-rdr-maps-v1/messxrs_3001/data/maps/xrs_map_mg_si_20150424.img",
                           "dtype": "u1", "shape": (720, 1440), "scale": 0.0030668824, "lon0": -180, "nodata": 0},
                "colors": SEQUENTIAL, "stops": "auto",
                "caption": ("Rapporto tra magnesio e silicio in superficie, dallo spettrometro a raggi X di "
                            "MESSENGER. La grande regione ricca di magnesio potrebbe essere il segno di un "
                            "antico impatto gigante che ha scavato il mantello. Copertura parziale, "
                            "soprattutto nell'emisfero nord."),
                "attribution": f"Magnesio: MESSENGER XRS (Nittler et al. 2020), {NASA_PDS}",
            },
        },
    },
    # ------------------------------------------------------------------ Venere
    "venus": {
        "radius_km": 6051.8,
        "layers": {
            "photo": {
                "kind": "trek", "label": "Radar",
                "trek_body": "Venus", "trek_id": "Venus_Magellan_C3-MDIR_Global_Mosaic_2025m", "ext": "png",
                "attribution": "Radar: NASA/JPL (Magellan), tramite NASA Solar System Treks",
            },
        },
    },
    # ------------------------------------------------------------------ Cerere
    "ceres": {
        "radius_km": 469.7,
        "layers": {
            "photo": {
                "kind": "trek", "label": "Immagine",
                "trek_body": "Ceres", "trek_id": "Ceres_Dawn_FC_DLR_global_59ppd_Feb2016", "ext": "jpg",
                "attribution": "Immagine: NASA/JPL-Caltech/UCLA/MPS/DLR/IDA (Dawn), tramite NASA Solar System Treks",
            },
            "hydrogen": {
                "kind": "grid", "label": "Idrogeno", "unit": "% acqua equivalente", "digits": 1,
                "source": {"format": "cells", "url": "https://sbnarchive.psi.edu/pds3/dawn/grand/DWNCGRD_2/DATA/HYDROGEN/GRD_SMOOTHED_HYDROGEN_MAP.TAB",
                           "res": 1.0, "columns": (1, 2, 3, 4, 5)},
                "colors": SEQUENTIAL, "stops": "auto",
                "caption": ("Idrogeno nel primo metro di suolo, espresso come percentuale di acqua "
                            "equivalente, dallo spettrometro GRaND di Dawn. Aumenta verso i poli: sotto "
                            "una sottile crosta c'è ghiaccio. Risoluzione di circa 600 km."),
                "attribution": "Idrogeno: Dawn GRaND (Prettyman et al.), NASA PDS Small Bodies Node · pubblico dominio",
            },
        },
    },
    # ------------------------------------------------------------------ Vesta
    "vesta": {
        "radius_km": 262.7,
        "layers": {
            "photo": {
                "kind": "trek", "label": "Immagine",
                "trek_body": "Vesta", "trek_id": "Vesta_Dawn_HAMO_TrueClr_DLR_global_74ppd_IAU", "ext": "png",
                "attribution": "Immagine: NASA/JPL-Caltech/UCLA/MPS/DLR/IDA (Dawn), tramite NASA Solar System Treks",
            },
        },
    },
    # ------------------------------------------------------------------ Fobos
    "phobos": {
        "radius_km": 11.1,
        "layers": {
            "photo": {
                "kind": "trek", "label": "Immagine",
                "trek_body": "Phobos", "trek_id": "Phobos_Viking_Mosaic_40ppd_DLRcontrol", "ext": "jpg",
                "attribution": "Immagine: NASA/JPL (Viking), controllo DLR, tramite NASA Solar System Treks",
            },
        },
    },
    # ------------------------------------------------------------------ Encelado
    "enceladus": {
        "radius_km": 252.1,
        "layers": {
            "photo": {
                "kind": "trek", "label": "Immagine",
                "trek_body": "Enceladus", "trek_id": "Enceladus_cyl_KH", "ext": "jpg",
                "attribution": "Immagine: NASA/JPL/Space Science Institute (Cassini), mosaico P. Schenk (LPI), tramite NASA Solar System Treks",
            },
        },
    },
    # ------------------------------------------------------------------ Titano
    "titan": {
        "radius_km": 2574.7,
        "layers": {
            "photo": {
                "kind": "trek", "label": "Immagine",
                "trek_body": "Titan", "trek_id": "TitanISS2018June.proj.scale", "ext": "jpg",
                "attribution": "Immagine: NASA/JPL/Space Science Institute (Cassini ISS, 938 nm), mosaico E. Karkoschka, tramite NASA Solar System Treks",
            },
        },
    },
}
