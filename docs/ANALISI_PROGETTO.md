# EarthPulse · Analisi del progetto (2 ottobre 2026)

Risposte alle domande su prodotto, "Oltre la Terra", pubblicazione e monetizzazione.
Questo documento serve come base per la prossima roadmap. Non è una consulenza legale o
fiscale: i punti su tasse e contratti vanno confermati con un commercialista e un legale.

---

## 1. Prodotto (Terra)

### 1.1 Promemoria per le ultime fasi
Le voci sono nella sezione "Promemoria" di `web/ROADMAP.md`:
- l'interno dei satelliti (Landsat 9, Suomi NPP, Sentinel-5P, MTG);
- la lingua inglese, poi francese e spagnolo;
- la revisione del copyright delle immagini;
- la revisione del tono dei testi.

**Lingue.** Il sito va reso "traducibile": tutti i testi passano da un dizionario per
lingua, con la libreria react-i18next. L'inglese è prioritario. Francese e spagnolo li
traduco io; conviene però una rilettura da madrelingua almeno della Metodologia. Il
backend restituisce già testi (didascalie, messaggi), che vanno tradotti anche lì.

**Tono formale.** Rileggo tutti i testi con un glossario fisso, per esempio:

| Oggi | Proposta |
|---|---|
| "Un po' meno verde del solito" | "Lieve calo rispetto alla media 2023–2025" |
| "Più verde del solito" | "Valore superiore alla media del periodo" |
| "Come negli anni scorsi" | "In linea con la media pluriennale" |
| "Tocca un punto" | "Selezionare un punto sul globo" |

**Immagini ESA.** Con la Licenza standard ESA le immagini sono solo per uso non
commerciale. Le strade sono due:
- sostituirle con immagini ESA rilasciate in CC BY-SA 3.0 IGO, che ammettono l'uso
  commerciale con attribuzione (ce ne sono molte su esa.int);
- chiedere un permesso scritto tramite il modulo
  https://blogs.esa.int/forms/brand-licensing-contact-form/ oppure scrivendo a
  spaceinimages@esa.int.

Le immagini NASA sono di pubblico dominio, a due condizioni: niente logo NASA e nessuna
frase che faccia pensare a un'approvazione della NASA.

### 1.2 Gialli troppo accesi (deserti e sabbia quasi bianchi)
Oggi la scala dei colori è lineare con un "punto di bianco": tutto ciò che lo supera
diventa bianco. La soluzione è una **curva tonale morbida** che comprime le alte luci
invece di tagliarle, del tipo arcoseno iperbolico o "highlight compression", come fanno
i prodotti "Highlight optimized" di Sentinel Hub. Il punto di bianco va calcolato sul
99,5° percentile della scena. La stessa correzione va applicata a Sentinel-2 e
all'archivio Landsat. La provo su Agadez, Dubai e Napoli prima di consegnarla.

### 1.3 Nome del luogo accanto alle coordinate
Si fa con il "geocoding inverso", cioè dalle coordinate al nome del comune o della
località:
- **beta:** endpoint del backend con cache, che interroga Nominatim (1 richiesta al
  secondo);
- **versione commerciale:** serve un servizio proprio (Photon o Nominatim installati sul
  server) oppure uno a pagamento (vedi 4.2).

### 1.4 Baseline e grafici per tutti gli indici
I dati ci sono già: il backend restituisce le singole osservazioni degli anni
precedenti. Propongo due grafici.

1. **"Stesso periodo, anni diversi"**, subito e per ogni indice, NDVI compreso.
   - Sull'asse orizzontale gli anni (2023, 2024, 2025, 2026).
   - Un punto per ogni immagine valida della finestra di ±15 giorni.
   - Una fascia grigia per l'intervallo minimo–massimo degli anni passati e una linea
     per la mediana (la baseline).
   - Il valore attuale evidenziato.

   È il grafico più chiaro per rispondere a "è normale per questo periodo?".
2. **"Andamento dell'anno"**, più avanti, eventualmente nel piano Pro.
   - La curva stagionale con le mediane mensili degli ultimi 3 anni, a confronto con
     l'anno in corso.
   - È più ricco, ma richiede circa 36 elaborazioni per luogo: va calcolato in anticipo
     o tenuto in cache.

### 1.5 Gas dal satellite: da rifare
Problemi attuali:
- una sola mappa, ma con un cerchio che sembra un cursore da trascinare;
- unità di misura poco intuitive (µmol/m²);
- manca un termine di confronto.

Proposta:
- **Andamento nel tempo sul luogo**: grafico dei valori giornalieri degli ultimi 90 giorni
  sopra il punto scelto, con l'API Statistical di Sentinel Hub. È la vista più
  comprensibile.
- **Confronto con lo stesso periodo dell'anno prima**: due mappe con il cursore, così ha
  senso spostarlo.
- **Lettura guidata**: per esempio "NO₂ sul luogo: 96 µmol/m², circa 2,3 volte la media
  della regione; valori tipici di una città media europea".
- Il cerchio del "luogo" diventa un contorno tratteggiato con un'etichetta, perché non
  sembri un comando.

### 1.6 Globo con la vista reale all'apertura
Si può fare, con una dissolvenza dal globo realistico alla mappa man mano che si zooma.
Le etichette restano sopra. Opzioni per le immagini:

- **NASA GIBS – Blue Marble**: è gratuito, ammette l'uso commerciale e copre il globo
  fino allo zoom 8, che basta per la vista d'insieme. È la scelta consigliata.
- **Più dettaglio oltre lo zoom 8**:
  - Esri World Imagery: 2 milioni di tasselli al mese gratis, poi 0,15 $ ogni 1000;
  - EOX Sentinel-2 cloudless con licenza commerciale.
- **Da evitare**: il servizio EOX gratuito e MapTiler Free, perché sono solo per uso non
  commerciale.

### 1.7 Nuvole: sfondo semplice con i confini
È facile: basta un'opzione **"Sfondo: immagine satellitare / mappa semplice"**, con
coste e confini da Natural Earth (dominio pubblico). Ha senso soprattutto per pioggia,
fulmini e incendi; le nuvole invece sono l'immagine stessa.

### 1.8 Altri satelliti e indici per la Terra (in futuro)

| Priorità | Dato | A cosa serve |
|---|---|---|
| Alta | **Sentinel-1** (radar) | Alluvioni sotto le nuvole, navi, terreno; anche di notte |
| Alta | **EGMS** (da Sentinel-1) | Movimenti del terreno millimetrici: frane, subsidenza, edifici |
| Alta | **Sentinel-3** | Temperatura del mare, colore dell'oceano (clorofilla), temperatura del suolo ogni giorno |
| Media | **NASA FIRMS** (MODIS/VIIRS) | Incendi attivi in tutto il mondo, quasi in tempo reale |
| Media | **Copernicus Land** (Imperviousness, CORINE) | Consumo di suolo ufficiale UE |
| Media | **GPM / IMERG** | Pioggia caduta, accumuli |
| Media | **SMAP** | Umidità del suolo |
| Bassa | **ECOSTRESS** | Temperatura a 70 m, diverse ore del giorno |
| Bassa | **EMIT** | Minerali e grandi perdite di metano |
| Bassa | **PRISMA** (ASI) | Iperspettrale italiano: ricerca, richiede registrazione |
| Bassa | **GRACE-FO** | Variazione delle acque sotterranee (scala regionale) |

---

## 2. Oltre la Terra

### 2.1 Orbite delle sonde, come per la Terra
Si può fare con **JPL Horizons**, servizio gratuito e senza account. Il backend chiede le
posizioni, le tiene in cache per qualche ora e il sito disegna l'orbita e il punto intorno
alla sfera, con una scheda cliccabile come per i satelliti della Terra.

ID Horizons (verificati sui codici NAIF):

| Corpo | Sonde (ID) |
|---|---|
| Luna | LRO (-85), Danuri (-155), Chandrayaan-2 (-152) |
| Marte | MRO (-74), Mars Express (-41), MAVEN (-202), TGO (-143), Mars Odyssey (-53) |
| Giove | Juno (-61) |
| In viaggio | Europa Clipper (-159), JUICE (-28) |

Che Horizons fornisca le traiettorie aggiornate per ciascuna sonda va verificato una per
una.

### 2.2 Altri corpi, solo con immagini vere
Corpi da aggiungere:
- **Mercurio** (MESSENGER);
- **Cerere e Vesta** (Dawn);
- **Fobos**;
- le lune di Saturno: **Titano, Encelado, Mimas, Teti, Dione, Rea, Giapeto** (Cassini);
- il **Sole**, con le immagini dal vivo di NASA SDO, aggiornate ogni pochi minuti e di
  pubblico dominio.

Casi particolari:
- **Venere**: c'è solo il radar Magellan, cioè dati veri ma non a luce visibile. Da
  inserire solo con un'etichetta chiara.
- **Plutone e Caronte, Tritone, lune di Urano**: sono stati fotografati solo in parte.
  Si possono mettere con le zone mai viste in grigio, come già per Europa e Callisto.
- **Saturno**: esistono mappe delle nubi ricavate da Cassini, da verificare.
- **Urano e Nettuno**: non esistono mappe reali, quindi restano fuori.

### 2.3 Analisi "come sulla Terra"
La chiave è **NASA Solar System Treks**: servizi gratuiti, senza account, di pubblico
dominio. Coprono Luna, Marte, Mercurio, Venere, Europa, Ganimede, Callisto, Io, Titano,
Fobos, Cerere, Vesta, Bennu e Ryugu.

Le loro mappe sono in proiezione equirettangolare, cioè **la stessa delle sfere 3D che
usiamo**: si possono caricare come "strati" intercambiabili, come gli indici della Terra.

| Corpo | Strati proposti |
|---|---|
| Luna | Colori (LRO WAC), Altitudine (LOLA), Composizione (ferro FeO e titanio TiO₂, utili per i mari basaltici e le risorse), Temperatura (Diviner), Ghiaccio ai poli (crateri in ombra perenne) |
| Marte | Colori (Viking), Altitudine (MOLA), Calore del suolo di giorno e di notte (THEMIS: inerzia termica, cioè roccia o polvere), Minerali idrati (CRISM/OMEGA: dove c'era acqua), Idrogeno/ghiaccio sotto la superficie (Mars Odyssey GRS) |
| Mercurio | Colori (MESSENGER), colori "esaltati" per la composizione, Altitudine |
| Europa, Ganimede | Ghiaccio e sali (Galileo) |
| Titano | Laghi e mari di metano (radar Cassini) |

Gli ID verificati per alcuni strati (per esempio `LRO_LOLA_ClrShade_Global_128ppd_v04`,
`Mars_MGS_MOLA_ClrShade_merge_global_463m`,
`THEMIS_DayIR_ControlledMosaics_100m_v2_oct2018`) sono in `docs/FONTI.md`. Gli altri
vanno cercati nei cataloghi Trek.

Passo successivo possibile: cliccare un punto della sfera e leggere coordinate,
altitudine e valore dello strato.

---

## 3. Pubblicazione

### 3.1 Serve un dominio?
- **Per farlo vedere ad amici e professori: no.** Basta l'indirizzo gratuito di GitHub
  Pages (`giovmar-source.github.io/earthpulse`), valido per una beta non commerciale.
- **Per un prodotto commerciale: sì**, ed è consigliato.
  - `.it` si registra con OVH, Aruba o Register.it, a circa 5-15 € l'anno; richiede la
    residenza nel SEE.
  - Cloudflare Registrar non vende né `.it` né `.eu`. Il `.com` lì costa circa 10 $
    l'anno.

### 3.2 Passi per diventare pubblico "a tutti gli effetti"
1. **Nome.** Verificare che "EarthPulse" sia libero come marchio su TMview/EUIPO e UIBM
   (classi 9 e 42). Esistono già prodotti chiamati "Earth Pulse": da controllare
   (non verificato).
2. **Dominio** `.com` e `.it`.
3. **Hosting adatto all'uso commerciale.**
   - GitHub Pages **non** può ospitare un SaaS commerciale. Il frontend va spostato su
     Cloudflare Pages o Netlify, gratuiti o quasi.
   - Il backend non può restare sul piano gratuito di Render, che va bene solo per prove
     e non per produzione. Serve un piano a pagamento con più memoria.
4. **Pagine legali**: privacy (GDPR), banner cookie secondo le regole del Garante,
   termini di servizio, crediti dei dati, P.IVA in homepage se si vende.
5. **Monitoraggio e backup**: avvisi se il server cade, copie dei dati.

---

## 4. Monetizzazione

### 4.1 Si possono vendere servizi basati su questi dati?
Sì: i dati aperti si possono usare in un prodotto a pagamento. Si vende il servizio,
cioè elaborazione, interfaccia e affidabilità, non il dato in sé. Alcune fonti però
richiedono azioni prima del lancio.

| Fonte | Esito | Cosa fare |
|---|---|---|
| Sentinel-2 / Sentinel-5P (Copernicus) | ✅ Uso commerciale ammesso | Attribuzione "Contains modified Copernicus Sentinel data [anno]" |
| Earth Search (catalogo) | ✅ ma senza garanzie di servizio | Cache e catalogo di riserva (CDSE) |
| Landsat (USGS) | ✅ Nessuna restrizione | Credito facoltativo |
| Microsoft Planetary Computer | ⚠️ Termini non verificati, senza SLA | Leggere i termini; tenere un'alternativa |
| NASA Black Marble | ✅ | Citare il DOI; account Earthdata dedicato con rinnovo automatico del token |
| Open-Meteo (qualità dell'aria) | ❌ API gratuita solo non commerciale | Abbonamento (circa 29 $/mese, da verificare) oppure dati CAMS diretti |
| CAMS (Copernicus) | ✅ | Attribuzione |
| Sentinel Hub (CDSE, per Sentinel-5P) | ⚠️ Quota gratuita piccola | Piano CREODIAS "Basic" 999 €/anno, oppure elaborare noi i file Sentinel-5P |
| EUMETSAT (MTG FCI, Lightning Imager) | ⚠️ | Dati orari: gratuiti (CC BY 4.0). Immagini con meno di 1 ora di ritardo: licenza 4.000-8.000 €/anno. Soluzione: nella versione commerciale mostrare le immagini con almeno 1 ora di ritardo |
| H SAF (pioggia) | ✅ | Credito "copyright EUMETSAT" |
| OpenFreeMap | ✅ | Attribuzione; servizio senza garanzie |
| Nominatim / Photon (ricerca luoghi) | ❌ Non adatti a un prodotto a pagamento | Installare Photon sul nostro server o usare un servizio a pagamento |
| CelesTrak | ✅ Uso tecnico, con regole d'uso | Scaricare al massimo ogni 2 ore, dal server, con cache |
| Solar System Scope | ✅ CC BY 4.0 | Attribuzione |
| USGS Astrogeology, NASA Trek, JPL Horizons, SDO | ✅ Pubblico dominio | Credito |
| Immagini ESA (Licenza standard) | ❌ Non commerciale | Sostituire o chiedere il permesso (vedi 1.1) |

### 4.2 Modello "gratis limitato + Pro"
Si può fare. Il lavoro tecnico è stimato in 2-4 settimane:
- **Accesso con account**: Supabase o simili, con login email/Google e un database
  utenti gratuito all'inizio.
- **Pagamenti**: tramite un **Merchant of Record** (Paddle o Lemon Squeezy, circa
  5% + 0,50 $ a transazione). È lui a vendere al cliente e a gestire l'IVA di tutti i
  Paesi UE.
- **Limiti nel backend**: il server controlla il piano dell'utente prima di ogni
  elaborazione.

Sul tipo di limiti, un'opinione. Bloccare i dati recenti per il piano gratuito ("gratis
fino a 5 anni fa, Pro l'anno in corso") è lecito, ma rende la versione gratuita poco
utile: i dati recenti sono proprio quelli che attirano. Propongo di limitare la
**quantità** e le **funzioni professionali**:

| Gratis | Pro (mensile) | Istituzionale (università, PA) |
|---|---|---|
| Alcune analisi al giorno | Analisi illimitate (entro un uso ragionevole) | Licenza per tutto l'ente |
| Aree fino a 3 km | Aree più grandi, serie storiche complete | Più utenti, assistenza |
| Visualizzazione | Esportazione PDF/CSV/GeoTIFF, report da citare | Fattura elettronica alla PA |
| — | Luoghi salvati e **avvisi automatici** (es. "NDVI in forte calo nel tuo campo") | Accesso API |

### 4.3 Partita IVA e tasse (Italia, vendita in UE)
- **Serve la Partita IVA.** Un abbonamento è un'attività abituale, quindi la prestazione
  occasionale non vale. Si apre gratis con il modello AA9/12, più la ComUnica alla Camera
  di Commercio se è attività d'impresa.
- **Codice ATECO 2025** da scegliere con il commercialista: per esempio 58.29 (software)
  o 63.10 (elaborazione dati, cloud). Coefficiente di redditività 67%.
- **Regime forfettario.**
  - Ricavi fino a 85.000 €.
  - Imposta al **5% per i primi 5 anni** se l'attività è nuova, poi 15%.
  - Niente IVA in fattura.
- **Contributi INPS.** È la voce più pesante.
  - Se l'attività è inquadrata come commercio: minimo circa **4.600 € l'anno** anche con
    pochi incassi, riducibile del 35% per i forfettari.
  - Se è inquadrata come gestione separata: 26% sul reddito, senza minimo.
  - **La scelta va fatta con il commercialista.**
- **IVA verso clienti di altri Paesi UE.**
  - Con un Merchant of Record non ci si pensa: si emette una sola fattura al mese al MoR.
  - Vendendo direttamente: sotto 10.000 € l'anno di vendite a consumatori UE vale il
    regime italiano; sopra serve l'OSS.
- **Pubblica Amministrazione.** Fattura elettronica FatturaPA tramite SDI, ed
  eventualmente MEPA. Le università pagano di solito con fattura diretta, non con il MoR.
- **Consiglio pratico**:
  1. lanciare prima una beta gratuita, senza incassi e quindi senza P.IVA;
  2. aprire la P.IVA quando si attiva il Pro;
  3. affidarsi a un commercialista (circa 50-100 €/mese).

### 4.4 Costi mensili indicativi della versione commerciale
| Voce | Costo indicativo |
|---|---|
| Server backend (piano a pagamento) | 7-25 $/mese |
| Open-Meteo commerciale | circa 29 $/mese |
| Sentinel Hub Basic (o elaborazione propria) | circa 83 €/mese (999 €/anno) |
| Dominio | 1-2 €/mese |
| Commercialista | 50-100 €/mese |
| INPS (se gestione commercianti) | circa 385 €/mese (minimo) |
| Merchant of Record | 5% + 0,50 $ per pagamento |

---

## 5. Domande aperte
1. Gas dal satellite: vanno bene grafico nel tempo + confronto con l'anno prima (1.5)?
2. Piano Pro: quali limiti preferisci tra quelli proposti in 4.2?
3. Nome: teniamo "EarthPulse" (da verificare come marchio) o ne valutiamo un altro?

## Fonti principali
- Copernicus Sentinel, nota legale: https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice
- CDSE termini e quote: https://dataspace.copernicus.eu/terms-and-conditions · https://documentation.dataspace.copernicus.eu/Quotas.html · prezzi CREODIAS: https://creodias.eu/pricing/sh-pricing/
- Earth Search: https://github.com/Element84/earth-search · AWS: https://registry.opendata.aws/sentinel-2-l2a-cogs/
- Landsat: https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products
- NASA Earthdata: https://earthdata.nasa.gov/learn/articles/nasa-earth-science-data-yours-use-fully-and-without-restrictions
- Open-Meteo termini e prezzi: https://open-meteo.com/en/terms · https://open-meteo.com/en/pricing
- Licenza CAMS: https://cds.climate.copernicus.eu/licences/licence-to-use-copernicus-products
- EUMETSAT Data Policy: https://www-cdn.eumetsat.int/files/2026-01/45173%20-%20Data_Policy.pdf · H SAF: https://hsaf.meteoam.it/
- OpenFreeMap: https://openfreemap.org/tos/
- Nominatim: https://operations.osmfoundation.org/policies/nominatim/ · Photon: https://github.com/komoot/photon
- CelesTrak: https://celestrak.org/usage-policy.php
- Solar System Scope: https://www.solarsystemscope.com/textures/ · USGS: https://www.usgs.gov/information-policies-and-instructions/crediting-usgs
- NASA immagini: https://www.nasa.gov/nasa-brand-center/images-and-media/
- ESA: https://photolibrary.esa.int/terms-and-conditions/ · https://earth.esa.int/eogateway/faq/policy-for-the-use-of-esa-images · modulo: https://blogs.esa.int/forms/brand-licensing-contact-form/
- GitHub Pages limiti: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits · Render free: https://render.com/docs/free · Cloudflare Pages: https://developers.cloudflare.com/pages/platform/limits/ · Netlify: https://www.netlify.com/pricing/
- NASA GIBS: https://nasa-gibs.github.io/gibs-api-docs/access-basics/ · EOX: https://eox.at/2025/03/sentinel-2-cloudless-2024/ · Esri: https://location.arcgis.com/pricing/ · MapTiler: https://www.maptiler.com/cloud/pricing/
- Natural Earth: https://www.naturalearthdata.com
- NASA Trek: https://trek.nasa.gov/ · https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon
- JPL Horizons: https://ssd-api.jpl.nasa.gov/doc/horizons.html · ID NAIF: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/naif_ids.html
- NASA SDO: https://sdo.gsfc.nasa.gov/data/ · https://sdo.gsfc.nasa.gov/data/rules.php
- Fisco: https://fiscomania.com/regime-forfettario/ · https://fiscomania.com/regime-oss-e-regime-forfettario/ · https://www.studiomicera.it/vendere-saas-partita-iva-developer-2026/ · INPS 2026: https://www.tutelaprevidenziale.it/artigiani-e-commercianti-contributi-inps-2026-aliquote-minimali-scadenze-circolare-n-14-2026/ · ATECO: https://codiceateco2025.it/58.29
- Pagamenti: https://www.paddle.com/pricing · https://www.lemonsqueezy.com/pricing · https://stripe.com/it/pricing
- Cookie: https://www.garanteprivacy.it/temi/cookie · Marchi: https://www.tmdn.org/tmview
