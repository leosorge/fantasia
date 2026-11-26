# FANTASIA

## Canali YouTube seguiti

Modifica [youtube-canali.txt](youtube-canali.txt) per aggiungere o togliere un canale. Incolla un URL di canale o scrivi un `@handle` per riga. Le righe vuote e quelle con `#` iniziale sono ignorate.

Ogni ciclo controlla i nuovi caricamenti dei canali seguiti, anche se il titolo o la descrizione non contengono parole di `Qlist.txt`. Questi video hanno precedenza sui risultati della ricerca per argomento. Restano validi i filtri di data e durata e il limite di tre segnalazioni accodate per ciclo. Da CLI puoi usare una lista alternativa con `--watch-channels percorso.txt`.

Il feed legge i testi in ordine di creazione, li adatta a sei formati interattivi o editoriali e mostra gli ultimi 12 in un'unica pagina a scorrimento. Su desktop, se c'è spazio, la griglia è di tre colonne per quattro righe, con schede da 480 × 600 px. Su schermi stretti la griglia si adatta a due colonne o una. I file effettivi su Drive si chiamano **news** e **olds**. La pipeline usa per impostazione predefinita i loro ID. Le variabili `FANTASIA_NEW_ID` e `FANTASIA_OLD_ID` li possono sostituire.

| Codice | Esperto |
| --- | --- |
| 1 | News, con titolo, estratto e link alla fonte quando presente |
| 2 | Quiz multiple choice, con frasi a completamento ricavate dal testo |
| 3 | Carousel, con i sistemi visivi originali di Carousel Builder v2.14.3 e il profilo Neroverde. Il selettore cambia tra Editoriale, Geometrico e Frame. Per il testo restano disponibili Narrativo, A sezioni e Verbatim |

Il feed riusa il CSS originale delle anteprime di Carousel Builder. La scheda HTML ha comandi propri per scorrere le slide e non avvia l’editor completo di Carousel Builder.
| 4 | Game-PIP, Qwat World con tre piani e tre bivi numerici AB, BC e ABC |
| 5 | 3D. Sorteggia Processore, Reticolo o Satellite. Estratto scorrevole di massimo 300 parole e link alla fonte separato |
| 6 | Quote Card. Sorteggia American Comics, Prism o Beatles · Son of Flowers |

`expert_choice.py` riconosce indizi editoriali e sceglie il formato. Accetta anche le intestazioni facoltative `Titolo:`, `Fonte:`, `Formato:` all'inizio di un file di testo. I codici `5` e `6` sorteggiano una delle tre varianti una sola volta alla creazione. Per scegliere direttamente una variante, usa `5.1`–`5.3` o `6.1`–`6.3`. Senza un formato esplicito o un indizio prioritario, il router ripartisce le notizie tra i formati compatibili usando una scelta stabile derivata dal contenuto. Le segnalazioni YouTube con soli dati di pubblicazione ricadono in News. La Quote Card può usare la frase-sintesi o un estratto del testo. Il Quiz usa termini del testo. Per Game-PIP servono tre frasi brevi, ciascuna con un singolo numero o una percentuale. Il gioco mostra ogni frase con il valore da completare e genera distrattori numerici. I file illeggibili o incompatibili restano in coda.

Game-PIP usa i percorsi A sotto, B in superficie e C sopra. Ai tre bivi si sceglie toccando i cartelli, con i pulsanti o con A, B e C. Durante la corsa, tocca il percorso o premi Spazio per saltare e raccogliere le monete.

## GitHub Pages e Drive

1. Metti i file del progetto nella radice del repository dedicato a FANTASIA, inclusa `.github/workflows/fantasia.yml`. Imposta **Settings → Pages → Source → GitHub Actions**. La branch predefinita deve consentire i commit del workflow.
2. Configura il secret GitHub `FANTASIA_DRIVE_CREDENTIALS` con il JSON delle credenziali Drive. Per queste cartelle in Drive personale usa credenziali OAuth utente con refresh token, ottenute con un client abilitato a Drive API e allo scope `https://www.googleapis.com/auth/drive`. Per un Drive condiviso si può usare un service account con permessi di scrittura e cestinamento e impostare `FANTASIA_SHARED_DRIVE_ID`. I service account non hanno spazio di archiviazione proprio.
3. Esegui manualmente il workflow **FANTASIA** per il primo deploy. Il workflow è programmato anche alle 00:15, 06:15, 12:15 e 18:15 UTC. File inseriti a mano e file generati dallo script esistente seguono la stessa coda.
4. Per usare il produttore, imposta `FANTASIA_PRODUCER=intersearQ` e il secret `YOUTUBE_API_KEY`. Accoda fino a tre segnalazioni per ciclo. Rileva la lingua e traduce titolo e descrizione in italiano sul runner con M2M100. Il primo ciclo può richiedere più tempo per scaricare il modello. Il produttore scrive in Drive un file Fantasia News v1 con le sezioni TITOLO, FONTE, SOMMARIO, TESTO, CAROUSEL, QUIZ, GIOCO, 3D e FRASE-SINTESI. Il router sorteggia tra i formati con sezioni valide. GIOCO resta incompleta se la descrizione non contiene tre fatti numerici utilizzabili. `--channels canali.txt` limita i canali per l'esecuzione da CLI.

Il feed su Pages contiene il materiale elaborato. Usa la cartella d'ingresso per testi destinati alla pubblicazione. Il router elabora tutti i file validi del ciclo e costruisce una sola pagina con le 12 schede più recenti. Ogni scheda che esce dalla pagina va in `olds` con un nome come `Prime_tre_parole_251126.html`. La data è quella della prima pubblicazione in ora italiana. Le schede eccedenti prodotte e archiviate nello stesso ciclo prendono la data del ciclo. Stato e pagina vengono registrati insieme. Dopo il deploy riuscito il workflow salva le date di pubblicazione e sposta nel Cestino i sorgenti già elaborati, purché non siano stati modificati nel frattempo. Le ricevute identificano i contenuti anche quando cambia soltanto la versione dei metadati Drive.

## Verifica locale

```sh
python -m unittest -v
python main.py check-drive
```

La cartella `demo/` del pacchetto contiene un esempio generato da 14 testi. Apri `demo/docs/index.html` e scorri la griglia. Carousel, Game-PIP e American Comics sono le prime tre schede. I due HTML espulsi sono in `demo/old/`. Con `python main.py demo --root demo` puoi rielaborare la coda locale dopo aver aggiunto nuovi file a `demo/new/`.
