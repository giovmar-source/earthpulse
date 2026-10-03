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
- [x] Venere: altitudine e gravità (Magellan, PDS)
- [ ] Rimandati con motivo: temperatura della Luna (Diviner: nessun file globale piccolo, solo 2,8 GB da ridurre), minerali e geologia di Marte (formati e legende non verificabili), forme vere di Fobos e Vesta (modelli 3D)
- [x] Nomi ufficiali IAU del luogo toccato e 47 siti di atterraggio con fonte e precisione
- [ ] Altitudine più dettagliata (8–16 pixel per grado): file da 8–33 MB, indirizzi da verificare
- [x] Nuovi corpi con immagini reali: Mercurio, Venere, Cerere, Vesta, Fobos, Encelado, Titano
- [x] Dati del telerilevamento con valori numerici: Luna (torio, ferro, idrogeno, gravità), Marte (acqua, inerzia termica, magnetismo), Mercurio (magnesio), Cerere (idrogeno); tocco sul globo con tutti i valori
- [x] Sole dal vivo (NASA SDO, 5 viste)
- [x] Mappa del Sistema solare: posizioni vere in ogni data, orbite calcolate, Cerere e Vesta dal JPL, eventi osservabili
- [ ] Lune minori di Saturno, Plutone, Caronte (fonti da trovare fuori da Trek)
- [x] Sonde nello spazio sulla mappa (JPL Horizons): Voyager, New Horizons, Parker, Solar Orbiter, BepiColombo, Juno, JUICE, Europa Clipper, Psyche, Lucy, Hera, OSIRIS-APEX
- [ ] Sonde in orbita intorno a Luna e Marte (LRO, Danuri, MRO, MAVEN…): posizione sul globo del corpo

## Fase 2b · Terra per professionisti
- [x] Acqua e allagamenti dal radar Sentinel-1 (adesso contro un anno o un mese prima)
- [x] Pioggia e umidità del suolo rispetto alla norma (NASA POWER)
- [x] Incendi attivi entro un raggio (NASA FIRMS, serve la chiave gratuita FIRMS_MAP_KEY)
- [x] Mare: temperatura con anomalia e clorofilla (NOAA)
- [x] Suolo impermeabilizzato (Copernicus HRL 2018, Europa)
- [ ] Movimenti del terreno EGMS: serve account EU Login e archivio dei dati sul server
- [ ] Pericolo di incendio EFFIS e aree bruciate (verificare il nome del livello)
- [ ] Allagamenti GFM (servizio globale pronto): confermare la licenza commerciale con EODC

## Fase 3 · Pronto per la vendita (tecnico) — predisposta, da accendere (docs/DEPLOY.md)
- [x] Pagina "Crediti e licenze" con tutte le fonti (registro unico `src/sources.py`) e `docs/LICENZE.md` con lo stato commerciale di ogni fonte
- [x] Fonti adatte alla vendita, attivabili con una variabile: qualità dell'aria via server (Open-Meteo commerciale), ricerca luoghi Geoapify, ritardo Meteosat di 1 ora, budget mensile Copernicus
- [x] Account Supabase (login con link via email), luoghi salvati, avvisi (tabelle e sicurezza in `supabase/schema.sql`)
- [x] Piani Gratis / Pro / Istituzionale con limiti (luoghi al giorno, esportazioni, luoghi salvati, avvisi), spenti finché `PLANS_ENFORCED` non è attivo
- [x] Pagamenti Paddle predisposti ma spenti (webhook con firma verificata)
- [x] Esportazioni: scheda del luogo in PDF, GeoTIFF degli indici, CSV delle serie
- [x] Avvisi automatici via email (incendi, acqua nuova) con `scripts/run_alerts.py`
- [x] Configurazione di produzione: Cloudflare Pages (`web/public/_headers`), Render a pagamento (`render.production.yaml`)
- [ ] Accendere: chiave FIRMS, poi Supabase, poi il resto dopo la verifica (ordine in `docs/DEPLOY.md`)
- [ ] Prezzi del piano Pro e del piano istituzionale

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
