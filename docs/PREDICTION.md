# "Who'll like it?" – how the prediction works and what it can do

In every film view, screenmates estimates how much each person will like the film. It is based
**only on that person's own stars**. Code: `backend/app/prognose.py`.

## Method

For each person, a small regularized regression (kernel ridge) learns what their stars depend on.
Each film is described by:

| Feature | Weight | Note |
|---|---|---|
| TMDB keywords ("slasher", "folk horror", "found footage" …) | 0.6 | only keywords that appear in at least **two** rated films – one-offs are noise |
| Genres | 0.3 | since 0.6 including horror itself, as not every film is one anymore |
| Decade | 0.6 | neighboring decades count half (1979 ≈ 1981) |
| TMDB score | 0.9 | "likes well-rated films" is the most common taste |
| Collection | 1.5 | parts of the same series |

Regularization λ = 2.5. Without a signal the estimate stays at the person's average; with few
examples it is damped.

**Reasoning shown:** the *most similar* film the person rated in the same direction. Similarity
ignores the TMDB score here: two good films are not the same kind of film. If the estimate is
close to the average, no reason is shown. The regression's largest term would have made a poor
explanation; for *Scream* it named *The Thing* instead of *Friday the 13th*.

## How good is it? (backtest)

`scripts/prognose-backtest.py`: 160 of the most-rated horror films with real TMDB keywords.
Measured back when screenmates only knew horror. Across all genres films differ more, which
should help the prediction rather than hurt it; this hasn't been re-measured yet.
Simulated people with a known taste rate random films, plus noise (σ = 0.6 stars, rounded). Each
rating is hidden once and estimated from the rest. The test measures how much smaller the error
is compared to the estimate "the person's average". Tuning and measurement used separate random
data.

| Ratings | Slasher | Supernatural | Classics | Quality | Monster | Random |
|---|---|---|---|---|---|---|
| 10 | +0 % | +1 % | +9 % | +10 % | +5 % | +1 % |
| 25 | +2 % | +10 % | +4 % | +21 % | +3 % | −2 % |
| 60 | +1 % | +13 % | +6 % | +19 % | +10 % | −4 % |

For comparison: someone who knew the taste exactly and only failed on the noise would reach 20–45 %.

**What this means:**
- The prediction is a **tendency, not a forecast**. It works best for tastes that hinge on
  quality, decade or subgenre.
- **Below 8 ratings** there is no estimate, because no method beat the average there. Up to 25
  ratings it is labeled "first tendency".
- It barely picks up **slasher preferences**. Among 25 random films only 2–3 are slashers, and TMDB
  tags them inconsistently ("slasher", "serial killer", "masked killer").
- For **purely random taste** it is marginally worse than the average (overfitting).

## Rejected

- **Nearest neighbors** (average plus weighted deviations of the most similar films): only half
  as good at 25 ratings, and worse than the average for slashers.
- **Normalized feature vectors:** no gain.

If you change the method, run the backtest before and after.
