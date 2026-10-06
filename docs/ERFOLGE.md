# Erfolge

Ein Erfolgssystem nach dem Vorbild von Xbox und Steam: Wer bei Filmabenden dabei ist, bewertet,
ins Gästebuch schreibt, Termine setzt, im Kino sendet oder schaut, schaltet Erfolge frei, sammelt
Punkte und steigt im Level auf. Code: `backend/app/erfolge.py` (Regeln und Katalog),
`backend/app/routers/erfolge.py` (API), `frontend/src/components/tabs/ErfolgeTab.vue`.

## Was es gibt

| Von | Übernommen |
|---|---|
| Xbox | Punkte pro Erfolg (Gamerscore), Stufen Bronze 10 · Silber 25 · Gold 50 · Platin 100, geheime Erfolge („???“ bis zum Freischalten), Pop-up beim Freischalten |
| Steam | Seltenheit („75 % der Gruppe“), Fortschrittsbalken (nur für einen selbst), Level aus Punkten mit Titeln, **Vitrine** mit bis zu drei Erfolgen auf dem Profil |

- **Keine Rangliste:** Die Gruppe sieht Level und Titel aller, alphabetisch; die eigene Punktzahl sieht nur man selbst.
- **Level** n braucht 12,5·n·(n−1) Punkte (Level 2 ab 25, 3 ab 75, 4 ab 150, 5 ab 250 …). Titel: Popcorn-Neuling, Filmfan (3), Cineast (5), Kritikerliebling (7), Regielegende (9), Hall of Fame (11).
- Das Level steht ab Level 2 als Abzeichen an jedem Avatar; Avatare in Teilnehmerlisten und Kommentaren führen zum Profil (`#/erfolge/person/<id>`).
- Freischaltungen erscheinen im Aktivitäts-Feed des Filmabends (die rückwirkenden beim Start nicht).

## Katalog

| Familie | Stufen (Ziel) | Zählt |
|---|---|---|
| 🛋️ Stammgast | 1 · 5 · 15 · 40 | bestätigte Filmabende, bei denen man dabei war (höchstens einer pro Tag) |
| 🏠 Gastgeber | 1 · 5 · 15 | gesetzte Termine, an denen (±1 Tag) ein bestätigter Abend stattfand |
| 🤞 Wort gehalten | 1 · 5 · 15 | Termine, für die man zugesagt hat und bei deren bestätigtem Abend (±1 Tag) man dabei war |
| 🗓️ Terminfinder | einmalig (Silber) | ein selbst vorgeschlagener Termin wurde in der Umfrage gewählt, und der Abend fand statt |
| 🎯 Treffsicher | 1 · 5 · 15 | eigene Vorschläge, die bei einem bestätigten Abend geschaut wurden |
| ✍️ Kritiker | 1 · 10 · 30 · 75 | bewertete bestätigte Abende |
| 📖 Gästebuch | 1 · 10 · 40 | Gästebuch-Einträge ab 20 Zeichen, einer pro Abend, höchstens drei pro Tag |
| ❤️ Herz | 3 · 6 · 10 | **verschiedene andere** Leute, die einen Eintrag von dir mit Herz markiert haben |
| 💡 Ideen | 1 · 3 · 10 | eigene Wünsche, die umgesetzt oder von drei **anderen** unterstützt wurden |
| 🎬 Kino-Regie | 1 · 5 · 15 | gesendete Vorstellungen, bei denen mindestens zwei andere je 5 Minuten zugeschaut haben |
| 🎟️ Kinogänger | 1 · 5 · 20 | Vorstellungen, die man mindestens 5 Minuten geschaut hat |
| Profil | einmalig | 📸 Profilbild, 🔐 Film-Passwort, 📺 Streamingdienste eingetragen |
| Geheim | einmalig | sieben Stück – siehe Code, hier nicht verraten |

## Gegen das Ausnutzen

1. **Punkte nur für Erfolge, nie pro Aktion.** Die Stufen begrenzen, was Wiederholung bringt.
2. **Gezählt wird der Ist-Zustand, und nur Verschiedenes.** Löschen und neu anlegen, eine Bewertung zehnmal ändern: bringt nichts.
3. **Liken und Abstimmen wird nie belohnt.** Es zählt nur, was man *von verschiedenen anderen* bekommt. Eigene Herzen und Stimmen zählen nie.
4. **Ein Filmabend zählt nur bestätigt:** mindestens zwei Teilnehmende, *eine andere Person, die dabei war,* hat ihn bewertet oder kommentiert, er liegt nicht in der Zukunft und wurde höchstens zwei Tage danach eingetragen (rückdatierte Einträge zählen nicht). Bewertungen, Gästebuch und Treffer zählen nur bei solchen Abenden.
5. **Was sich nicht aus den Daten lesen lässt, wird protokolliert** (Tabelle `ereignis`): wer einen Termin setzt, wer im Kino sendet und schaut, wessen Vorschlag geschaut wird.
6. **Erfolge sind dauerhaft** (wie bei Xbox/Steam). Admins können auf dem Profil einen Erfolg **entziehen**; er bleibt entzogen, bis ein Admin ihn zurückgibt.
7. **Rückwirkend:** Alles, was beim Einführen (`appmeta.erfolge_seit`, Migration 0005) schon existierte, zählt einmal so, wie es ist. Die erste Prüfung läuft beim Start; ihre Freischaltungen sind als `rueckwirkend` markiert und kommen als ein zusammenfassendes Pop-up statt als Flut.

Gegen zwei Freunde, die sich gegenseitig alles bestätigen, hilft keine Regel ganz – aber höchstens ein Abend pro Tag und die Stufen halten das langsam, und Admins können entziehen.

## Technisches

- Ausgewertet wird für alle auf einmal (`erfolge.stand`), höchstens alle 5 Sekunden (`pruefen`), dazu sofort bei `POST /api/erfolge/neu`. Das Frontend ruft das nach jedem erfolgreichen Schreibzugriff auf (gebündelt) und zeigt neue Freischaltungen als Pop-up.
- Neue Erfolge: Eintrag in `KATALOG`; neue Familien brauchen eine Zählung in `stand()` und einen Test in `tests/test_erfolge.py`.
