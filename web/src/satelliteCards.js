// Schede dei satelliti (stessi dati verificati dell'app Android:
// ESA, eoPortal, NASA Science, Wikipedia).

export const SATELLITE_CARDS = {
  'sentinel-2': {
    title: 'Sentinel-2',
    agency: 'Copernicus · ESA / Unione Europea',
    image: 'img/sentinel2_exterior.jpg',
    credit: 'Immagine: ESA/ATG medialab · Licenza standard ESA',
    intro:
      'Due satelliti gemelli in orbita, sfasati tra loro, che fotografano tutte le terre ' +
      'emerse ogni 5 giorni in 13 bande, con dettagli fino a 10 metri.',
    facts: [
      ['Quota', '786 km, orbita eliosincrona'],
      ['Ora di passaggio', '10:30 del mattino'],
      ['Larghezza ripresa', '290 km'],
      ['Bande', '13 (risoluzione 10, 20 e 60 m)'],
      ['Massa al lancio', '1140 kg'],
      ['Lanci', '2A 2015 · 2B 2017 · 2C 2024'],
    ],
    inEarthPulse:
      'Analisi della vegetazione, colori reali, indici (acqua, umidità, costruito, ' +
      'clorofilla, neve, alghe, torbidità) e storie prima/dopo.',
    note: 'Dal 21 gennaio 2025 Sentinel-2C ha preso il posto di 2A, che continua con una campagna estesa.',
  },
  landsat: {
    title: 'Landsat 8 e 9',
    agency: 'NASA / USGS',
    image: 'img/landsat9.jpg',
    credit: 'Immagine: NASA · pubblico dominio',
    intro:
      "L'archivio satellitare più lungo al mondo: Landsat osserva le terre emerse dal 1972. " +
      'Landsat 8 e 9 lavorano in coppia e misurano sia la luce riflessa sia il calore.',
    facts: [
      ['Quota', '705 km, orbita eliosincrona'],
      ['Ora di passaggio', 'circa 10:12 del mattino'],
      ['Larghezza ripresa', '185 km'],
      ['Rivisita', '16 giorni ciascuno · 8 in coppia'],
      ['Strumenti', 'OLI-2 (9 bande, 30 m) e TIRS-2 (termico, 100 m)'],
      ['Lancio Landsat 9', '27 settembre 2021'],
    ],
    inEarthPulse:
      "Archivio dal 1984 (sezione “Nel tempo”) e temperatura delle superfici per le isole di calore.",
  },
  'suomi-npp': {
    title: 'Suomi NPP',
    agency: 'NASA / NOAA',
    image: 'img/suomi_npp.jpg',
    credit: 'Immagine: NASA · pubblico dominio',
    intro:
      "Satellite meteorologico e climatico. Il suo strumento VIIRS riprende l'intero pianeta " +
      'ogni giorno, anche di notte, e misura le luci delle città.',
    facts: [
      ['Quota', 'circa 830 km'],
      ['Passaggi', 'circa 13:30 e 1:30 ora locale'],
      ['Larghezza ripresa', '3000 km'],
      ['Strumento', 'VIIRS, 22 bande, banda giorno/notte'],
      ['Lancio', '28 ottobre 2011'],
    ],
    inEarthPulse: 'Luci notturne annuali (NASA Black Marble) dal 2012.',
    note: 'NOAA ha annunciato la fine della distribuzione dei suoi dati dal 1° novembre 2026: il lavoro passa a NOAA-20 e NOAA-21.',
  },
  'sentinel-5p': {
    title: 'Sentinel-5P',
    agency: 'Copernicus · ESA / Unione Europea',
    image: null,
    intro:
      "Il satellite europeo dedicato all'aria che respiriamo e al clima. Il suo spettrometro " +
      'TROPOMI misura ogni giorno, su tutto il pianeta, la quantità di diversi gas in atmosfera.',
    facts: [
      ['Quota', '824 km, orbita eliosincrona'],
      ['Ora di passaggio', 'circa 13:30'],
      ['Larghezza ripresa', '2600 km: tutta la Terra ogni giorno'],
      ['Strumento', 'TROPOMI, dall\'ultravioletto all\'infrarosso a onde corte'],
      ['Pixel', 'circa 5,5 × 3,5 km'],
      ['Gas misurati', 'NO₂, ozono, CO, metano, SO₂, formaldeide, aerosol'],
      ['Lancio', '13 ottobre 2017'],
    ],
    inEarthPulse: 'Mappe di biossido di azoto, metano e monossido di carbonio nella scheda Atmosfera.',
    note: '"P" sta per Precursore: fa da ponte in attesa degli strumenti Sentinel-4 e Sentinel-5 sui satelliti meteorologici.',
  },
  mtg: {
    title: 'Meteosat-12 (MTG-I1)',
    agency: 'EUMETSAT / ESA',
    image: null,
    intro:
      'Il primo Meteosat di terza generazione. È geostazionario: gira insieme alla Terra e resta ' +
      "sempre sopra lo stesso punto dell'equatore, così guarda Europa e Africa senza interruzioni.",
    facts: [
      ['Quota', 'circa 35 800 km, orbita geostazionaria'],
      ['Posizione', '0° di longitudine, sopra il Golfo di Guinea'],
      ['Strumento FCI', '16 canali, immagine completa ogni 10 minuti'],
      ['Dettaglio', 'da 0,5-1 km (visibile) a 2 km (infrarosso)'],
      ['Lightning Imager', 'il primo rilevatore di fulmini europeo in orbita geostazionaria, giorno e notte'],
      ['Lancio', '13 dicembre 2022, Ariane 5'],
      ['Servizio principale', 'dal 17 giugno 2025, al posto di Meteosat-10'],
    ],
    inEarthPulse: 'Nuvole in diretta, incendi attivi, fulmini e pioggia nella scheda Atmosfera.',
    note: "Erede dello strumento SEVIRI dei Meteosat di seconda generazione, con il doppio dei dettagli e più canali. Sul globo appare quasi fermo: è il bello dell'orbita geostazionaria.",
  },
}
