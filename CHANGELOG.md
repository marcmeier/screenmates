# Changelog

## 0.9.1 – 2026-10-06

### Geändert
- **Kino neu aufgeteilt:** Der Chat steht für alle – auch für den Gastgeber – rechts neben dem Bild,
  mit fester Höhe zum Scrollen. „Senden“ liegt jetzt breit unter dem Bild.
- **Kino-Chat bleibt 30 Tage:** Nachrichten werden gespeichert (vorher nur im Speicher, nach einem
  Neustart weg) und altern nach 30 Tagen raus. Ältere Nachrichten lassen sich nachladen,
  Tagestrenner zeigen, wann etwas geschrieben wurde. Reaktionen bleiben ein Moment im Bild.
- **Filmabend-Seite aufgeräumt:** Die Planung ist eine Zeile – Termin, wer dabei ist, deine
  Antwort, Einladen. Aufgeklappt wird sie von selbst nur, wenn etwas auf dich wartet (noch nicht
  geantwortet, Umfrage zum Abstimmen oder Festlegen); sonst über „Planung“. Am Tag selbst steht
  dort „Heute“.
- Wird nach einem vergangenen Abend ein neuer Termin gesetzt, beginnen die Zusagen von vorn
  (vorher stand „Dabei: …“ vom letzten Mal einfach weiter da).
- **Kiste für alle:** Der Übergang vom Countdown zum Drehen ist jetzt eine Bewegung. Das Band
  zieht schon während des Countdowns langsam an und beschleunigt weich, der Countdown blendet
  aus, statt hart zu verschwinden.

### Behoben
- Die Kiste ruckelte beim Drehen: Die Startzeit wurde bei jeder Live-Abfrage neu aus der
  Server-Uhr umgerechnet und schwankte mit dem Netz. Jetzt steht sie beim Öffnen fest, und der
  Uhrenabgleich nimmt die schnellste Messung.
- **Push-Nachrichten kamen nicht an.** Die Kontaktadresse für die Push-Dienste
  (`https://github.com/marcmeier/screenmates`) hatte einen Pfad, den die Signatur nicht erlaubt –
  jede Zustellung scheiterte. Jetzt geht nur der Ursprung raus (`https://github.com`), ebenso bei
  einer eigenen `PUSH_KONTAKT`-Adresse. Ein Test signiert und verschlüsselt jetzt echt.
- **„Test schicken“** wartet auf die Antwort des Push-Dienstes und meldet, ob die Nachricht wirklich
  zugestellt wurde (vorher hieß es „geschickt“, sobald sie in der Warteschlange lag).
- Findet der Browser seinen Push-Dienst nicht (Brave ohne Google-Push, Chromium-Builds ohne
  Google-Dienste), erklärt screenmates jetzt auf Deutsch, was zu tun ist, statt „Registration failed“.

### Betrieb
- Migration `0011`: Tabelle `kinonachricht` (Kino-Chat, 30 Tage).

## 0.9.0 – 2026-10-06

**Gemeinsam planen, gemeinsam erinnern:** Den Termin findet die Gruppe per Umfrage, jede Person
sagt zu, vielleicht oder ab, und der Abend landet im Kalender. screenmates meldet sich jetzt auch bei
geschlossener App, im Kino wird gequatscht und gekreischt, und am Ende des Jahres gibt es den
Rückblick. Das letzte Feature-Release vor 1.0.

### Neu
- **Terminumfrage.** Statt eines festen Termins schlägt man mehrere vor („Abstimmen“ beim Termin);
  alle antworten pro Termin mit Ja, Vielleicht oder Nein, der Favorit ist markiert. Wer festlegt,
  setzt den Termin, und die Antworten werden zu Rückmeldungen für den Abend. Festlegen darf, wer
  die Umfrage gestartet hat, der Gastgeber oder ein Admin – oder jeder, solange niemand den Stab hält.
  Vorschläge stehen im Aktivitäts-Feed.
- **Dabei, vielleicht, kann nicht.** Neben „Ich bin dabei!“ gibt es „Vielleicht“ und „Kann nicht“;
  wer wie geantwortet hat, steht unter den Dabei-Chips.
- **Kalender.** „Kalender“ beim Termin lädt den Abend als `.ics`-Datei (mit Ort, Filmen zur Wahl
  und Erinnerung zwei Stunden vorher). In den Einstellungen gibt es ein **Kalender-Abo** mit den
  nächsten Terminen aller eigenen Gruppen; verschiebt sich ein Termin, zieht der Kalender nach. Der
  Link ist persönlich und lässt sich erneuern oder abschalten.
- **Benachrichtigungen (Web Push)** aufs Handy und den Rechner, auch bei geschlossener App: neuer
  oder verschobener Termin, neue Terminumfrage, Erinnerung am Tag des Filmabends (drei Stunden
  vorher, nicht für wer abgesagt hat), die Kiste geht auf, das Kino ist live, der Gastgeber-Stab
  wird dir angeboten, jemand antwortet auf deinen Kommentar. Einschalten pro Gerät, auswählen pro
  Person, Testnachricht inklusive. Was gerade live passiert, bekommt nur, wer die App nicht offen
  hat. Auf iPhone und iPad in der App auf dem Home-Bildschirm.
- **Kino-Chat und Reaktionen.** Neben dem Bild ein Chat für alle, die gerade im Kino sind, und
  Reaktionen (😂 😱 ❤️ 👏 🍿 🔥 😴 🤯), die für alle übers Bild fliegen. Im Vollbild erscheinen neue
  Nachrichten direkt im Bild, Reaktionen gehen über die Steuerleiste.
- **Rückblick** unter „Unsere Filme“: das Filmjahr der Gruppe – Filme, Abende, Stunden, Genres,
  bester, umstrittenster und einstimmigster Film, Rekorde (Wochen am Stück, Lieblingstag) und
  Auszeichnungen wie „Stammgast“, „Strengste Kritik“ oder „Herzensbrecher“. Dazu eine **Story**
  zum Durchtippen. Im Dezember und Januar weist die Startseite darauf hin.
- **Neue Erfolge:** 🤞 „Wort gehalten“ (zugesagt und gekommen, drei Stufen), 🗓️ „Terminfinder“
  (dein Umfrage-Termin wurde gewählt und der Abend fand statt) und ein geheimer.
- Statistiken in der Seitenleiste zählen jetzt auch Kino-Chat-Nachrichten und Reaktionen.
- Neue Screenshots in der README.

### Behoben
- Im Changelog standen 0.7.0 und 0.8.0 mit dem falschen Datum.
- Zwei Erfolgs-Tests schlugen fehl, wenn sie nach Mitternacht liefen (die Test-Abende schalteten
  nebenbei „Nachteule“ frei).

### Betrieb
- Migration `0010`: Tabellen `terminvorschlag`, `terminstimme`, `pushabo`; `mitglied.rueckmeldung`,
  `user.kalender`, `user.push`, `abend.erinnert`, `appmeta.vapid`.
- Neue Abhängigkeit `pywebpush`. Die VAPID-Schlüssel erzeugt screenmates beim ersten Gebrauch und
  speichert sie in der Datenbank (Backup!). `PUSH_KONTAKT` ist optional. Push braucht HTTPS.
- Neu ohne Anmeldung erreichbar: `/api/kalender/<token>.ics` (der Token ist der Schlüssel).
- Ein Hintergrund-Task prüft jede Minute, ob eine Erinnerung fällig ist.
- Kino-Chat und Reaktionen liegen nur im Speicher (die letzten 200, höchstens 6 Stunden) und lösen
  kein Neuladen der anderen Apps aus.
- Ein Service Worker (`/sw.js`) zeigt die Benachrichtigungen; er speichert nichts zwischen.

## 0.8.0 – 2026-10-05

**Der Gastgeber-Stab:** Wer den Abend führt, ist jetzt eine Rolle, die wandert – weitergeben,
übernehmen, abstimmen. Damit kann auch ohne Admin jemand die Kiste für alle öffnen und das Kino
bespielen.

### Neu
- **Gastgeber-Stab.** Eine Person pro Gruppe hält ihn: Sie öffnet die Kiste für alle und bespielt
  das Kino (Bildschirm teilen, Programm, Vorstellung beenden, **persönlicher OBS-Schlüssel**, der
  nur mit dem Stab funktioniert). Admins der Gruppe können weiterhin alles.
  - Wer einen neuen Termin setzt, bekommt den Stab, wenn ihn gerade niemand hält oder der letzte
    Abend vorbei ist. Den Termin verschieben nimmt ihn niemandem weg.
  - **Weitergeben:** Der Gastgeber bietet den Stab jemandem an – annehmen oder ablehnen.
  - **Übernehmen:** Ist der Gastgeber nicht da (seit einer Minute keine App offen) oder gibt es
    keinen, nimmt man den Stab einfach. Ist er da, stimmen die Anwesenden 60 Sekunden lang ab:
    Die Stimme des Gastgebers zählt doppelt, sein Ja entscheidet sofort, mehr Ja als Nein gewinnt,
    ohne Widerspruch gilt Schweigen als Zustimmung. Steht das Ergebnis fest, endet die Abstimmung
    sofort. Wer verliert, wartet fünf Minuten.
  - Läuft beim Wechsel gerade eine Übertragung, läuft sie weiter; der neue Gastgeber kann sie
    beenden und selbst senden.
  - Angebote und Abstimmungen erscheinen überall in der App; Wechsel stehen im Aktivitäts-Feed.
- **Hinter den Kulissen:** Zwischen den Statistiken in der Seitenleiste blitzt auf, was gerade
  vorbereitet wird – „Popcorn wird vorbereitet …“, „Tauben werden von der Datenleitung
  verscheucht …“ und mehr.
- **Unterstützen per Ko-fi und PayPal.** Admins tragen auf der Über-Seite ihren Ko-fi- und
  PayPal.me-Namen ein (oder fügen einfach den Link ein). Jeder Weg bekommt einen Knopf und am
  Rechner einen QR-Code zum Scannen mit dem Handy – im Browser erzeugt, ohne fremden Dienst.
  Gespeichert wird nur der Name, verlinkt werden nur ko-fi.com und paypal.me.
- Neue Screenshots in der README.

### Behoben
- Auf der Profilseite stand die Überschrift „Erfolge“ doppelt.
- Statistik: „1 Gruppe“ statt „1 Gruppen“ (Einzahl für alle Zahlen).
- Die Schriftauswahl zeigt jede Schrift gleich in ihrer Schrift, nicht erst beim Drüberfahren.

### Betrieb
- Migration `0009`: `abend.gastgeber_id` (vorbelegt mit dem, der den Termin gesetzt hat),
  Tabelle `stabwechsel`, `user.obs_key`. Senden, Programm und Vorstellung beenden prüfen jetzt
  „Gastgeber oder Admin der Gruppe“.

## 0.7.0 – 2026-10-05

**Gemeinsam statt nebeneinander:** Der Gastgeber öffnet die Filmabend-Kiste und alle sehen live
zu, Änderungen von Freunden erscheinen ohne Neuladen, und reingekommen wird nur noch mit
Einladungslink. Dazu ein Profil mit Erfolgen und eigenem Farbschema, eine aufgeräumte Verwaltung
mit KI-Kosten, Statistiken in der Seitenleiste und eine Über-Seite mit Impressum.

### Neu
- **Die Kiste für alle öffnen.** Der Gastgeber des Abends (wer den Termin gesetzt hat) oder ein
  Admin der Gruppe öffnet die Filmabend-Kiste für alle: Wer screenmates gerade offen hat – egal
  auf welcher Seite –, bekommt nach einem kurzen Countdown dieselbe Öffnung zu sehen, mit
  demselben Band und demselben Gewinner, zur selben Zeit. Wer später kommt, steigt mittendrin
  ein. Der Gewinner bleibt als **„Film des Abends“** stehen, bis er geschaut ist (oder der
  Gastgeber ihn zurücknimmt), und steht im Aktivitäts-Feed. Den Gewinner zieht der Server.
  Alle anderen können weiter **probedrehen** – deutlich als Probe markiert, zählt nicht.
- **Live-Updates.** Bewertet, kommentiert, merkt oder schlägt jemand etwas vor, sehen die anderen
  es sofort – ohne die Seite neu zu laden. Im Hintergrund-Tab fragt screenmates seltener nach.
- **Kommentare mit Antworten bleiben als Platzhalter.** Wer einen Kommentar löscht, auf den schon
  jemand geantwortet hat, hinterlässt „Vom Ersteller gelöscht“ (bzw. „Von einem Admin entfernt“) –
  die Antworten bleiben im Zusammenhang. Ohne Antworten verschwindet er wie bisher; fällt die
  letzte Antwort weg, geht auch der leere Platzhalter.
- **Profil & Erfolge an einem Ort.** Der Profil-Knopf führt zu deinem Profil mit Level, Erfolgen
  und Vitrine; dort liegen auch deine Einstellungen. Alte Links (`#/erfolge`, `#/einstellungen`)
  funktionieren weiter.
- **Darstellung: Farbschema und Schrift.** Sieben dunkle Farbschemata (Kino, Nacht, Neon, Wald,
  Bernstein, Violett, Schwarz) und sieben Schriften, darunter eine besonders gut lesbare. Gilt
  nur für dich, auf allen deinen Geräten.
- **Verwaltung als eigener Bereich**, nur für Admins sichtbar: Gruppen und Einladungen, Anträge,
  Benutzer, Katalog – getrennt vom eigenen Profil.
- **KI-Nutzung in der Verwaltung:** Anfragen, Fehlschläge, Tokens und Kosten (OpenRouter meldet
  sie in US-Dollar) – heute, 7 und 30 Tage, gesamt, pro Person und die letzten Anfragen.
- **Statistiken in der Seitenleiste** statt der Katalog-Zahl: abwechselnd z. B. wie viele Filme
  gemeinsam geschaut, Herzen verteilt, Kisten geöffnet, wie viel im Kino gestreamt wurde und wie
  viele Pakete dabei verloren gingen. Nur Summen, nie etwas über einzelne Personen.
- **Über screenmates** mit Version, Quellcode-Link und den Abschnitten **Unterstützen**,
  **Impressum** und **Datenschutz**, die Admins direkt auf der Seite schreiben (Markdown). Die
  Seite ist auch ohne Einladung erreichbar; leere Abschnitte werden nicht gezeigt.
- **Einladungslinks statt Zugangsfrage.** Eine gemeinsame Filmfrage passt nicht, wenn auf einem
  Server mehrere Gruppen ohne gemeinsame Erinnerung sind. Jetzt gilt: nur mit Einladung. Admins
  einer Gruppe erzeugen Links für ihre Gruppe – „direkt aufnehmen“ oder „mit Freigabe“, mit Ablauf
  und Nutzungslimit, widerrufbar, zum Kopieren oder Teilen. Wer den Link öffnet, landet direkt
  bei der Namenswahl für diese Gruppe; wer schon einen Namen hat, tritt mit dem Link bei (oder
  fragt an). Anträge und Beitrittsanfragen entscheiden die Admins der Gruppe – kein Server-Admin
  nötig. Notausgang: `python -m app.cli einladung`.
- **Handy: Profil-Menü.** Der Profil-Knopf oben rechts öffnet ein Menü mit Profil & Erfolgen
  (samt Level), Einstellungen, Wünschen & Ideen, Verwaltung, Über und Abmelden – auf dem Handy
  waren Erfolge und Wünsche vorher gar nicht erreichbar.

### Behoben
- Die Kisten-Animation misst die Breite jetzt in jedem Bild – vorher konnte die Markierung neben
  dem Gewinner landen, wenn die Bühne beim Start noch nicht fertig aufgebaut war.

### Entfernt
- Die Zugangsfrage (ersetzt durch Einladungen). Wer drin ist, bleibt drin.

### Betrieb
- Migration `0007`: Tabellen `einladung`, `beitrittsanfrage`; `session.einladung_id`,
  `user.antrag_gruppe_id`; Tabelle `zugang` entfällt. Danach in Verwaltung → Gruppen
  Einladungslinks erzeugen und verschicken.
- Migration `0008`: Tabellen `kistenoeffnung`, `kianfrage`, `zaehler`, `seitentext`;
  `watchednote.geloescht`, `user.design`.
- Live-Updates: jede offene App fragt alle 1,5 s `GET /api/live` (im Hintergrund alle 15 s) –
  eine kleine Antwort, kein WebSocket nötig, läuft durch jeden Proxy.
- Mit Kino zählt ein Hintergrund-Task alle 15 s Traffic und verlorene Pakete der
  MediaMTX-Sitzungen mit (`/v3/webrtcsessions/list`). Was vor dem Update lief, ist nicht erfasst.
- Impressum und Datenschutz in Über → Bearbeiten eintragen, falls nötig.

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
