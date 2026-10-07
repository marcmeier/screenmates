# Privacy

What screenmates stores, which other services the browsers and the server talk to, and what you can
switch off. Use it as a starting point for the privacy notice on your about page (Admin → About); it is
not legal advice.

screenmates has no tracking, no analytics and no telemetry. It doesn't phone home.

## What the server stores

| Data | Why | How long |
|---|---|---|
| Names, colors, profile pictures (re-encoded, no EXIF), appearance and language | the people in the app | until the name is deleted |
| Group memberships, attendance, date poll answers | planning the evening | until the name or group is deleted |
| Suggestions, vetoes, watchlist, watched films, ratings, guestbook comments, hearts | the history | until deleted; comments stay without a name when their author is deleted |
| Wishes & ideas with votes and notes | the wish list | until deleted |
| Awards and the events they're counted from | awards | until the name is deleted |
| Cinema chat messages | the chat | 30 days |
| Notifications in the bell | the bell | 30 days |
| Push subscriptions (push service address, keys, a device label like "Firefox on Android") | push notifications | until switched off, or the push service drops them |
| Sessions (a random cookie id, which names the browser may use) | staying signed in | the cookie lasts a year; browsers without a name are forgotten after 30 days |
| Login codes and invitations (codes only as hashes, invitations as tokens) | getting in | login codes are single-use and expire after 15 minutes or 24 hours |
| AI search log: who, when, model, tokens, cost (not the text of the search) | the admins' cost overview | until an admin clears it |

Everyone can download all of their own data (Profile → Settings → Your data) and delete their name there.

Client IP addresses are only kept in memory for rate limiting. The web server's access log (uvicorn)
writes IP addresses and paths to the container log; turn it off with `UVICORN_ACCESS_LOG=false`, or keep
your log retention short. Your reverse proxy may log as well.

## Other services

| Service | Who talks to it | What it sees | When |
|---|---|---|---|
| TMDB (`image.tmdb.org`) | every browser | IP address, which posters are shown | whenever films are shown, if a TMDB key is set |
| TMDB API (`api.themoviedb.org`) | the server | searches and film ids, no personal data | with a TMDB key |
| YouTube (`youtube-nocookie.com`) | the browser | IP address, the trailer | only after clicking a trailer |
| STUN server (Google by default) | browsers in the cinema | IP addresses | when watching or sending; `STUN_SERVERS=` turns it off |
| Push services of Google, Mozilla, Apple, Microsoft | the server | an encrypted message for a subscribed device | only for people who switched notifications on |
| Anthropic or OpenRouter | the server | the text of an AI search and titles the group has seen | only when an AI key is set and someone searches |

The STUN server lets browsers find their public address for the cinema. If MediaMTX has a public address
(`CINEMA_PUBLIC_HOST`), browsers usually manage without it: set `STUN_SERVERS=` (empty), and remove the
`webrtcICEServers2` entry from `deploy/mediamtx.yml` so MediaMTX doesn't ask Google either. You can also
point both at a STUN server of your own.

Fonts are bundled with the app; no font CDN is involved.
