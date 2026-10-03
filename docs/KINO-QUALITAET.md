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
