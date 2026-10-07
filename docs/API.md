# API reference

All endpoints live under `/api`. Interactive OpenAPI docs are served at `/docs` while the backend
is running. Path and field names are German, as in the code (e.g. `termin` = date,
`kiste` = case, `gastgeber` = host, `kino` = cinema).

**Access:** – anyone · **N** a chosen name · **E** author or admin · **A** admin

**Invite-only:** as soon as one name exists, the whole API answers browsers without access with
`423` – except `/health`, `/zugang`, `/login`, `/kino/mtx-auth` and streaming with an OBS key
(`/kino/whip`, `/kino/sitzung/whip/…`). Access comes from an invitation (`POST /zugang`), a
login code (`POST /login`) or a name. "Anyone" then means: anyone with access.

**Names and devices:** a browser may only use the names it created or connected with a login code
(`auf_geraet` in `GET /users`). There are no passwords.

**Language:** every request may carry `X-Sprache: de|en`; texts the server writes for that request
(errors, shelves, awards, facts) follow it. Texts for someone else – push messages, the bell,
calendar feeds – follow that person's profile language.

## Catalog

| Method | Path | Access | Purpose |
|---|---|:-:|---|
| GET | `/health`, `/status` | – | Health check. Catalog, sync and feature status, watchlist and watched counts |
| GET | `/movies` | – | Catalog, by popularity (`limit`, `offset`) |
| GET | `/movies/{id}` · `/search/{id}` | – | Details (fills in missing data from TMDB) |
| GET | `/movies/{id}/credits` | – | Cast and key crew |
| GET | `/movies/{id}/aehnliche` | – | Recommendations (fallback: shared genres) |
| GET | `/search?q=` | – | Film search (`limit`, `seite`) |
| GET | `/discover` | – | Films by filter (released only): `sort`, `include` (all of these genres) / `exclude` (genre IDs), `sprachen`, `jahr_*`, `note_*`, `dauer_*`, `stimmen_*`, `seite` |
| GET | `/stoebern` | – | Browse shelves: "On our services", one per service (own subscriptions first), Free, New, genres, hidden gems, classics – each with its grid `filter` |
| GET | `/genres` | – | Genre IDs and names |
| GET | `/personen?q=` | – | People search (TMDB), by popularity |
| GET | `/personen/{id}/filme` | – | Filmography (optional `genre`), best known first, without cameo appearances |
| POST | `/sync` | A | Import the most popular and best-rated films from TMDB |
| POST | `/ki-suche` | – | Free text → film suggestions (needs `LLM_API_KEY`) |
| GET | `/movies/{id}/anbieter` | – | "Where's it on?": subscription/free/rent/buy in the configured region (JustWatch via TMDB), the group's subscriptions first with `bei` |
| GET | `/movies/{id}/trailer` | – | Best YouTube trailer (configured language before English) or `null` |
| GET | `/movies/{id}/prognose` | – | "Who'll like it?": estimated stars per person with a reason, from 8 ratings on ([PREDICTION.md](PREDICTION.md)) |
| GET | `/anbieter` | – | Subscription services for the picker (without rental shops) |

`/discover` also filters by streaming: `abos=true` (the group's subscriptions), `anbieter=8,9`
(these services by subscription), `kostenlos=true` (free, including with ads).
`/anbieter?zum_stoebern=true` only returns services that make a useful shelf (no rental shops,
channels or ad tiers), own subscriptions first.

Every film carries the group flags `gesehen` (watched), `gemerkt` (on the watchlist) and
`vorgeschlagen_von` (suggested by).

## Users & permissions

| Method | Path | Access | Purpose |
|---|---|:-:|---|
| GET | `/users` | – | Approved names, `ich`, `admin`, `antraege` (open requests, admins only), `auf_geraet` (ids of the names this browser may pick) |
| POST | `/users` | – | Create a name: the first name in an empty database becomes admin and needs the setup code from the server log (`setup`; throttled like `/zugang`); with a "direct" invitation you're in that group right away, otherwise it's a request (`freigegeben: false`) to the admins of the invitation's group. Admins create approved names directly. At most 20 open requests |
| POST | `/users/waehlen` | – | Switch to one of this browser's names (`user_id`) or sign out (`user_id: null`; the name stays on the browser) |
| DELETE | `/users/{id}` | A | Delete a user or reject a request (ratings and votes are removed, comments anonymized). Never the last admin |
| PUT/DELETE | `/users/{id}/bild` | E | Upload (image as request body, max. 5 MB; JPG/PNG/WebP/GIF, becomes 256×256 WebP without metadata) or remove a profile picture. E = the person themselves or an admin |
| GET | `/users/{id}/bild` | – | Profile picture (URL with `?v=…` from `users[].bild`, cached for long) |

| PUT | `/users/me/design` | N | Your look: color `theme` and `schrift` (font) |
| PUT | `/users/me/sprache` | N | Your language: `de` or `en` (applies on all devices) |
| POST | `/users/me/willkommen` · `/users/me/erste-schritte` | N | The introduction / the first-steps card was seen (applies on all devices) |
| POST | `/abos` | N | Set your streaming subscriptions (provider IDs) |
| POST | `/dabei` | N | Toggle your attendance at the next night (in ↔ no answer) |
| PUT | `/dabei` | N | Reply `antwort`: `ja`, `vielleicht`, `nein` or `null`; a yes counts for the "Kept your word" award |
| DELETE | `/dabei` | A | Reset everyone's attendance and replies |

## Groups

Everything about the movie night, history, watchlist, suggestions, veto, case, date, info, feed
and cinema refers to the session's **active group** and requires a name that is a member (`401`
without a name, `409` without a group, `404` for entries of other groups). "A" there means: admin
of *this group* or server admin. The catalog stays open to everyone; its flags (watched,
watchlisted, suggested, "on our services") apply to the active group.

| Method | Path | Access | Purpose |
|---|---|:-:|---|
| GET | `/gruppen` | N | My groups and the active one |
| POST | `/gruppen/aktiv` | N | Switch the active group (`gruppe_id`, own groups only) |
| GET | `/admin/gruppen` | group/server admin | Manageable groups with members |
| POST | `/admin/gruppen` | server admin | Create a group |
| PATCH | `/admin/gruppen/{id}` | group/server admin | Rename |
| DELETE | `/admin/gruppen/{id}` | server admin | Delete a group with everything in it (members and awards stay) |
| PUT/DELETE | `/admin/gruppen/{id}/mitglieder/{user}` | group/server admin | Add a member or set the group admin right (`admin`) / remove |

`/users` additionally returns `gruppe` (active group: `id`, `name`, `admin`, `mitglieder`);
`dabei` and `rueckmeldung` (`ja`/`vielleicht`/`nein`/`null`) apply to the active group.

## Awards

| Method | Path | Access | Purpose |
|---|---|:-:|---|
| GET | `/erfolge` | – | Catalog (secret ones as "???", rarity in %), everyone's level/title/showcase, latest unlocks, your own progress with points |
| GET | `/erfolge/{id}` | – | Profile: level, title, showcase, unlocked awards |
| POST | `/erfolge/neu` | N | Check and fetch your unlocks not yet shown (for the pop-up) |
| PUT | `/erfolge/vitrine` | N | Show up to three of your unlocked awards in the showcase |
| PATCH | `/admin/erfolge/{id}/{key}` | A | Revoke an award (`entzogen: true`, stays revoked) or give it back |

## Access & administration

| Method | Path | Access | Purpose |
|---|---|:-:|---|
| GET | `/zugang` | – | `gesperrt` (names exist), `offen` (this browser has access), `einladung` (group and mode of this browser's invitation) |
| POST | `/zugang` | – | Come in with an invitation (`token`). Throttled: 10 failed attempts (invitations and login codes) per IP, 100 in total per 15 min |
| POST | `/login` | – | Redeem a login code (`code`, e.g. `ABCD-EFGH`; case, spaces and dashes don't matter): this browser gets the name and is signed in with it. One use; throttled like `/zugang` |
| GET | `/login` | N | `geraete`: on how many browsers your name is |
| POST | `/login/code` | N | A login code for another device of yours: `code`, `path` (`/#/login/<code>`), `valid_until` (15 min) |
| POST | `/login/andere-abmelden` | N | Take your name off every other browser |
| DELETE | `/login/namen/{id}` | – | Take a name off this browser |
| GET/POST | `/admin/gruppen/{id}/einladungen` | group/server admin | The group's valid links, or a new link: `direkt`, `tage` (or `null`), `max_nutzungen` (or `null`), `notiz` |
| DELETE | `/admin/einladungen/{id}` | group/server admin | Revoke a link (people already in stay in) |
| POST | `/einladungen/annehmen` | N | Join a group with an existing name via its link (`direkt`) or ask to join |
| GET | `/admin/gruppen/{id}/anfragen` | group/server admin | New names that came with one of the group's links, and join requests |
| POST | `/admin/gruppen/{id}/anfragen/{user}` | group/server admin | Accept (`annehmen: true`) or reject |
| GET/POST | `/admin/users` | A | All names incl. requests and number of signed-in devices, or create an approved name directly |
| PATCH | `/admin/users/{id}` | A | `name`, `color` (`#rrggbb`), `admin`, `freigegeben` (approve a request). There is always one admin left |
| POST | `/admin/users/{id}/abmelden` | A | Take the name off every browser; browsers signed in with it also lose access |
| POST | `/admin/users/{id}/login-code` | A | A login code for that person (valid 24 h), e.g. after a lost phone or for a name created by an admin |
| GET | `/admin/ki-nutzung` | A | How much the AI search was used and what it cost (as far as the provider reports) |
| GET | `/ueber` | – | About page: version, repository, imprint/privacy/donation texts, linked accounts (reachable without an invitation) |
| PUT | `/admin/seiten/{key}` | A | Edit an about-page text or account |

## Movie night

| Method | Path | Access | Purpose |
|---|---|:-:|---|
| GET | `/suggestions` | – | Suggestions per film with `von`, sorted by votes |
| POST | `/suggestions` | N | Suggest a film (idempotent) |
| DELETE | `/suggestions/{movie_id}` | N | Withdraw your suggestion |
| DELETE | `/suggestions` | N | Withdraw all your suggestions |
| DELETE | `/suggestions/alle` | A | Delete all suggestions |
| POST/DELETE | `/veto` | N | Place or withdraw your veto against a suggestion (one per person) |
| GET/POST | `/spin` | – | Pool with `gewicht` (weight; films with a veto excluded), or a weighted draw |
| GET | `/kiste` | N | The case currently being opened for everyone (with server time `jetzt` for the synchronized reel) |
| POST | `/kiste` | host/A | Open the case for everyone – all members see the same reel and the same winner live; notifies absent members via push |
| DELETE | `/kiste/{id}` | host/A | Take down the film of the night (e.g. plans changed) |
| GET | `/termin` | – | Next date with `notiz` (past dates: `null`) |
| PUT/DELETE | `/termin` | N | Set (without a time zone = server time zone) or remove the date. Setting it notifies the group via push |
| GET | `/termin.ics` | N | The next date as a calendar file |
| GET | `/termin/umfrage` | N | Date poll: open proposals with votes, `favorit`, `darf_festlegen` |
| POST | `/termin/umfrage` | N | Propose a date (`termin`, `notiz`; at most 8, counts as your own yes) |
| PUT | `/termin/umfrage/{id}/stimme` | N | `antwort`: `ja`, `vielleicht`, `nein` or `null` |
| DELETE | `/termin/umfrage/{id}` | E/F | Withdraw a proposal |
| POST | `/termin/umfrage/{id}/festlegen` | F | Fix the date: answers become replies, the poll closes |
| DELETE | `/termin/umfrage` | F | End the poll without a date |
| GET/POST/DELETE | `/kalender` | N | Personal calendar subscription link (`pfad`): view, regenerate (the old one stops working), turn off |
| GET | `/kalender/{token}.ics` | token | Calendar subscription: the next dates of all your groups, without sign-in |
| GET | `/rueckblick` · `/rueckblick/{jahr}` | N | Years with films, or the group's film year in numbers |
| GET | `/erinnerungen` | – | "On this day": films watched in earlier years, ±3 days (`heute=` for testing) |
| GET | `/events` | – | Activity feed |
| GET | `/live` | – | Live poll every open app sends: a `stand` version (changes when anything changed, so clients reload only then), unread `glocke` count, the running `kiste` and the `gastgeber` state; also marks you as present |
| GET | `/statistik` | – | Little facts for the sidebar ("1,234 hearts given") – server-wide totals only, never about one person |
| GET/POST/DELETE | `/wishlist[/{movie_id}]` | –/N/N | Watchlist |

**F** = may decide: whoever started the poll, the host, an admin of the group – or anyone, as long
as nobody holds the baton.

## Host baton

| Method | Path | Access | Purpose |
|---|---|:-:|---|
| GET | `/gastgeber` | N | Who holds the baton, who is present, an open handover vote (`wechsel`) |
| POST | `/gastgeber/uebergeben` | host/A | Offer the baton to someone in the group, who accepts or declines |
| POST | `/gastgeber/uebernehmen` | N | Take the baton – at once if nobody holds it, the host isn't around, or you're a group admin; otherwise those present vote (the host's vote counts double, silence is consent) |
| POST/DELETE | `/gastgeber/wechsel/{id}` | N | Accept/decline an offer or vote (`ja`) / withdraw your own request |

## Watched

| Method | Path | Access | Purpose |
|---|---|:-:|---|
| GET | `/watched` | – | History (`alle=true` includes hidden entries) |
| POST | `/watched` | N | Mark as watched. Removes the film from the watchlist and suggestions |
| PATCH | `/watched/{id}` | N | Change the date, hide |
| DELETE | `/watched/{id}` | A | Delete the entry with its ratings and comments |
| POST | `/watched/{id}/rating` | N | 1–5 stars (overwrites your own rating) |
| DELETE | `/watched/rating/{id}` | E | Delete a rating |
| POST | `/watched/{id}/notes` | N | Guestbook entry, with `parent_id` as a reply |
| DELETE | `/watched-notes/{id}` | E | Delete a comment (with its replies) |
| POST | `/watched/hearts` | N | Toggle a heart on a comment |
| POST | `/watched/{id}/dabei` | N | Set the attendees |
| GET | `/watched/zu-bewerten` | N | "How was it?": your nights of the last 4 days without your stars |

## Wishes & info

| Method | Path | Access | Purpose |
|---|---|:-:|---|
| GET/POST | `/features` | –/N | Wishes (open by votes, then done) |
| PATCH/DELETE | `/features/{id}` | E | Edit text or delete |
| PATCH | `/features/{id}/done` | A | Mark as done |
| POST | `/features/{id}/vote` | N | Toggle your vote |
| POST | `/features/{id}/notes` | N | Add a note |
| DELETE | `/feature-notes/{id}` | E | Delete a note |
| GET/PUT | `/info` | –/A | Markdown info text (house rules etc.) |

## Cinema

| Method | Path | Access | Purpose |
|---|---|:-:|---|
| GET | `/kino` | – | Live status, title, linked film, viewers, audience of the show, `pause` |
| POST | `/kino/programm` | A | Set the title, link a film |
| POST/DELETE | `/kino/da` | N | Heartbeat while watching, or leave |
| POST | `/kino/whip` | A or OBS key | Stream (WHIP proxy to MediaMTX) |
| POST | `/kino/whep` | N | Watch (WHEP proxy) |
| PATCH/DELETE | `/kino/sitzung/{whip,whep}/{id}` | as above | Renegotiate or end a WebRTC session |
| GET | `/kino/obs` · POST `/kino/obs/neu` | A | Server URL and stream key for OBS, renew the key |
| DELETE | `/kino` | A | End the stream for everyone (OBS too) |
| POST | `/kino/mtx-auth` | internal | Permission check MediaMTX calls for every action |
| GET | `/kino/chat` | N | Chat (kept for 30 days) and reactions: without a cursor the last 50 messages and `letzte`/`rletzte`, with `seit=<id>&rseit=<id>` everything new · `/kino/chat/aelter?vor=<id>` older ones |
| POST | `/kino/chat` · `/kino/reaktion` | N | Message (up to 300 characters) or reaction (`emoji` from `reaktionen`) |
| POST | `/kino/pause` | host/A | `{"an": true/false}`: pause banner over the picture |
| POST | `/kino/moment` | N | "Hang on, be right back" – arrives like a reaction via `/kino/chat` |

## Suggestions, bell, taste

| Method | Path | Access | Purpose |
|---|---|:-:|---|
| GET | `/suggestions/prognose` | N | Per suggestion `wert` (half stars), `genau` and `personen` (real stars or prediction); `fuer`: `dabei` (from two yeses) or `gruppe` |
| GET | `/suggestions/anbieter` | N | Per suggestion the best way to watch: `art` (`abo`/`kostenlos`/`leihen`/`kaufen`), `name`, `logo`, `bei` (whose subscription) |
| GET | `/glocke` · POST `/glocke/gelesen` | N | The last 30 notifications with `neu`, count `ungelesen` (also in the live poll as `glocke`) · mark all read |
| GET | `/users/{id}/geschmack` | N | Rating similarity to everyone who shares a group with you (from 3 films in common) |

## Danger zone

| Method | Path | Access | Purpose |
|---|---|:-:|---|
| GET | `/admin/reset` | A | Areas with counts (`chronik`, `filmabend`, `kino`, `wuensche`, `erfolge`, `statistik`), `neustart` (other names + invitations), existing backups |
| POST | `/admin/reset` | A | Clear `bereiche` (for all groups) or `["neustart"]`; `bestaetigung` must be `LÖSCHEN` or `DELETE`. Backs up the database first |

## Notifications

| Method | Path | Access | Purpose |
|---|---|:-:|---|
| GET | `/push` | N | VAPID `schluessel` (for `pushManager.subscribe`), chosen `arten`, number of `geraete` |
| POST | `/push/abo` | N | Register this device (`endpoint`, `keys`, `geraet`); belongs to the person signed in on it |
| POST | `/push/abmelden` | N | Unregister this device |
| PUT | `/push/arten` | N | Change your choice, e.g. `{"arten": {"kino": false}}` |
| POST | `/push/test` | N | Test message to all your devices |
