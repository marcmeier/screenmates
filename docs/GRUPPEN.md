# Gruppen

Ein screenmates-Server kann mehrere unabhängige Freundeskreise tragen. Beispiel: Gruppe 1 mit
sechs Leuten, Gruppe 2 mit vier – manche in beiden, manche nur in einer.

| Gilt für … | Was |
|---|---|
| den ganzen Server | Zugangsfrage, Namen und Anträge, Admins, Profilbilder, Film-Passwörter, Streaming-Abos, Level und **Erfolge**, Wünsche & Ideen, Filmkatalog, KI-Suche |
| eine Gruppe | Filmabend (wer dabei ist, Vorschläge, Veto, Kiste, Termin, Infos), Chronik mit Bewertungen und Gästebuch, Merkliste, Aktivitäts-Feed, „Heute vor einem Jahr“, **Kino** |

- **Nur Mitglieder** sehen die Inhalte einer Gruppe – auch über die API (`401`/`409`/`404`).
- **Aktive Gruppe:** pro Browser-Sitzung (`session.gruppe_id`), Wechsel über die Auswahl in der Seitenleiste. Ohne gewählte Gruppe gilt die mit der kleinsten ID.
- **Rollen:** Server-Admins legen Gruppen an, benennen um, löschen und ernennen Gruppen-Admins. Gruppen-Admins nehmen in *ihrer* Gruppe Leute auf, entfernen sie, benennen um und haben dort die Filmabend-Rechte (Vorschläge leeren, Teilnahme zurücksetzen, Infos, Gesehen-Einträge, Kommentare löschen, Kino senden). Server-Admins haben diese Rechte in Gruppen, in denen sie Mitglied sind.
- **Neue Namen:** Gibt es nur eine Gruppe, landen freigegebene Namen automatisch darin. Bei mehreren entscheidet ein Admin (Einstellungen → Gruppen; „Noch in keiner Gruppe“ listet, wer fehlt).
- **Kino:** eins pro Gruppe, MediaMTX-Pfad `kino-<Gruppen-ID>` (Regex-Pfad in `deploy/mediamtx.yml`), eigenes Geheimnis, eigener OBS-Stream-Key (der Key bestimmt die Gruppe, die WHIP-URL ist für alle gleich), eigenes Publikum. Mehrere Gruppen können gleichzeitig senden – Upload-Bandbreite beachten.
- **Erfolge** zählen über alle Gruppen: Ein bestätigter Filmabend ist einer, egal in welcher Gruppe (höchstens einer pro Tag).
- **Technik:** `watched`, `wishlist`, `suggestion`, `veto` haben eine `gruppe_id`; ihre Eindeutigkeit gilt pro Gruppe. `abend`, `info` und `kinostate` verwenden die Gruppen-ID als ID. Migration `0006` legt „Unsere Gruppe“ (ID 1) mit allen bisherigen Daten und freigegebenen Namen an; wer Admin war, ist dort Gruppen-Admin.
