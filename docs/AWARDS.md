# Awards

An achievement system modeled on Xbox and Steam: joining movie nights, rating, writing in the
guestbook, setting dates, and streaming or watching in the cinema unlock awards, earn points and
raise your level. Code: `backend/app/erfolge.py` (rules and catalog),
`backend/app/routers/erfolge.py` (API), `frontend/src/components/tabs/ErfolgeTab.vue`.

## What's in it

| From | Adopted |
|---|---|
| Xbox | points per award (Gamerscore), tiers Bronze 10 · Silver 25 · Gold 50 · Platinum 100, secret awards ("???" until unlocked), a pop-up on unlock |
| Steam | rarity ("75 % of the group"), progress bars (visible only to yourself), levels from points with titles, a **showcase** of up to three awards on your profile |

- **No leaderboard:** the group sees everyone's level and title, alphabetically; only you see your own score.
- **Level** n needs 12.5·n·(n−1) points (level 2 from 25, 3 from 75, 4 from 150, 5 from 250 …). Titles: Popcorn rookie, Film fan (3), Cinephile (5), Critics’ darling (7), Directing legend (9), Hall of Fame (11).
- From level 2 on, the level appears as a badge on every avatar; avatars in attendee lists and comments link to the profile (`#/erfolge/person/<id>`).
- Unlocks show up in the movie night's activity feed (the retroactive ones from the first run do not).

## Catalog

| Family | Tiers (goal) | Counts |
|---|---|---|
| 🛋️ Regular | 1 · 5 · 15 · 40 | confirmed movie nights you attended (at most one per day) |
| 🏠 Host | 1 · 5 · 15 | dates you set on which (±1 day) a confirmed night took place |
| 🤞 Kept your word | 1 · 5 · 15 | dates you said yes to and whose confirmed night (±1 day) you attended |
| 🗓️ Date finder | once (Silver) | a date you proposed won the poll, and the night took place |
| 🎯 Sharpshooter | 1 · 5 · 15 | your suggestions that were watched at a confirmed night |
| ✍️ Critic | 1 · 10 · 30 · 75 | confirmed nights you rated |
| 📖 Guestbook | 1 · 10 · 40 | guestbook entries of 20+ characters, one per night, at most three per day |
| ❤️ Heart | 3 · 6 · 10 | **different other** people who hearted one of your entries |
| 💡 Ideas | 1 · 3 · 10 | your wishes that were implemented or backed by three **other** people |
| 🎬 Cinema director | 1 · 5 · 15 | shows you streamed with at least two others watching for 5 minutes each |
| 🎟️ Cinemagoer | 1 · 5 · 20 | shows you watched for at least 5 minutes |
| Profile | once | 📸 profile picture, 🔐 film password, 📺 streaming services added |
| Secret | once | seven of them – see the code, not spoiled here |

## Against gaming the system

1. **Points only come from awards, never per action.** The tiers cap what repetition can earn.
2. **What counts is the current state, and only distinct things.** Deleting and re-creating, changing a rating ten times: gets you nothing.
3. **Liking and voting are never rewarded.** Only what you receive *from different other people* counts. Your own hearts and votes never do.
4. **A movie night only counts once confirmed:** at least two attendees, *another person who was there* rated or commented on it, it isn't in the future, and it was logged at most two days afterwards (backdated entries don't count). Ratings, guestbook entries and hits only count for such nights.
5. **What can't be read from the data is logged** (table `ereignis`): who sets a date, who streams and watches in the cinema, whose suggestion gets watched.
6. **Awards are permanent** (as on Xbox/Steam). Admins can **revoke** an award on a profile; it stays revoked until an admin gives it back.
7. **Retroactive:** everything that already existed when awards were introduced (`appmeta.erfolge_seit`, migration 0005) counts once, as it is. The first check runs at startup; its unlocks are marked `rueckwirkend` and arrive as a single summary pop-up instead of a flood.

No rule fully stops two friends from confirming everything for each other – but at most one night per day and the tiers keep that slow, and admins can revoke.

## Technical notes

- Evaluation runs for everyone at once (`erfolge.stand`), at most every 5 seconds (`pruefen`), and immediately on `POST /api/erfolge/neu`. The frontend calls that after every successful write (batched) and shows new unlocks as a pop-up.
- New awards: add an entry to `KATALOG`; new families need a count in `stand()` and a test in `tests/test_erfolge.py`.
