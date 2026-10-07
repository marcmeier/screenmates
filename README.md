<div align="center">

<img src="frontend/public/favicon.svg" alt="screenmates logo" width="88" height="88">

# screenmates

**The self-hosted movie-night app for your circle of friends.**<br>
Plan the night, let the case pick the film, watch together live – even from different couches.

[![CI](https://github.com/marcmeier/screenmates/actions/workflows/ci.yml/badge.svg)](https://github.com/marcmeier/screenmates/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/marcmeier/screenmates?color=e50914)](https://github.com/marcmeier/screenmates/releases)
[![License: AGPL v3](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)
![Python](https://img.shields.io/badge/python-3.12%2B-3776ab?logo=python&logoColor=white)
![Vue](https://img.shields.io/badge/vue-3-42b883?logo=vuedotjs&logoColor=white)
![Docker](https://img.shields.io/badge/docker-compose-2496ed?logo=docker&logoColor=white)

[Features](#-features) ·
[Quick start](#-quick-start) ·
[Configuration](#-configuration) ·
[Cinema setup](#-cinema-watch-together) ·
[Docs](#-documentation) ·
[Contributing](#-contributing)

<img src="docs/assets/hero.png" alt="screenmates on desktop and phone" width="100%">

</div>

## Why screenmates?

Group chats are terrible at movie nights. Nobody knows who's coming, twenty films get suggested and
nobody decides, and afterwards nobody remembers what you watched or who loved it.

screenmates gives your group one place for the whole evening: **who's in, what we watch, watching it
together, and remembering it** – with a loot-box style case that makes picking the film the best part of
the night. It's self-hosted, invite-only, has no accounts or passwords to manage, and runs in a single
Docker container.

## ✨ Features

### 🗓️ Plan the night
- **Who's in?** – everyone answers *I'm in*, *Maybe* or *Can't make it*.
- **Date poll** when the day is still open; fixing a date turns the votes into replies.
- **Invitation card** as an image for your group chat, and the date **in your calendar** – as a file or a
  live subscription across all your groups.
- **Evening mode** on the day itself guides through three steps: *Who's here?* → *Open the case* → *Roll film!*
- **House rules & info**, an **activity feed** and *"On this day"* – what you watched around this date in earlier years.

### 🎁 Let the case decide
- Everyone **suggests** films and has **one veto**.
- The **movie-night case** opens like a CS2 case: a reel of posters races past and slows down to reveal the
  film of the night. Rarity colors show the **real odds** – more votes, better chances.
- The host opens it **for everyone at once** – all members see the same reel and the same winner, live.
- Each suggestion shows **how much your group will probably like it** ("For you ≈ 4.2 ★") and **where it's
  streaming** – your group's subscriptions first.

### 🍿 Find something to watch
- **Shelves like a streaming service:** what's on your subscriptions, Netflix, Prime Video, Disney+ & co.,
  genre shelves, free films, new releases, hidden gems and classics.
- **All films** grid with filters for service, genre, decade, rating and runtime.
- **One search field** for films and people (with filmographies).
- **Ask the AI:** *"slow-burn folk horror, but not too gory"* → real, existing films (optional, bring your own key).
- Film details with trailer, **"Where's it on?"** (subscription, rent, buy), cast, similar films and
  **"Who'll like it?"** – estimated stars for each person, learned from their own ratings.

### 📺 Cinema: watch together
- The host **shares a browser tab or streams from OBS** – everyone sees the same picture with
  **sub-second latency** over WebRTC, in 1080p with stereo sound.
- **Chat and reactions** (😱 🍿 😂 …) fly across the picture for everyone – fullscreen too.
- The host can call a **pause**; viewers can send *"Hang on, be right back"*.
- Afterwards one click logs the film as watched, with everyone who was there.

### 📖 Remember it
- **Our films:** a watchlist and the history of everything you've watched – stars and comments per
  person, attendees, a **guestbook** with replies and hearts.
- **"How was it?"** asks for your stars the day after.
- **Year in review:** your film year in numbers – nights, hours, genres, best and most divisive film,
  records and awards like *Regular* or *Harshest critic* – also as a **story** to tap through.

### 🏆 Awards, profiles & more
- **Awards like on Xbox and Steam** – Bronze to Platinum, secret ones, levels, a showcase on your profile.
  Designed so that spamming doesn't pay ([how](docs/AWARDS.md)).
- **Kindred tastes:** see who in the group rates films most like you.
- **Your own look:** seven dark color themes and seven fonts, per person.
- **Live everywhere:** ratings, comments and suggestions show up for everyone without reloading.
- **Push notifications** (Web Push) for new dates, polls, the case opening, the cinema going live, replies
  and more – each person picks what they want. Works as a home-screen app on iPhone, too.
- **German and English**, chosen per person.

### 👥 Built for groups of friends
- **Invite-only:** without an invitation link, there's nothing to see. Links can add people directly or
  require approval, with expiry and usage limits, revocable any time.
- **No accounts:** pick your name – and optionally protect it with a **film as your password**.
- **Several groups per server**, each with its own movie night, history and cinema; names, levels and
  awards are shared ([how groups work](docs/GROUPS.md)).
- **Host baton:** one person runs the night; the baton can be handed over, taken over, or voted on.
- **Admin area** with user management, invitation links, AI cost tracking and a danger zone with automatic
  backups.

## 📸 Screenshots

| Movie night | Find |
|---|---|
| ![Movie night with date, suggestions and the case](docs/screenshots/movie-night.png) | ![Find with streaming shelves](docs/screenshots/discover.png) |
| **The case – opened for everyone** | **Film details** |
| ![The case reveals the film of the night](docs/screenshots/case.png) | ![Film details with trailer and where to watch](docs/screenshots/details.png) |
| **Cinema** | **Our films** |
| ![Watching together with chat and reactions](docs/screenshots/watch-party.png) | ![History with ratings and guestbook](docs/screenshots/our-movies.png) |
| **Tonight: evening mode** | **Profile & awards** |
| ![Evening mode guides through the night](docs/screenshots/tonight.png) | ![Profile with level, kindred tastes and awards](docs/screenshots/profile.png) |
| **Year in review** | **Date poll** |
| ![The group's film year in numbers](docs/screenshots/year-in-review.png) | ![Finding a date by poll](docs/screenshots/date-poll.png) |

<details>
<summary><b>More screenshots</b> – phone, host baton, themes, activity</summary>

| Phone | Cinema on the phone | Year in review as a story |
|---|---|---|
| ![Movie night on a phone](docs/screenshots/mobile.png) | ![Cinema on a phone](docs/screenshots/mobile-watch-party.png) | ![Story](docs/screenshots/story.png) |

| Host baton | Your own look |
|---|---|
| ![Voting on who takes the host baton](docs/screenshots/host-baton.png) | ![Color themes and fonts](docs/screenshots/themes.png) |

| Activity | Kindred tastes |
|---|---|
| ![Activity feed](docs/screenshots/activity.png) | ![Who rates like you](docs/screenshots/taste-match.png) |

</details>

## 🚀 Quick start

### Docker Compose (recommended)

```bash
git clone https://github.com/marcmeier/screenmates.git
cd screenmates
cp backend/.env.example backend/.env   # optional: add your TMDB key here
docker compose up -d --build
```

Open **http://localhost:8000** – the first name you create becomes the admin. From there, create
invitation links for your friends under *Admin → Groups*.

The stack includes screenmates and the MediaMTX media server for the cinema. All data (SQLite database,
push keys, profile pictures) lives in the `screenmates-data` volume – back it up.

> [!TIP]
> Without any configuration screenmates runs on a small built-in demo catalog. For the full film catalog,
> get a free [TMDB API key](https://www.themoviedb.org/settings/api), put it in `backend/.env`, and click
> *Sync with TMDB* in the admin area.

### From source

Requires Python ≥ 3.12 and Node ≥ 20.

```bash
make install   # backend venv + npm ci
make dev       # backend :8000 + Vite :5173 → http://localhost:5173
```

`make help` lists every task. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development setup.

### Going public

To use screenmates with friends over the internet, put it behind a reverse proxy with HTTPS (Caddy,
Traefik, nginx …) and set:

```dotenv
COOKIE_SECURE=true
FORWARDED_ALLOW_IPS=<your proxy's IP or network>
```

For the cinema, see [Cinema setup](#-cinema-watch-together) below.

## 🔧 Configuration

Everything is optional. Set it in `backend/.env` or as environment variables.

| Variable | Default | Purpose |
|---|---|---|
| `TMDB_API_KEY` | – | Full film catalog, posters, people, trailers, where to watch ([get a key](https://www.themoviedb.org/settings/api)). v3 key or v4 token. |
| `TMDB_LANGUAGE` | `de-DE` | Language of film data (titles, plots, genres), e.g. `en-US`. |
| `TMDB_REGION` | `DE` | Region for streaming availability, e.g. `US`, `GB`. |
| `LLM_API_KEY` | – | Enables the AI search – an Anthropic key or an [OpenRouter](https://openrouter.ai) key (`sk-or-…`, detected automatically). |
| `LLM_MODEL` / `LLM_PROVIDER` / `LLM_BASE_URL` | – | Pick the model (OpenRouter default: the inexpensive `deepseek/deepseek-v4.1-flash`), force a provider, or use any OpenAI-compatible API. |
| `DATABASE_URL` | SQLite | SQLite in `backend/screenmates.db`, in Docker `/data/screenmates.db`. |
| `MEDIA_DIR` | `backend/media` | Profile pictures; in Docker `/data/media` (same volume as the database). |
| `COOKIE_SECURE` | `false` | Set to `true` behind HTTPS. |
| `FORWARDED_ALLOW_IPS` | – | Your reverse proxy's IP(s), comma-separated, so rate limits see the real client IP. |
| `CORS_ORIGINS` | – | Only needed if frontend and API run on different origins. |
| `PUSH_KONTAKT` | – | Contact for the browsers' push services (`mailto:…` or `https:` URL). Push keys are generated automatically on first use. Push requires HTTPS (or `localhost`). |
| `KINO_PUBLIC_HOST` | – | *(Compose)* Public hostname or IP of your server, so cinema viewers outside your network can connect. |

### Admin CLI

For the operator, inside the container (or `backend/.venv/bin/python -m app.cli …`):

```bash
docker compose exec screenmates python -m app.cli namen          # list all names
docker compose exec screenmates python -m app.cli admin "Alice"  # make someone an admin
docker compose exec screenmates python -m app.cli einladung      # emergency link (once, 24 h, direct)
```

That's how an existing installation gets its first admin, and how you get back in if every admin is
locked out.

## 📺 Cinema: watch together

The cinema streams via WebRTC through the [MediaMTX](https://github.com/bluenviron/mediamtx) media
server: the host sends **once**, MediaMTX distributes to every viewer. screenmates only relays the
connection negotiation (WHIP to stream, WHEP to watch) and checks permissions on every step; MediaMTX's
own HTTP ports stay internal.

**Locally:** `make kino-install` downloads MediaMTX (pinned version, verified checksum), and `make dev`
starts it automatically. With Docker it's already part of `compose.yaml`.

**For friends outside your network,** screenmates must be reachable from the internet (VPS, home server
with port forwarding, or a private network like Tailscale), plus:

1. Open port **8189** (UDP, and TCP as fallback) to the media server.
2. Set `KINO_PUBLIC_HOST=your.server.example` (Compose) so viewers get a reachable address.
3. Behind HTTPS, set `COOKIE_SECURE=true`.
4. Against dropouts, enlarge the UDP receive buffer: on the host `net.core.rmem_max=8388608` (e.g. in
   `/etc/sysctl.d/`) and for MediaMTX `MTX_UDPREADBUFFERSIZE=8388608`. The Linux default (208 KB)
   overflows on 1080p keyframes.

**Bandwidth:** the server needs 2–8 Mbit/s upload **per viewer**, depending on the quality level.

**Streaming options:**
- **Share a screen or tab** right in the browser – one click. For sound, share a tab and tick "Share
  audio". Choose the **quality** (1080p / 720p / 480p) and the **content** (*Film* – sharpness first, or
  *Game* – smooth, up to 60 fps). Why H.264 and these settings: [measurements](docs/CINEMA-QUALITY.md).
- **OBS** (version 30+): under *Settings → Stream* choose **WHIP** and paste server and bearer token from
  the cinema page; for 1080p use 6000–8000 kbit/s, keyframe interval 1 s, no B-frames. **Best for films:**
  add the file as a *Media Source* – smoother than any screen capture.

> [!NOTE]
> Only stream what you're allowed to show – your own recordings, games, DRM-free films. Netflix & co.
> windows stay black when captured anyway (DRM).

Browser streaming, an OBS-style WHIP sender, watching with sound, and a viewer with UDP blocked (TCP
fallback) are tested automatically on every push – also against the real `docker compose` stack. For what
can't be automated (real OBS, viewers across the internet) there's a
[15-minute checklist](docs/CINEMA-CHECKLIST.md).

## 🏗️ Architecture

```
frontend/  Vue 3 + Vite + Pinia + vue-i18n   ─┐  development: Vite proxies /api → :8000
backend/   FastAPI + SQLModel/SQLite         ─┘  production: FastAPI serves API + built SPA
deploy/    MediaMTX config (cinema)
```

- **Backend** (`backend/app`): routers by area, authorization as central FastAPI dependencies
  (`session.py`, invite gate in `routers/zugang.py`), TMDB access with a local fallback catalog
  (`tmdb.py`), live updates via a lightweight poll (`/api/live`) that works through any proxy.
- **Frontend** (`frontend/src`): one SPA with hash routing, Pinia stores, central API error handling, a
  service worker for push notifications, installable as a PWA.
- **Database:** SQLite with Alembic migrations that the app applies at startup – updates never need manual
  steps.
- **Cinema:** WebRTC via MediaMTX, with screenmates as the permission gate (`/api/kino/mtx-auth`).

All endpoints are listed in the [API reference](docs/API.md); interactive OpenAPI docs are served at
`/docs` while the backend is running.

### Quality

```bash
make lint   # ruff + eslint
make test   # 270+ backend tests + Playwright E2E against the real backend (cinema with a real MediaMTX)
```

GitHub Actions runs lint, unit and E2E tests, and the full E2E suite against the `docker compose` stack
on every push and pull request.

## 📚 Documentation

| Document | What's inside |
|---|---|
| [Groups](docs/GROUPS.md) | Several circles of friends on one server – roles, invitations, what's shared |
| [Awards](docs/AWARDS.md) | The award catalog, levels, and the rules that keep it fair |
| [Prediction](docs/PREDICTION.md) | How "Who'll like it?" works – and how accurate it really is |
| [Cinema quality](docs/CINEMA-QUALITY.md) | Measurements behind the streaming settings (codec, bitrate, audio, buffering) |
| [Cinema checklist](docs/CINEMA-CHECKLIST.md) | Manual test for OBS and viewers over the internet |
| [API reference](docs/API.md) | Every endpoint with its permissions |
| [Changelog](CHANGELOG.md) | What changed in each release |

## 🗺️ Roadmap

- **TV series** (needs a `media_type` + `id` key)
- **Clips:** cut and share scenes from films
- Ideas from the community – [open a feature request](https://github.com/marcmeier/screenmates/issues/new?template=feature_request.yml)

## 🤝 Contributing

Contributions are welcome! Read [CONTRIBUTING.md](CONTRIBUTING.md) to get started, and please follow the
[Code of Conduct](CODE_OF_CONDUCT.md). Found a security issue? See [SECURITY.md](SECURITY.md).

## 📄 License

screenmates is free software under the [GNU Affero General Public License v3.0](LICENSE). If you run a
modified version as a service for others, you must make your source code available to them.

## 🙏 Acknowledgements

- Film data, images and streaming availability from [TMDB](https://www.themoviedb.org) – *This product
  uses the TMDB API but is not endorsed or certified by TMDB.* Streaming availability is provided to TMDB
  by [JustWatch](https://www.justwatch.com).
- Live streaming powered by [MediaMTX](https://github.com/bluenviron/mediamtx).
- Built with [FastAPI](https://fastapi.tiangolo.com), [SQLModel](https://sqlmodel.tiangolo.com),
  [Vue](https://vuejs.org) and [Vite](https://vite.dev).
- Inspired by [horror.marha.de](https://horror.marha.de).

<div align="center">
<sub>Made for movie nights with friends. 🍿</sub>
</div>
