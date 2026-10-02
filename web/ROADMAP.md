# Roadmap

Obiettivo: un prodotto per professionisti (università, pubblica amministrazione, aziende),
da vendere in tutta l'UE con un piano gratuito limitato e un piano Pro.
Analisi completa delle scelte: `docs/ANALISI_PROGETTO.md`. Fonti: `docs/FONTI.md`.

## Regole per ogni nuova funzione (pensando alla vendita)
- Ogni fonte di dati passa dal backend, dietro un "adattatore": se una fonte non è più
  adatta (licenza, costi) si cambia in un punto solo.
- Ogni dato porta con sé la sua attribuzione; niente fonti "solo non commerciali" nelle
  funzioni nuove.
- Risultati in cache sul server: meno costi, più velocità, quote rispettate.
- Testi dell'interfaccia raccolti in pochi file, pronti per la traduzione.
- Nome del prodotto in un solo punto (`web/src/brand.js`).

## Fase 1 · Qualità delle analisi (Terra)
- [x] Nome del prodotto centralizzato
- [x] Nome del luogo accanto alle coordinate (geocoding inverso, servizio sostituibile)
- [x] Grafico "stesso periodo, anni diversi" per tutti gli indici
- [x] Colori reali: dalle bande a 16 bit con curva tonale morbida (sabbia e deserti non più gialli)
- [x] Gas dal satellite rifatto: andamento sul luogo (30 / 90 / 365 giorni) + confronto con l'anno prima
- [x] Nuvole: animazione 24 ore con un'immagine ogni 30 minuti (sfondo invariato)
- [x] Globo realistico all'apertura (NASA Blue Marble, fino allo zoom 7)

## Fase 2 · Oltre la Terra
- [x] Mappe tematiche: altitudine di Luna e Marte (LOLA, MOLA dal PDS, legenda in km, altitudine del punto toccato) e "Roccia o polvere" su Marte (THEMIS notturno)
- [ ] Altre mappe con scala numerica: temperatura della Luna (Diviner, file grandi: lettura a pezzi), gravità di Venere (Magellan), forme vere di Fobos e Vesta (modelli 3D)
- [ ] Altitudine più dettagliata (16 pixel per grado) e nomi dei crateri e dei luoghi (IAU Gazetteer) sul punto toccato
- [x] Nuovi corpi con immagini reali: Mercurio, Venere, Cerere, Vesta, Fobos, Encelado, Titano
- [x] Dati del telerilevamento con valori numerici: Luna (torio, ferro, idrogeno, gravità), Marte (acqua, inerzia termica, magnetismo), Mercurio (magnesio), Cerere (idrogeno); tocco sul globo con tutti i valori
- [ ] Ancora da fare: Sole dal vivo (SDO); lune minori di Saturno, Plutone, Caronte (fonti da trovare fuori da Trek)
- [ ] Orbite delle sonde (JPL Horizons): LRO, Danuri, MRO, Mars Express, MAVEN, TGO, Juno…

## Fase 3 · Pronto per la vendita (tecnico)
- [ ] Pagina "Crediti e licenze" con tutte le attribuzioni
- [ ] Fonti adatte all'uso commerciale: ricerca luoghi sul nostro server, Open-Meteo commerciale o CAMS diretto, immagini EUMETSAT con almeno 1 ora di ritardo in modalità commerciale, budget Sentinel Hub
- [ ] Account utenti e piani: analisi al giorno, esportazioni PDF/CSV/GeoTIFF, luoghi salvati con avvisi automatici, piano istituzionale
- [ ] Hosting di produzione (frontend su Cloudflare Pages o Netlify, backend a pagamento), monitoraggio, backup

## Fase 4 · Rifinitura (promemoria)
- [ ] Interno dei satelliti nella scheda: Landsat 9, Suomi NPP, Sentinel-5P, Meteosat-12
- [ ] Lingue: inglese, poi francese e spagnolo
- [ ] Copyright delle immagini: immagini ESA CC BY-SA 3.0 IGO o permesso ESA
- [ ] Rilettura di tutti i testi con tono formale

## Fase 5 · Commerciale
- [ ] Nome definitivo e verifica del marchio (TMview/EUIPO, UIBM), dominio .com e .it
- [ ] Beta gratuita pubblica
- [ ] Commercialista, Partita IVA, Merchant of Record (Paddle o Lemon Squeezy)
- [ ] Pagine legali: privacy, cookie, termini di servizio, recesso
- [ ] Lancio del piano Pro

## Più avanti
- Sentinel-1 (radar), EGMS (movimenti del terreno), Sentinel-3 (mare), incendi FIRMS,
  consumo di suolo Copernicus, pioggia GPM, umidità del suolo SMAP, PRISMA (ASI)
- Curva stagionale dell'anno per ogni indice (piano Pro)
- IRIDE, se nasce un progetto con la pubblica amministrazione
