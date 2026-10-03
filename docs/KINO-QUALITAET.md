# Kino – warum diese Sende-Einstellungen

Gemessen am 2026-10-03 mit einem anspruchsvollen 1080p-Testbild (Farbverlauf in Bewegung,
feines Rauschen, kleine Schrift), echtem MediaMTX und einem Zuschauer, über die WebRTC-Statistik
(`outbound-rtp` / `inbound-rtp`). Auflösung und Bitrate beim Zuschauer.

## Ausgangslage (v0.3): unscharf

VP8, `degradationPreference: maintain-framerate`, max. 6 Mbit/s, ohne Startbitrate:

| nach | Auflösung | Bitrate | Grenze laut Browser |
|---|---|---|---|
| 3 s | **480×270** | 4,8 Mbit/s | bandwidth |
| 8 s | **640×360** | 5,2 Mbit/s | bandwidth |
| 15 s | 1920×1080 | 5,1 Mbit/s | none |

Chrome startet mit vorsichtiger Bandbreitenschätzung und opfert bei „Bildrate halten“ die
Auflösung – obwohl die Bitrate längst reicht. Bei jedem kurzen Einbruch wiederholt sich das.

## Vergleich (gleiche Quelle, nach 10 s)

| Variante | Zuschauer sieht | Eindruck (Ausschnitt in Originalgröße) |
|---|---|---|
| VP8, Bildrate halten (alt) | 640×360 | winzig, unscharf |
| VP8, Auflösung halten, 6 M | 1920×1080 | Schrift scharf, Blockartefakte um feine Punkte |
| VP9, Auflösung halten, 8 M | 1920×1080 gemeldet | **schwarzes Bild** beim Zuschauer |
| **H.264, Auflösung halten, 8 M, Start 4 M** | 1920×1080 | **sauber und scharf** |
| AV1, Auflösung halten, 8 M | 1920×1080 | ähnlich gut wie H.264 |
| VP8, balanced, 10 M | 480×270 → 960×540, 15 fps | schlecht |

Startbitrate (Chrome-Hinweis `x-google-start-bitrate` im SDP): mit ihr 1080p ab der ersten
Sekunde, ohne sie die ersten Sekunden mit 15 fps und gröberem Bild.

## Entscheidung

- **H.264 bevorzugt** (sauberstes Bild, jedes Gerät dekodiert es, iPhones in Hardware),
  VP8 als Ersatz, VP9 zuletzt.
- **Startbitrate** passend zur Qualitätsstufe.
- **Film**: Auflösung halten. **Spiel**: Bildrate halten, bis 60 fps – dank Startbitrate
  ebenfalls ab Sekunde 1 in 1080p.
- Stufen und gemessene Bitrate (H.264, Film):

| Stufe | Auflösung | gemessen | Upload je Zuschauer |
|---|---|---|---|
| Hoch | 1920×1080 | ~6,5 Mbit/s | bis 8 Mbit/s |
| Mittel | 1280×720 | ~3,3 Mbit/s | bis 4 Mbit/s |
| Sparsam | 853×480 | ~1,7 Mbit/s | bis 2 Mbit/s |

Das Sende-Pult zeigt live, was wirklich gesendet wird, und warnt, wenn der Browser wegen
Prozessor („cpu“) oder Verbindung („bandwidth“) zurückregelt.

## Grenzen dieser Messung

Gemessen auf einem Rechner (12 Kerne, Software-Encoder in Chromium) mit Server auf demselben
Gerät. Über das Internet begrenzt die Upload-Bandbreite des Servers; auf schwächeren Rechnern
kann der Encoder („cpu“) begrenzen – dann hilft „Mittel“.

## Echter Film, echter Rechner (Live-Messung beim ersten Test)

Gemessen an einer laufenden Übertragung (Brave, geteilter Tab mit Film, ein Zuschauer im
privaten Fenster), als zusätzlicher Mess-Zuschauer über 20 s:

| | Wert |
|---|---|
| Video | H.264, 1850×920 (Fenstergröße), 23,8 fps (Film: 24 fps), 6,1 Mbit/s |
| Bildqualität | QP ⌀ 21,7 – sehr gut |
| Aussetzer | 0 verworfene Bilder, 0 Freezes, 0 Paketverluste |
| Puffer beim Zuschauer | ~100 ms |
| Prozessor | Browser zusammen ~1,7 von 12 Kernen – keine Grenze |
| **Ton** | **Opus, mono, ~31 kbit/s** – das schwächste Glied |

Am Bild war kaum noch etwas zu holen; voll 1080p gibt es, wenn der geteilte Tab Vollbild ist.

## Ton: Stereo statt Telefonqualität

Chrome sendet Opus ohne Zusatz als Mono mit ~32 kbit/s und sprachoptimiert. Gemessen mit
440 Hz links / 880 Hz rechts und Frequenzanalyse je Kanal beim Zuschauer:

| | gesendet | MediaMTX | beim Zuschauer | links 440/880 Hz | rechts 440/880 Hz |
|---|---|---|---|---|---|
| vorher | mono | 1 Kanal | 33 kbit/s | -34 / -34 dB | -34 / -34 dB |
| nur Sender stereo | stereo | 2 Kanäle | 191 kbit/s | -34 / -34 dB | -34 / -34 dB |
| **Sender + Zuschauer** | stereo | 2 Kanäle | **194 kbit/s** | **-28 / -119 dB** | **-109 / -28 dB** |

Zwei Dinge waren nötig: Der Sender schickt `stereo=1;sprop-stereo=1;maxaveragebitrate=…`
(Hoch 192, Mittel 128, Sparsam 96 kbit/s) und nimmt ohne Sprachfilter auf (keine Echo- und
Rauschunterdrückung, keine automatische Lautstärke). **Und der Zuschauer muss mit `stereo=1`
ankündigen, dass er Stereo hören will** – sonst mischt Chrome das Signal wieder zu Mono.
Die E2E-Suite prüft das mit derselben Zwei-Ton-Messung.

## Gleichmäßigkeit: Puffer beim Zuschauer

Eindruck aus dem Test: „läuft intern ein wenig jittrig“. Gemessen per `requestVideoFrameCallback`
für jedes Bild: Abstand der Aufnahme-Zeitstempel gegen Abstand der Anzeige beim Zuschauer
(laufender Stream, 20 s je Messung, nacheinander):

| Puffer (`jitterBufferTarget`) | Anzeige-Streuung | Aufnahme-Streuung | Abweichung Anzeige↔Aufnahme p95 / max |
|---|---|---|---|
| Standard (~46 ms) | 16,1 ms | 14,0 ms | 23 ms / **65 ms** |
| **300 ms** | **13,5 ms** | 13,1 ms | **14 ms / 24 ms** |
| 600 ms | 14,3 ms | 11,1 ms | 20 ms / 31 ms |

WebRTC ist auf Videocalls getrimmt und zeigt Bilder so früh wie möglich. Mit 300 ms Puffer
fügt der Transport praktisch keine Unruhe mehr hinzu; mehr Puffer brachte nichts. Alle
Zuschauenden nutzen denselben Wert und bleiben damit untereinander synchron. Über das Internet
hilft der Puffer zusätzlich: verlorene Pakete können noch nachgefordert werden, bevor das Bild
gezeigt wird – weniger Klötzchen, weniger angeforderte Keyframes.

Was kein Puffer glättet: Unruhe, die schon beim Aufnehmen entsteht. Ein 24-fps-Film auf einem
60-Hz-Bildschirm läuft im 3:2-Takt, ein geteilter Tab übernimmt diesen Takt (gemessen: Abstände
17–67 ms statt gleichmäßig 42 ms). Abhilfe: **OBS mit dem Film als „Medienquelle“** – OBS liest
die Datei direkt und sendet exakt gleichmäßige Bilder, dazu mit gründlicherer Kodierung.
