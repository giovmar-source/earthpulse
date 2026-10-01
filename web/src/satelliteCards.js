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
}
