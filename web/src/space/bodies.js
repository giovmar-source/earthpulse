// "Oltre la Terra": i corpi celesti mostrati e le loro schede.
// I corpi con texture null usano la mappa "Immagine" preparata dal server
// (mosaici NASA Solar System Treks): fonti in src/planet_layers.py.
// Mappe: Luna, Marte e Giove da Solar System Scope (CC BY 4.0); lune di Giove
// da mosaici USGS Astrogeology (pubblico dominio), elaborati dal progetto
// open source amarcher/solar-system.

const SSS = 'Mappa: Solar System Scope (CC BY 4.0), da dati NASA'
const USGS = 'Mappa: NASA/JPL/USGS Astrogeology (Voyager, Galileo), pubblico dominio'
const NH = 'Mappa: NASA/Johns Hopkins APL/Southwest Research Institute (New Horizons, PIA11707), pubblico dominio; in grigio le zone mai fotografate'

// Anelli di Saturno: raggi dal centro in raggi equatoriali di Saturno (60 268 km).
// Anello C 74 658–92 000 km, B 92 000–117 580 km, divisione di Cassini fino a 122 170 km,
// anello A fino a 136 775 km con la lacuna di Encke a 133 589 km. Opacità indicativa.
const R_SAT = 60268
const SATURN_RINGS = {
  inner: 74658 / R_SAT,
  outer: 136775 / R_SAT,
  bands: [
    [74658 / R_SAT, 92000 / R_SAT, '#8f8371', 0.35],
    [92000 / R_SAT, 117580 / R_SAT, '#dccdab', 0.85],
    [117580 / R_SAT, 122170 / R_SAT, '#6b6253', 0.08],
    [122170 / R_SAT, 133400 / R_SAT, '#cbbb99', 0.6],
    [133400 / R_SAT, 133780 / R_SAT, '#6b6253', 0.06],
    [133780 / R_SAT, 136775 / R_SAT, '#cbbb99', 0.55],
  ],
}

export const BODIES = [
  {
    key: 'moon', name: 'Luna', group: 'Terra', texture: 'textures/space/moon.jpg', credit: SSS, live: { type: 'moon' },
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
    key: 'mars', name: 'Marte', group: 'Pianeti', texture: 'textures/space/mars.jpg', credit: SSS, live: { type: 'planet', target: 'Mars', label: 'Marte' },
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
    key: 'jupiter', name: 'Giove', group: 'Giove', texture: 'textures/space/jupiter.jpg', credit: SSS, live: { type: 'jupiter' },
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
    key: 'io', name: 'Io', group: 'Giove', texture: 'textures/space/io.jpg', credit: USGS, live: { type: 'jupiter' },
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
    key: 'europa', name: 'Europa', group: 'Giove', texture: 'textures/space/europa.jpg', credit: USGS, live: { type: 'jupiter' },
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
    key: 'ganymede', name: 'Ganimede', group: 'Giove', texture: 'textures/space/ganymede.jpg', credit: USGS, live: { type: 'jupiter' },
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
    key: 'callisto', name: 'Callisto', group: 'Giove', texture: 'textures/space/callisto.jpg', credit: USGS, live: { type: 'jupiter' },
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
  // ---- Corpi con mappe scaricate dal server (NASA Solar System Treks): texture null
  {
    key: 'phobos', name: 'Fobos', group: 'Marte', texture: null, live: { type: 'planet', target: 'Mars', label: 'Marte' },
    tagline: 'La luna più grande di Marte: un sasso di 27 km che un giorno si sbriciolerà.',
    facts: [
      ['Dimensioni', '27 × 22 × 18 km (non è sferico: qui è disegnato come una sfera)'],
      ['Distanza da Marte', 'circa 6000 km dalla superficie'],
      ['Un giro intorno a Marte', '7 ore e 39 minuti, più veloce di un giorno marziano'],
    ],
    story: 'Gira così vicino a Marte che le maree lo avvicinano di quasi 2 metri ogni secolo: tra qualche ' +
      'decina di milioni di anni si spezzerà in un anello o cadrà sul pianeta. Il grande cratere Stickney ' +
      'è largo 9 km, un terzo della luna.',
    missions: ['Mars Express (ESA): numerosi sorvoli ravvicinati', 'MMX (JAXA): missione per raccoglierne campioni e riportarli sulla Terra'],
  },
  {
    key: 'mercury', name: 'Mercurio', group: 'Pianeti', texture: null, live: { type: 'planet', target: 'Mercury', label: 'Mercurio' },
    tagline: 'Il pianeta più piccolo e più vicino al Sole, con un nucleo di ferro enorme.',
    facts: [
      ['Diametro', '4879 km (poco più grande della Luna)'],
      ['Distanza dal Sole', 'circa 58 milioni di km'],
      ['Un anno', '88 giorni terrestri'],
      ['Un giorno (da un\'alba all\'altra)', '176 giorni terrestri'],
      ['Temperatura', 'da −180 °C di notte a +430 °C di giorno'],
    ],
    story: 'Il nucleo metallico occupa circa l\'85% del raggio del pianeta. Nonostante il caldo, nei crateri ' +
      'vicino ai poli, sempre in ombra, MESSENGER ha trovato ghiaccio d\'acqua.',
    missions: ['MESSENGER (NASA): in orbita dal 2011 al 2015, ha mappato tutto il pianeta',
      'BepiColombo (ESA e JAXA): ingresso in orbita previsto a fine 2026'],
  },
  {
    key: 'venus', name: 'Venere', group: 'Pianeti', texture: null, live: { type: 'planet', target: 'Venus', label: 'Venere' },
    tagline: 'Il pianeta più caldo: sotto nubi di acido solforico, una superficie vista solo con il radar.',
    facts: [
      ['Diametro', '12 104 km (quasi come la Terra)'],
      ['Distanza dal Sole', 'circa 108 milioni di km'],
      ['Un giorno (rotazione)', '243 giorni terrestri, al contrario degli altri pianeti'],
      ['Un anno', '225 giorni terrestri'],
      ['Al suolo', 'circa 464 °C e una pressione 92 volte quella terrestre'],
    ],
    story: 'Le nubi nascondono sempre la superficie: la mappa è un\'immagine radar della sonda Magellan. ' +
      'Le zone chiare sono terreni ruvidi, come colate di lava e montagne; quelle scure pianure lisce.',
    missions: ['Magellan (NASA, 1990-1994): ha mappato con il radar il 98% della superficie',
      'Venus Express (ESA, 2006-2014) e Akatsuki (JAXA, 2015-2024) hanno studiato l\'atmosfera',
      'EnVision (ESA), VERITAS e DAVINCI (NASA): missioni previste negli anni 2030'],
  },
  {
    key: 'ceres', name: 'Cerere', group: 'Asteroidi', texture: null, live: null,
    tagline: 'Il pianeta nano della fascia degli asteroidi, con macchie di sale lucenti.',
    facts: [
      ['Diametro', 'circa 940 km'],
      ['Distanza dal Sole', 'circa 414 milioni di km (tra Marte e Giove)'],
      ['Un giorno', '9 ore'],
      ['Un anno', '4,6 anni terrestri'],
    ],
    story: 'È l\'oggetto più grande della fascia degli asteroidi. Le macchie chiare del cratere Occator sono ' +
      'depositi di sali (carbonato di sodio) lasciati da acqua salata risalita dall\'interno.',
    missions: ['Dawn (NASA): in orbita dal 2015 al 2018'],
  },
  {
    key: 'vesta', name: 'Vesta', group: 'Asteroidi', texture: null, live: null,
    tagline: 'Un mondo mancato: un asteroide con crosta, mantello e nucleo, come un piccolo pianeta.',
    facts: [
      ['Diametro medio', 'circa 525 km'],
      ['Distanza dal Sole', 'circa 353 milioni di km'],
      ['Un giorno', '5 ore e 20 minuti'],
      ['Un anno', '3,6 anni terrestri'],
    ],
    story: 'Al polo sud c\'è il bacino da impatto Rheasilvia, largo circa 500 km, con un picco centrale ' +
      'tra i più alti del Sistema solare. Molti meteoriti caduti sulla Terra (le eucriti) vengono da Vesta.',
    missions: ['Dawn (NASA): in orbita dal 2011 al 2012'],
  },
  {
    key: 'enceladus', name: 'Encelado', group: 'Saturno', texture: null, live: { type: 'planet', target: 'Saturn', label: 'Saturno' },
    tagline: 'Una luna di ghiaccio che spruzza nello spazio l\'acqua del suo oceano.',
    facts: [
      ['Diametro', '504 km'],
      ['Distanza da Saturno', 'circa 238 000 km'],
      ['Un giro intorno a Saturno', '1,4 giorni'],
    ],
    story: 'Dalle "strisce di tigre" vicino al polo sud escono getti di vapore e cristalli di ghiaccio che ' +
      'alimentano uno degli anelli di Saturno. Vengono da un oceano sotto la crosta: Cassini li ha attraversati ' +
      'e vi ha trovato sali e molecole organiche. I colori della mappa sono potenziati.',
    missions: ['Cassini (NASA, ESA, ASI): intorno a Saturno dal 2004 al 2017'],
  },
  {
    key: 'titan', name: 'Titano', group: 'Saturno', texture: null, live: { type: 'planet', target: 'Saturn', label: 'Saturno' },
    tagline: 'La luna con un\'atmosfera più densa della nostra e laghi di metano.',
    facts: [
      ['Diametro', '5150 km (più grande di Mercurio)'],
      ['Distanza da Saturno', 'circa 1,2 milioni di km'],
      ['Un giro intorno a Saturno', '16 giorni'],
      ['Al suolo', 'circa −180 °C e una pressione 1,5 volte quella terrestre'],
    ],
    story: 'Una foschia arancione nasconde la superficie: la mappa è ripresa nel vicino infrarosso, che la ' +
      'attraversa. Ci sono dune, fiumi e laghi, ma di metano ed etano liquidi. Nel 2005 la sonda europea ' +
      'Huygens è atterrata sulla sua superficie.',
    missions: ['Cassini-Huygens (NASA, ESA, ASI): 2004-2017, con l\'atterraggio di Huygens nel 2005',
      'Dragonfly (NASA): un drone che volerà su Titano, arrivo previsto nel 2034'],
  },
  // ---- Giganti esterni e Plutone (mappe nel sito)
  {
    key: 'saturn', name: 'Saturno', group: 'Saturno', texture: 'textures/space/saturn.jpg', credit: SSS,
    flattening: 0.098, rings: SATURN_RINGS, distance: 8, live: { type: 'planet', target: 'Saturn', label: 'Saturno' },
    tagline: 'Il pianeta degli anelli: così leggero che, in media, è meno denso dell\'acqua.',
    facts: [
      ['Diametro', '120 536 km all\'equatore (9,4 volte la Terra)'],
      ['Distanza dal Sole', 'circa 1,43 miliardi di km'],
      ['Un giorno', 'circa 10 ore e 33 minuti'],
      ['Un anno', '29,4 anni terrestri'],
      ['Lune conosciute', 'oltre 270'],
    ],
    story: 'Gli anelli sono fatti di miliardi di frammenti di ghiaccio, da granelli a blocchi grandi come case: ' +
      'gli anelli principali hanno un diametro di circa 270 000 km ma sono spessi in genere da pochi metri a ' +
      'qualche decina. Sul globo sono disegnati alle distanze reali dal centro del pianeta; ' +
      'la loro trasparenza è indicativa.',
    missions: ['Pioneer 11 (1979), Voyager 1 e 2 (1980-1981): i primi sorvoli',
      'Cassini-Huygens (NASA, ESA, ASI): in orbita dal 2004 al 2017'],
  },
  {
    key: 'uranus', name: 'Urano', group: 'Esterni', texture: 'textures/space/uranus.jpg', credit: SSS,
    flattening: 0.023, live: { type: 'planet', target: 'Uranus', label: 'Urano' },
    tagline: 'Il gigante di ghiaccio che ruota "coricato" su un fianco.',
    facts: [
      ['Diametro', '51 118 km (4 volte la Terra)'],
      ['Distanza dal Sole', 'circa 2,9 miliardi di km'],
      ['Un giorno', 'circa 17 ore e 14 minuti'],
      ['Un anno', '84 anni terrestri'],
      ['Inclinazione dell\'asse', 'circa 98°: ogni polo resta al sole per 42 anni'],
    ],
    story: 'Il colore azzurro viene dal metano dell\'atmosfera, che assorbe la luce rossa. Sotto le nubi ' +
      'c\'è un mantello di acqua, ammoniaca e metano ad alta pressione. La mappa mostra le sue tenui bande ' +
      'di nubi: dal 1986 nessuna sonda è più tornata.',
    missions: ['Voyager 2 (NASA): l\'unico sorvolo, nel 1986',
      'Osservato oggi dal telescopio spaziale James Webb e da Hubble'],
  },
  {
    key: 'neptune', name: 'Nettuno', group: 'Esterni', texture: 'textures/space/neptune.jpg', credit: SSS,
    flattening: 0.017, live: { type: 'planet', target: 'Neptune', label: 'Nettuno' },
    tagline: 'Il pianeta più lontano, con i venti più veloci del Sistema solare.',
    facts: [
      ['Diametro', '49 528 km (quasi 4 volte la Terra)'],
      ['Distanza dal Sole', 'circa 4,5 miliardi di km'],
      ['Un giorno', 'circa 16 ore'],
      ['Un anno', '165 anni terrestri'],
      ['Venti', 'fino a circa 2000 km/h'],
    ],
    story: 'È stato scoperto nel 1846 con il calcolo, prima ancora che al telescopio: le irregolarità ' +
      'dell\'orbita di Urano indicavano un pianeta sconosciuto. Tritone, la sua luna più grande, gira al ' +
      'contrario ed è probabilmente un oggetto catturato dalla fascia di Kuiper.',
    missions: ['Voyager 2 (NASA): l\'unico sorvolo, nel 1989',
      'Osservato oggi dal telescopio spaziale James Webb e da Hubble'],
  },
  {
    key: 'pluto', name: 'Plutone', group: 'Esterni', texture: 'textures/space/pluto.jpg', credit: NH,
    live: { type: 'planet', target: 'Pluto', label: 'Plutone' },
    tagline: 'Il pianeta nano con un "cuore" di ghiaccio di azoto.',
    facts: [
      ['Diametro', '2377 km (più piccolo della nostra Luna)'],
      ['Distanza dal Sole', 'in media 5,9 miliardi di km (39,5 UA)'],
      ['Un giorno', '6,4 giorni terrestri'],
      ['Un anno', '248 anni terrestri'],
      ['Lune', '5; Caronte è grande la metà di Plutone'],
    ],
    story: 'La grande regione chiara a forma di cuore è Tombaugh Regio; la sua metà occidentale, Sputnik ' +
      'Planitia, è una pianura di ghiaccio di azoto che si rinnova lentamente. È classificato come pianeta ' +
      'nano dal 2006. New Horizons lo ha fotografato bene solo da un lato: il resto della mappa è grigio.',
    missions: ['New Horizons (NASA): sorvolo del 14 luglio 2015'],
  },
]
