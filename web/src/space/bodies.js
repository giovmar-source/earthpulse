// "Oltre la Terra": i corpi celesti mostrati e le loro schede.
// Mappe: Luna, Marte e Giove da Solar System Scope (CC BY 4.0); lune di Giove
// da mosaici USGS Astrogeology (pubblico dominio), elaborati dal progetto
// open source amarcher/solar-system.

const SSS = 'Mappa: Solar System Scope (CC BY 4.0), da dati NASA'
const USGS = 'Mappa: NASA/JPL/USGS Astrogeology (Voyager, Galileo), pubblico dominio'

export const BODIES = [
  {
    key: 'moon', name: 'Luna', group: 'Terra', texture: 'textures/space/moon.jpg', credit: SSS,
    tagline: "L'unico satellite naturale della Terra, e l'unico altro mondo dove l'uomo ha camminato.",
    facts: [
      ['Diametro', '3474 km (poco più di un quarto della Terra)'],
      ['Distanza media', '384 400 km'],
      ['Gravità', '1,62 m/s², un sesto di quella terrestre'],
      ['Un giorno lunare', '29,5 giorni terrestri'],
      ['Temperatura', 'da −173 °C di notte a +127 °C di giorno'],
    ],
    story: 'Ruota su se stessa nello stesso tempo in cui gira intorno alla Terra: per questo ci mostra ' +
      'sempre la stessa faccia. Le macchie scure sono i "mari", pianure di lava solidificata; ' +
      'le zone chiare sono altopiani antichi pieni di crateri.',
    missions: ['Lunar Reconnaissance Orbiter (NASA): la fotografa dal 2009 con dettagli di mezzo metro',
      'Chandrayaan-2 (India) e Danuri (Corea del Sud) in orbita',
      'Programma Artemis (NASA, ESA e partner): il ritorno degli astronauti'],
  },
  {
    key: 'mars', name: 'Marte', group: 'Pianeti', texture: 'textures/space/mars.jpg', credit: SSS,
    tagline: 'Il pianeta rosso: deserti di ossidi di ferro, vulcani giganti e antichi letti di fiumi.',
    facts: [
      ['Diametro', '6779 km (circa metà della Terra)'],
      ['Distanza dalla Terra', 'da 55 a 400 milioni di km'],
      ['Gravità', '3,71 m/s², il 38% di quella terrestre'],
      ['Un giorno (sol)', '24 ore e 37 minuti'],
      ['Un anno', '687 giorni terrestri'],
      ['Temperatura media', 'circa −63 °C'],
    ],
    story: "Ha il vulcano più alto del Sistema solare, l'Olympus Mons (circa 22 km), e un canyon lungo " +
      "4000 km, la Valles Marineris. Le calotte polari sono di ghiaccio d'acqua e anidride carbonica.",
    missions: ['Mars Reconnaissance Orbiter (NASA) e Mars Express (ESA) in orbita',
      'Rover Perseverance (NASA) nel cratere Jezero, con campioni di roccia da riportare sulla Terra',
      'ExoMars Trace Gas Orbiter (ESA) misura i gas della sua atmosfera'],
  },
  {
    key: 'jupiter', name: 'Giove', group: 'Giove', texture: 'textures/space/jupiter.jpg', credit: SSS,
    tagline: 'Il gigante del Sistema solare: potrebbe contenere più di mille Terre.',
    facts: [
      ['Diametro', '139 820 km (11 volte la Terra)'],
      ['Distanza dal Sole', '778 milioni di km'],
      ['Un giorno', '9 ore e 56 minuti, il più corto tra i pianeti'],
      ['Un anno', '11,9 anni terrestri'],
      ['Lune conosciute', 'oltre 90'],
    ],
    story: 'Non ha una superficie solida: è fatto soprattutto di idrogeno ed elio. Le bande colorate ' +
      'sono correnti di nubi; la Grande Macchia Rossa è una tempesta più grande della Terra, ' +
      'osservata da oltre 150 anni.',
    missions: ['Juno (NASA) in orbita dal 2016, vola sopra i poli', 'JUICE (ESA) e Europa Clipper (NASA) in viaggio verso le sue lune'],
  },
  {
    key: 'io', name: 'Io', group: 'Giove', texture: 'textures/space/io.jpg', credit: USGS,
    tagline: 'Il mondo più vulcanico del Sistema solare.',
    facts: [
      ['Diametro', '3643 km (come la nostra Luna)'],
      ['Distanza da Giove', '421 700 km'],
      ['Un giro intorno a Giove', '1,8 giorni'],
    ],
    story: "La gravità di Giove e delle altre lune lo \"strizza\" continuamente: l'attrito scalda " +
      "l'interno e alimenta centinaia di vulcani attivi. I colori gialli e arancioni sono zolfo.",
    missions: ['Galileo (NASA, 1995-2003)', 'Juno (NASA): sorvoli ravvicinati nel 2023 e 2024'],
  },
  {
    key: 'europa', name: 'Europa', group: 'Giove', texture: 'textures/space/europa.jpg', credit: USGS,
    tagline: 'Sotto il ghiaccio, un oceano di acqua salata più grande di tutti quelli terrestri.',
    facts: [
      ['Diametro', '3122 km'],
      ['Distanza da Giove', '671 000 km'],
      ['Un giro intorno a Giove', '3,6 giorni'],
    ],
    story: 'La crosta di ghiaccio è attraversata da lunghe fratture. Sotto, a decine di km di ' +
      'profondità, c\'è un oceano liquido: uno dei posti migliori per cercare ambienti adatti alla vita.',
    missions: ['Europa Clipper (NASA): lanciata nel 2024, arrivo previsto nel 2030', 'JUICE (ESA): due sorvoli previsti'],
  },
  {
    key: 'ganymede', name: 'Ganimede', group: 'Giove', texture: 'textures/space/ganymede.jpg', credit: USGS,
    tagline: 'La luna più grande del Sistema solare: è più grande del pianeta Mercurio.',
    facts: [
      ['Diametro', '5268 km'],
      ['Distanza da Giove', '1 070 400 km'],
      ['Un giro intorno a Giove', '7,2 giorni'],
    ],
    story: 'È l\'unica luna con un campo magnetico tutto suo, che crea piccole aurore. Le zone chiare ' +
      'e scure sono ghiaccio di età diverse; anche qui, in profondità, ci sarebbe un oceano.',
    missions: ['JUICE (ESA): lanciata nel 2023, entrerà in orbita intorno a Ganimede nel 2034'],
  },
  {
    key: 'callisto', name: 'Callisto', group: 'Giove', texture: 'textures/space/callisto.jpg', credit: USGS,
    tagline: 'La superficie più craterizzata del Sistema solare: un archivio di 4 miliardi di anni.',
    facts: [
      ['Diametro', '4821 km'],
      ['Distanza da Giove', '1 882 700 km'],
      ['Un giro intorno a Giove', '16,7 giorni'],
    ],
    story: 'Quasi niente ha cambiato la sua superficie dalla nascita del Sistema solare: ogni cratere ' +
      'è rimasto lì. Il grande bacino Valhalla, con i suoi anelli, è largo circa 3800 km.',
    missions: ['Galileo (NASA, 1995-2003)', 'JUICE (ESA): numerosi sorvoli previsti'],
  },
]
