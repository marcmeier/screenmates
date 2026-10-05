# Changelog

## Unveröffentlicht

### Neu
- **Einladungslinks statt Zugangsfrage.** Eine gemeinsame Filmfrage passt nicht, wenn auf einem
  Server mehrere Gruppen ohne gemeinsame Erinnerung sind. Jetzt gilt: nur mit Einladung. Admins
  einer Gruppe erzeugen Links für ihre Gruppe – „direkt aufnehmen“ oder „mit Freigabe“, mit Ablauf
  und Nutzungslimit, widerrufbar, zum Kopieren oder Teilen. Wer den Link öffnet, landet direkt
  bei der Namenswahl für diese Gruppe; wer schon einen Namen hat, tritt mit dem Link bei (oder
  fragt an). Anträge und Beitrittsanfragen entscheiden die Admins der Gruppe – kein Server-Admin
  nötig. Notausgang: `python -m app.cli einladung`.
- **Handy: Profil-Menü.** Der Profil-Knopf oben rechts öffnet ein Menü mit Erfolgen (samt Level),
  Wünschen & Ideen, Einstellungen und Abmelden – auf dem Handy waren Erfolge und Wünsche vorher
  gar nicht erreichbar.

### Entfernt
- Die Zugangsfrage (ersetzt durch Einladungen). Wer drin ist, bleibt drin.

### Betrieb
- Migration `0007`: Tabellen `einladung`, `beitrittsanfrage`; `session.einladung_id`,
  `user.antrag_gruppe_id`; Tabelle `zugang` entfällt. Danach in Einstellungen → Gruppen
  Einladungslinks erzeugen und verschicken.

## 0.6.0 – 2026-10-05

**Für eure Gruppe – oder mehrere:** screenmates lässt sich hinter eine Zugangsfrage legen, neue
Leute beantragen ihren Namen, Admins verwalten Profile, und ein Server trägt mehrere unabhängige
Freundeskreise mit eigenem Filmabend und eigenem Kino. Dazu Erfolge mit Levels und Vitrine,
Profilbilder, alle Genres statt nur Horror und eine KI-Suche, die mit OpenRouter günstig läuft.

### Neu
- **Gruppen: mehrere unabhängige Freundeskreise auf einem Server.** Jede Gruppe hat ihren eigenen
  Filmabend (wer dabei ist, Vorschläge, Veto, Kiste, Termin, Infos), ihre Chronik mit Bewertungen
  und Gästebuch, ihre Merkliste, ihren Aktivitäts-Feed und **ihr eigenes Kino** – mehrere Gruppen
  können gleichzeitig senden. Sichtbar ist das nur für Mitglieder. Namen, Admins, Profilbilder,
  Level und Erfolge gelten weiter für den ganzen Server. Server-Admins legen Gruppen an und
  ernennen Gruppen-Admins; die nehmen Leute auf und machen am Filmabend, was bisher Admins
  vorbehalten war. Wer in mehreren Gruppen ist, wechselt in der Seitenleiste. Mit nur einer
  Gruppe landen freigegebene Namen automatisch darin. Alles Bisherige steht in „Unsere Gruppe“.
- **Erfolge** nach dem Vorbild von Xbox und Steam: 32 Erfolge in Bronze, Silber, Gold und
  Platin für Filmabende, Kritiken, Gästebuch, Termine, Kino und Profil, dazu sechs geheime.
  Punkte ergeben ein Level mit Titel, das als Abzeichen an jedem Avatar steht. Neue Erfolge
  erscheinen als Pop-up und im Aktivitäts-Feed; jede Person hat ein Profil mit Vitrine für bis
  zu drei Erfolge. Seltenheit und Fortschritt wie bei Steam, aber keine Rangliste.
  **Ausnutzen lohnt sich nicht:** Punkte gibt es nur für Erfolge, Liken und Abstimmen wird nie
  belohnt (nur Herzen *von verschiedenen anderen*), ein Filmabend zählt erst, wenn ihn eine andere
  Person, die dabei war, bestätigt, rückdatierte Einträge zählen nicht. Was es vor dem Start schon
  gab, zählt rückwirkend. Alle Regeln: [`docs/ERFOLGE.md`](docs/ERFOLGE.md).
- **Profilbilder.** In den Einstellungen lädt man ein eigenes Bild hoch; es ersetzt überall die
  Initialen. Der Browser verkleinert Handyfotos vor dem Hochladen, der Server schneidet sie
  quadratisch zu (256 px, WebP) und kodiert sie neu – Ortsangaben und andere Metadaten der Fotos
  bleiben dabei nicht erhalten. Admins können Bilder anderer entfernen.
- **Zugangsfrage: screenmates nur für eure Gruppe.** Admins legen eine Frage fest, z. B. „Welchen
  Film haben wir zuerst zusammen geschaut?“. Wer die App öffnet, muss erst den richtigen Film
  anklicken – vorher ist nichts zu sehen, auch nicht über die API. Fehlversuche werden pro IP
  gedrosselt. Wer schon angemeldet ist, merkt davon nichts.
- **Namen beantragen, Admins geben frei.** Neue Leute stellen hinter der Zugangsfrage einen Antrag;
  Admins sehen offene Anträge als Zahl in der Navigation und geben frei oder lehnen ab.
- **Admins statt Host-Film.** Admin ist jetzt ein Recht einer Person, nicht mehr ein geteilter
  Film, den jeder kennen kann. Admins ernennen weitere Admins; den letzten kann man weder
  löschen noch herabstufen. Der erste Name einer neuen Installation wird Admin, bestehende
  Installationen bekommen ihren ersten Admin mit `python -m app.cli admin "<Name>"`.
- **Benutzerverwaltung** in den Einstellungen: umbenennen, Farbe ändern, Admin-Recht vergeben
  oder entziehen, Film-Passwort zurücksetzen, auf allen Geräten abmelden, löschen – mit Anzeige,
  auf wie vielen Geräten jemand angemeldet ist.
- **Favicon** im Stil der eingeklappten Leiste („sm“), dazu Icons für den Homescreen von iPhone
  und Android (`apple-touch-icon`, Web-Manifest).
- **KI-Suche über OpenRouter.** Statt eines Anthropic-Keys geht auch ein OpenRouter-Key (`sk-or-…`,
  wird automatisch erkannt) – und damit jedes Modell dort. Standard ist das günstige
  `deepseek/deepseek-v4.1-flash` (rund 0,12 Cent pro Suche); jeder Vorschlag wird ohnehin gegen TMDB geprüft.
  Das „Nachdenken“ (Reasoning) wird dabei abgeschaltet: Bei Reasoning-Modellen verbrauchte es das
  ganze Antwort-Budget, bevor die Liste kam – ohne ist die Suche schneller, billiger und zuverlässig.
  Fehler der KI werden verständlich gemeldet (Key abgelehnt, Guthaben leer, überlastet, abgeschnitten).
- **Alle Genres statt nur Horror.** Finden, Stöbern, Suche, Personen und KI-Suche umfassen jetzt
  jeden Film. Horror ist ein Genre unter vielen und hat sein eigenes Regal – ganz vorn.
- **Genre-Regale** beim Stöbern: Horror, Komödie, Thriller, Action, Science-Fiction, Drama,
  Animation, Dokumentarfilm. Die Dienst-Regale zeigen das ganze Angebot.
- **Filmografien** zeigen alle Filme einer Person, auf Wunsch nach Genre gefiltert.
- Gezeigt werden nur Filme, die schon erschienen sind. Bei großen Mengen steht „Mehr als 10.000
  Filme", denn mehr liefert TMDB nicht.
- „Geheimtipps" an echten Daten neu eingestellt: über alle Genres hinweg verdrängten Filme mit
  kleiner, begeisterter Fan-Basis alles andere. Jetzt mindestens zwei Jahre alt und in verbreiteten
  Originalsprachen (u. a. *Harakiri*, *Die sieben Samurai*, *Cinema Paradiso*).

### Entfernt
- Host-Modus mit Host-Film und `Strg+Shift+H` (ersetzt durch Admins).

### Behoben
- **Filme aus dem Start-Katalog bekamen nie ein Poster** (u. a. Scream, Hereditary, Shining,
  Midsommar): Die Detailansicht vervollständigte nur Filme ohne Laufzeit, der Start-Katalog hat
  aber eine. Jetzt holt sie mit TMDB-Key auch fehlende Poster einmal nach.
- **Die Seitenleiste springt beim Ein- und Ausklappen nicht mehr:** Logo, Gruppe, Navigation und
  Profil behalten ihre Höhe; eingeklappt zeigt die Gruppe ihr Kürzel.
- **Das Kino-Bild hat eine feste Größe:** höchstens 1280 px breit und immer so groß, dass es samt
  Titelzeile ins Fenster passt – auf großen Monitoren musste man vorher scrollen. Auf dem Handy
  volle Breite, im Vollbild wie gehabt bildschirmfüllend.
- **Mit TMDB endeten Raster und Suche nach 20 Filmen**, obwohl es z. B. 320 Horrorfilme bei
  Netflix gibt: TMDB liefert 20 Filme pro Seite, die App fragte 24 an und hielt „weniger als
  gefragt" für das Ende. Jetzt meldet der Server, ob es weitergeht und wie viele es insgesamt sind.

### Verbessert
- Raster laden beim Scrollen von selbst nach („Mehr laden" bleibt als Knopf), und „Alle Filme"
  zeigt die Gesamtzahl („320 Filme").

### Betrieb
- **Sechs Migrationen** (`0003`–`0006`) laufen beim Start automatisch: Zugangsfrage und Admins pro
  Person, Profilbilder, Erfolge, Gruppen. Alles Bisherige landet in „Unsere Gruppe“; wer vorher
  angemeldet war, bleibt es.
- **Erster Admin** einer bestehenden Installation: `python -m app.cli admin "<Name>"` (im
  Container). `python -m app.cli namen` listet alle Namen, `zugang-aus` hebt die Zugangsfrage auf.
- **Hinter einem Reverse Proxy** `FORWARDED_ALLOW_IPS` setzen (Proxy-IP, ggf. Cloudflare-Netze),
  damit die Drossel der Zugangsfrage die echte Client-IP sieht.
- **Profilbilder** liegen unter `MEDIA_DIR` (Docker: `/data/media`, im selben Volume wie die
  Datenbank – beim Backup mitnehmen). Neue Abhängigkeit: Pillow.
- **MediaMTX:** ein Pfad pro Gruppe (`kino-<id>`, Regex in `deploy/mediamtx.yml`) – den
  Medienserver nach dem Update mit der neuen Konfiguration neu starten.

### Tests
- 183 Backend-Tests, 40 Browser-Tests (auch gegen den Docker-Stack). Neu u. a.: alle
  Schutzregeln der Erfolge gegen Ausnutzen, Zugangsfrage samt Drossel, Rechte pro Person und
  Gruppe, Profilbild-Verarbeitung (EXIF/GPS weg, Bomben-Schutz), Kino pro Gruppe, Migrationen
  ab einem echten Ausgangsstand.
- Die Einladungskarte bekommt im Browser-Test 15 statt 5 Sekunden zum Zeichnen (gelegentlicher
  Zeit-Ausreißer auf ausgelasteten Rechnern).

## 0.5.0 – 2026-10-03

**Stöbern, losen, einladen:** „Finden" zeigt das Horror-Angebot von Netflix, Prime & Co. in
Regalen, die Filmabend-Kiste ersetzt das Glücksrad, und der Abend bekommt Termin, Einladungskarte
und Erinnerungen. Dazu schätzt screenmates, wem ein Film gefallen wird – ehrlich gemessen.

### Neu
- **Stöbern statt Suchen-müssen:** „Finden" startet mit Regalen wie bei einem Streamingdienst:
  „Läuft bei uns" (eure Abos), je ein Regal pro Dienst (Netflix, Prime Video, Disney+, Paramount+,
  Joyn, WOW … eure eigenen zuerst, mit „Euer Abo"), „Kostenlos streamen", „Neu erschienen",
  „Geheimtipps" und „Klassiker". Seitwärts wischen oder blättern, „Alle zeigen" öffnet das ganze
  Angebot im Raster.
- **„Alle Filme" mit Dienst-Auswahl:** Logos zum Filtern nach einem Dienst, dazu „Kostenlos" und
  „Läuft bei uns". Die gewählte Ansicht wird gemerkt.
- **Filmabend-Kiste statt Glücksrad**, wie das Öffnen einer Kiste in Counter-Strike 2: Ein Band aus
  Postern rast unter der Markierung durch, bremst lange ab und enthüllt den Film des Abends. Die
  **Seltenheitsfarben** (Standard, Limitiert, Geheim, Verdeckt, ★ Legendär) zeigen die echten
  Chancen, der Kisteninhalt listet sie in Prozent. Mit Klick-Geräuschen und Fanfare (abschaltbar),
  Beinahe-Treffern, „Überspringen" (auch Escape) und kurzer Animation bei „weniger Bewegung".
- **„Wem gefällt's?"** in jeder Filmansicht: geschätzte Sterne pro Person aus ihren eigenen
  Bewertungen, mit Begründung („wie Freitag der 13., ★ 5"). Ab 8 Bewertungen, bis 25 als „erste
  Tendenz". Im Rückblick-Test bis zu 20 % genauer als der Durchschnitt der Person. Was die
  Prognose kann und was nicht, steht in `docs/PROGNOSE.md`.
- **Termin und Einladung:** Datum und Ort für den nächsten Abend. „Einladen" erzeugt eine Karte
  als Bild (Termin, Poster der Vorschläge ohne Veto, wer dabei ist) und einen Text mit Link. Auf
  dem Handy geht beides direkt ins Teilen-Menü, sonst Bild speichern und Text kopieren.
- **„Heute vor einem Jahr":** Auf dem Filmabend erscheint, was ihr um dieses Datum in früheren
  Jahren geschaut habt, mit euren Sternen und dem beliebtesten Kommentar.

### Betrieb
- Erste echte Migration (`0002`): Tabelle `abend` und Spalte `movie.keywords`. Fehlende Stichworte
  älterer Filme holt die Prognose nach und nach aus TMDB (höchstens 30 pro Anfrage).
- `scripts/prognose-backtest.py` misst die Prognose an echten TMDB-Filmen.

### Tests
- 110 Backend-Tests, 34 Browser-Tests (auch gegen den Docker-Stack und in UTC). Neue Prüfungen
  jeweils mit absichtlich eingebauten Fehlern gegengecheckt; Regale und Prognose zusätzlich mit
  echten TMDB-Daten, die Migration an einer Kopie einer echten Datenbank.

## 0.4.0 – 2026-10-03

Der **Filmabend wird persönlicher**: Wo läuft der Film, wer hat welches Abo, wie fand ihn wer –
und wer ihn auf keinen Fall sehen will. Dazu eine Datenbank, die künftige Updates ohne
Datenverlust mitmacht.

### Neu
- **Seitenleiste einklappbar**: nur Icons (mit Tooltips, Kurzlogo „sm“, Live-Zähler am Kino-Icon),
  pro Gerät gemerkt. Auf dem Handy unverändert.
- **Bewerten und Kommentieren direkt in der Detailansicht** jedes gesehenen Films – nicht mehr
  nur unter Unsere Filme → Gesehen. Dazu der Gruppen-Schnitt „Ihr: ★ 4,7“ neben der TMDB-Wertung.
- **„Wo läuft's?“** in jeder Filmansicht: Abo, kostenlos, leihen, kaufen in Deutschland (Daten:
  JustWatch über TMDB). Abos, die jemand aus der Gruppe hat, stehen vorn – mit Namen.
- **Meine Abos** in den Einstellungen (nur echte Abo-Dienste, keine Leih-Shops) und der Filter
  **„Läuft bei uns“** in Finden. „Prime Video mit Werbung“ zählt als Prime Video.
- **Trailer** in der Detailansicht, deutsch bevorzugt; YouTube (nocookie) lädt erst beim Klick.
- **Veto**: Jede Person kann einen vorgeschlagenen Film ablehnen; das Glücksrad lässt ihn aus.
  Vetos verfallen, wenn der Film geschaut oder die Vorschläge geleert werden.

### Betrieb
- **Datenbank-Migrationen mit Alembic.** Die App bringt die Datenbank beim Start selbst auf den
  neuesten Stand. Datenbanken aus 0.2/0.3 werden ohne Datenverlust übernommen (fehlende Tabellen
  werden ergänzt). Künftige Schema-Änderungen: `make migration name="…"`. Ein Test schlägt fehl,
  wenn ein Modell geändert, aber keine Migration geschrieben wurde. Migrationen laufen mit
  ausgeschalteten Fremdschlüsseln, damit ein Tabellen-Umbau unter SQLite keine Kaskaden auslöst.

### Behoben
- Bewertungen und Kommentare aus einer Ansicht erschienen in anderen offenen Ansichten erst nach
  dem Neuladen.
- Escape schloss ein Fenster nicht mehr, wenn nach einer Aktion der Fokus aus dem Fenster fiel.
- Bewertungen überall mit deutschem Komma (4,7 statt 4.7).

### Tests
- 92 Backend-Tests, 28 Browser-Tests (auch gegen den kompletten Docker-Stack). Anbieter und
  Trailer zusätzlich mit echten TMDB-Daten, die Migration an einer Kopie einer echten Datenbank
  geprüft.

## 0.3.0 – 2026-10-03

Das **Kino**: gemeinsam live schauen, auch wenn alle an verschiedenen Orten sitzen.

### Neu
- **Kino** als eigener Bereich: Der Host teilt einen Browser-Tab (oder sendet per WHIP aus
  OBS), alle sehen live dasselbe Bild über WebRTC. Medienserver MediaMTX verteilt; screenmates
  prüft Rechte und leitet nur die Verbindungsaushandlung weiter.
- Menüpunkt „Kino“ mit Live-Anzeige und Zahl der Zuschauenden, Banner „Jetzt im Kino“ auf dem
  Filmabend, Film nach der Vorstellung mit allen Zuschauenden als gesehen eintragen.
- Sende-Pult mit **Qualität** (Hoch 1080p / Mittel 720p / Sparsam 480p) und **Inhalt**
  (Film / Spiel bis 60 fps) sowie Live-Anzeige der tatsächlichen Sendewerte.
- **Navigation in drei Bereiche** statt zehn Punkte: Filmabend · Finden · Unsere Filme
  (plus Kino). Ein Suchfeld für Entdecken, Titel, Personen und KI. Alte Links werden umgeleitet.
- Schrift Inter, mit dem eigenen Build ausgeliefert.

### Verbessert (alles gemessen, Details in `docs/KINO-QUALITAET.md`)
- **Bild:** 1080p ab der ersten Sekunde statt 480×270 in den ersten ~15 s – Auflösung halten,
  Startbitrate, H.264 statt VP8.
- **Ton:** Stereo mit bis zu 192 kbit/s statt Mono mit ~32 kbit/s (Sender *und* Zuschauer
  fordern Stereo an, sonst mischt Chrome herunter).
- **Gleichmäßigkeit:** 300 ms Wiedergabepuffer beim Zuschauer – größte Abweichung vom
  Aufnahmetakt 65 → 24 ms.
- Personensuche: Leute mit Horror-Bezug zuerst; Filmografien ohne Doku-Auftritte, bekannteste
  Filme zuerst, Rollen auf Deutsch.
- Entdecken und TMDB-Abgleich: nur Spielfilme ab 60 min, „Beste Bewertung“ erst ab 200 Stimmen.

### Behoben
- Sender wie OBS/FFmpeg brachen zufällig ab, wenn MediaMTX einen ICE-TCP-Kandidaten zuerst
  nannte – sie bekommen jetzt nur UDP-Kandidaten.
- Glücksrad-Beschriftungen standen teils auf dem Kopf.

### Betrieb & Tests
- `make kino-install`, MediaMTX in `compose.yaml`; neue Tabelle, bestehende Datenbanken bleiben gültig.
- CI-Job, der den kompletten `docker compose`-Stack startet und alle E2E-Tests dagegen fährt.
- 69 Backend-Tests, 23 Browser-Tests – darunter Kino mit echtem Medienserver, OBS-Ersatz per
  FFmpeg, TCP-Ausweichweg bei gesperrtem UDP und Stereo per Frequenzanalyse.

### Noch nicht im echten Einsatz geprüft
- Zuschauen über das Internet (Checkliste: `docs/KINO-CHECK.md`).
- Echtes OBS als Sender.

## 0.2.0 – 2026-10-03

Senior-Review des ersten Stands; Befunde und Behebungen in `docs/REVIEW.md`.

- Rechte-Modell (Name zum Schreiben, Host zum Verwalten), Schutz- und Host-Film werden nie
  ausgeliefert, Drosselung beim Raten.
- Schema mit Kaskaden und Unique-Constraints, Schema-Version, Validierung überall.
- TMDB-Ergebnisse mit Postern, robuster Client; KI-Suche über die Anthropic API.
- Neues Frontend mit allen Bereichen, Fehlermeldungen, Tastaturbedienung, mobile Ansicht.
- Tests, Lint, CI, Docker.

## 0.1.0 – 2026-10-03

Erster lauffähiger Nachbau (MVP): Katalog, Suche, Merkliste, Gesehen, Wünsche, Info, Namenswahl.
