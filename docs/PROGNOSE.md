# „Wem gefällt's?" – wie die Prognose funktioniert und was sie kann

In jeder Filmansicht schätzt screenmates, wie der Film jeder Person gefallen wird. Grundlage sind
**nur ihre eigenen Sterne**. Code: `backend/app/prognose.py`.

## Verfahren

Pro Person lernt eine kleine regularisierte Regression (Kernel-Ridge), wovon ihre Sterne abhängen.
Jeder Film wird dafür beschrieben durch:

| Merkmal | Gewicht | Bemerkung |
|---|---|---|
| TMDB-Stichworte („slasher", „folk horror", „found footage" …) | 0,6 | nur Stichworte, die bei mindestens **zwei** bewerteten Filmen vorkommen. Einmalige sind Rauschen |
| Genres | 0,3 | ohne „Horror", das haben hier alle |
| Jahrzehnt | 0,6 | Nachbar-Jahrzehnte zählen halb (1979 ≈ 1981) |
| TMDB-Note | 0,9 | „mag gut bewertete Filme" ist der häufigste Geschmack |
| Filmreihe | 1,5 | Teile derselben Reihe |

Regularisierung λ = 2,5. Ohne Signal bleibt die Schätzung beim Durchschnitt der Person, bei wenigen
Beispielen wird sie gebremst.

**Begründung:** Gezeigt wird der *ähnlichste* Film, den die Person in dieselbe Richtung bewertet hat.
Die Ähnlichkeit zählt dabei ohne TMDB-Note: Zwei gute Filme sind nicht die gleiche Art Film. Liegt
die Schätzung nahe am Durchschnitt, gibt es keine Begründung. Der größte Term der Regression wäre
als Begründung untauglich gewesen; bei Scream nannte er „Das Ding aus einer anderen Welt" statt
„Freitag der 13.".

## Wie gut ist sie? (Rückblick-Test)

`scripts/prognose-backtest.py`: 160 der meistbewerteten Horrorfilme mit echten TMDB-Stichworten.
Simulierte Personen mit bekanntem Geschmack bewerten zufällige Filme, dazu Rauschen (σ = 0,6 Sterne,
gerundet). Jede Bewertung wird einmal verdeckt und aus den übrigen geschätzt. Der Test misst, um
wie viel der Fehler kleiner ist als bei der Schätzung „Durchschnitt der Person". Feintuning und
Messung liefen auf getrennten Zufallsdaten.

| Bewertungen | Slasher | Übernatürlich | Klassiker | Qualität | Monster | Zufall |
|---|---|---|---|---|---|---|
| 10 | +0 % | +1 % | +9 % | +10 % | +5 % | +1 % |
| 25 | +2 % | +10 % | +4 % | +21 % | +3 % | −2 % |
| 60 | +1 % | +13 % | +6 % | +19 % | +10 % | −4 % |

Zum Vergleich: Wer den Geschmack exakt kennt und nur am Rauschen scheitert, käme auf 20–45 %.

**Was das heißt:**
- Die Prognose ist eine **Tendenz, keine Vorhersage**. Am besten trifft sie Geschmäcker, die an
  Qualität, Jahrzehnt oder Subgenre hängen.
- **Unter 8 Bewertungen** gibt es keine Schätzung, weil kein Verfahren dort besser als der Durchschnitt
  war. Bis 25 Bewertungen heißt sie „erste Tendenz".
- **Slasher-Vorlieben** erkennt sie kaum. Unter 25 Zufallsfilmen sind nur 2–3 Slasher, und TMDB
  verschlagwortet uneinheitlich („slasher", „serial killer", „masked killer").
- Bei **reinem Zufallsgeschmack** liegt sie minimal schlechter als der Durchschnitt (Überanpassung).

## Verworfen

- **Nächste Nachbarn** (Durchschnitt plus gewichtete Abweichungen der ähnlichsten Filme): bei 25
  Bewertungen nur halb so gut, Slasher sogar schlechter als der Durchschnitt.
- **Normierte Merkmalsvektoren:** kein Gewinn.

Wer das Verfahren ändert, lässt den Rückblick-Test vorher und nachher laufen.
