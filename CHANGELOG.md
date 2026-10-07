# Changelog

All notable changes to screenmates are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/). Releases are published on
[GitHub](https://github.com/marcmeier/screenmates/releases).

## Unreleased

### Security
- Names belong to devices now. Until now anyone with an invitation link could pick any name that had
  no film password, including an admin's, and use it with all its rights. A browser can now only use
  the names it created itself or connected with a one-time login code.
- Login codes (`ABCD-EFGH`) come from Profile → Settings → "Connect another device", as text, link and
  QR code. They work once and for 15 minutes; codes an admin makes (Admin → People, or
  `python -m app.cli login <name>`) work for 24 hours. Only a hash of the code is stored, and wrong codes
  count against the same limit as wrong invitations.
- A fresh install no longer makes whoever reaches it first its admin. The first name needs the setup code
  that the server writes to its log on every start until then (`docker compose logs screenmates`, or
  `python -m app.cli einrichtung`). The log also shows a `/#/setup/<code>` link that fills it in.
  `SETUP_TOKEN` sets the code in advance.
- Responses carry a Content-Security-Policy (only the app's own scripts, trailers only from
  youtube-nocookie.com, no framing) and `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`,
  `Permissions-Policy`.
- The AI search needs a name and has a daily allowance per person (`LLM_LIMIT_PER_DAY`, default 30), so
  nobody can run up the provider bill.
- A browser that came with an invitation but has no name loses its access when the invitation expires or is
  withdrawn. Browsers that never got a name are forgotten after 30 days.
- Calendar feeds no longer take their links from a client-supplied `X-Forwarded-Host` header; `PUBLIC_URL`
  sets the address explicitly.

### Privacy
- Groups no longer see into each other. The rating prediction on a film page listed everyone on the server
  and used ratings from all groups, including the film and stars its "because you rated …" hint was based
  on. Predictions, the suggestions' group forecast and taste matching now use only the active group's
  members and evenings, and the AI search only hides films the active group has seen.

### Added
- Docker images for amd64 and arm64 on the GitHub container registry, built and published with every
  release; `compose.yaml` uses them, so a new install no longer builds anything.
- Time zone setting `TIMEZONE` (or `TZ`). Dates, reminders, "on this day", awards and the year in review
  used to be fixed to German time. Without the setting, a new install takes the zone of the first admin's
  browser. The date dialog says which zone it means ("Berlin time").
- Your data: Profile → Settings can download everything screenmates keeps about you as a file, and delete
  your own name.
- `STUN_SERVERS` for the cinema (default unchanged); empty turns the STUN server off.
- `docs/PRIVACY.md`: what is stored for how long, which other services see what, and what to switch off.

### Changed
- Film data defaults to English now (`TMDB_LANGUAGE=en-US`, `TMDB_REGION=US`); set `de-DE`/`DE` for German.
  The demo catalog follows that setting, as do genre names in the film data; the genre filter is in the
  app's language. A fresh install names its first group in the first admin's language ("Our group").
- Quotation marks, the trailer player's language and the page language no longer assume German.
- Danger zone: in the app it now clears areas of the active group only (history, movie night, cinema);
  other groups stay as they are. Server-wide areas (wishes, awards, statistics) and starting over with a
  single admin moved to the command line: `python -m app.cli reset <area>… [--keep <name>] --yes`, which
  shows what would go without `--yes` and backs up the database first, like the app.
- "Wishes & ideas" is optional: off on a new install, switched on in Admin → System. Installations in use
  keep it on.
- Public interfaces are English: `PUSH_CONTACT` (was `PUSH_KONTAKT`, falls back to `PUBLIC_URL`),
  `CINEMA_PUBLIC_HOST` (was `KINO_PUBLIC_HOST`), command line `names`, `invite`, `setup` (were `namen`,
  `einladung`, `einrichtung`), and the app sends its language as `Accept-Language` (was `X-Sprache`). The
  old names keep working.
- New `SOURCE_URL` for the source link on the about page, so a modified version can point to its own code
  as the AGPL asks. Push services no longer get the project's address as contact when `PUBLIC_URL` is set.
- Settings show on how many devices you are signed in, and can sign you out on all the others.
- "Sign out" keeps the name on the device so you can pick it again; "Remove from this device" takes it off.
- The "Better safe than sorry" award is now "Second screen": connect a second device of your own.

### Fixed
- Language: switching to English and right back to German could end in English, because the answers
  arrived in the other order. Language, theme and font now change on screen at once and reach the server
  in the order they were clicked.
- Settings → Appearance: picking a theme and then quickly a font could undo the theme, because the second
  change still sent the old theme along. Theme and font are now saved separately.
- Movie night page: a reload that started just before you saved the date (or a poll result) could arrive
  afterwards and make the date disappear again until the next change; the invitation then said "date to
  follow".

### Removed
- The film password. It only protected names whose owner had set one, and a favourite film is easy to
  guess.

### Upgrading
- Existing databases keep German time (Europe/Berlin) unless `TIMEZONE` says otherwise.
- If you relied on the old German defaults for film data, set `TMDB_LANGUAGE=de-DE` and `TMDB_REGION=DE`.
- Every browser that is signed in keeps its name. Browsers that were signed out need a login code once,
  from another device of that person or from an admin.

### Documentation
- The repository is now in English: new README with screenshots of the current app, translated docs
  (`docs/GROUPS.md`, `AWARDS.md`, `PREDICTION.md`, `CINEMA-QUALITY.md`, `CINEMA-CHECKLIST.md`, `API.md`)
  and changelog. Future entries are written in English.
- Licensed under the GNU AGPL v3.0; added contributing guide, security policy, code of conduct, issue and
  pull request templates, and Dependabot.

## 0.21.4 – 2026-10-07

### Changed
- **Trailer on the film details:** the big red play circle in the middle of the backdrop is replaced by a small
  glass pill "▶ Trailer" in the top-left corner, styled like the close button. The whole backdrop starts the
  trailer, and on hover it brightens and the pill takes the accent color.

## 0.21.3 – 2026-10-07

### Fixed
- **English UI:** the "On this day a year ago" card on the movie night was still in German.
- **Kindred tastes:** reads "Kim agrees … 80 % with you" instead of the clumsy "Kim ticks to … 80 % like you".
- **Settings → Appearance:** no longer claims film titles and plots stay in German – their language follows the
  server's `TMDB_LANGUAGE`.
- `backend/pyproject.toml` carried the outdated version 0.5.0; it now matches the app version.

## 0.21.2 – 2026-10-07

### Fixed
- **Color themes with a light accent:** in the "Black" theme (and less so in "Forest" and "Amber"), white text
  on the accent color was hard to read – e.g. "Open for everyone", the LIVE/TODAY badges, counters, step
  numbers and the trailer button. These spots now use the text color that matches the theme.

## 0.21.1 – 2026-10-07

### Changed
- **First steps:** "Turn on notifications" now has an unobtrusive "No thanks". The step then counts as done
  (with a hint where to turn them on later) – the checklist can be completed without notifications.
- **Trailer hard to miss:** film details show a large play button in the middle of the backdrop, and
  "Trailer" is also the first button next to Watched, Save and Suggest.

## 0.21.0 – 2026-10-07

### Changed
- **Movie night on the phone, compact and tidy:**
  - Planning card: the date on top (the hint in its own short line), Invite and Planning as two small icons
    next to it, below that who's in and your reply as **one** bar (I'm in · Maybe · Can't make it);
    "Set date" and "Vote" share a row.
  - Evening mode: only the current step (or one where you can act right now, e.g. open the case) is
    expanded – the others shrink to a single line. The case button is visible without scrolling; the LIVE
    badge stays on one line.
- **The case celebrates the winner:** when the reel stops, the film steps forward as a large card – with a
  short flash, a halo in its rarity color, a sheen across the poster, slowly turning light rays and a low
  tone before the fanfare; the other films fall back. With "reduce motion" only the large card remains.

## 0.20.2 – 2026-10-07

### Fixed
- **The cinema shows the drawn film:** the film from the case only went into the cinema program if nothing
  was there yet – so a title from an earlier show stayed put. Now every newly drawn case puts its film into
  the program once, as long as nobody is streaming; if you change it by hand afterwards, your choice stays.

## 0.20.1 – 2026-10-07

### Changed
- **Evening mode guides through the three steps:** exactly one step is current (red, softly glowing), done
  ones are checked off in green, upcoming ones dimmed; arrows between the steps and a progress bar show the
  way. Once the film is drawn, the steps before count as done (previously "Who's here?" stayed red with only
  one yes).
- **Step 3:** "Watch in the cinema" or "To the cinema – already showing" is now the big glowing button;
  "Watched – log it" sits plainly next to it.

## 0.20.0 – 2026-10-07

### Added
- **The host watches like everyone else:** whoever streams now sees the stream in the cinema like the
  others by default – with the same delay, with sound and a volume slider. To avoid double audio, the shared
  tab stays muted in Chrome. A switch in the player toggles the zero-latency preview.

### Fixed
- **"End stream"** reliably ends the show: first on the server, then locally (before, the local teardown
  could prevent the call).
- The "Open the case for everyone" button in evening mode looked disabled while step 1 was open.
- In the cinema, chat and picture start at the same height (the LIVE row sits above them); "since …" and
  "x watching" are translated.

### Changed
- **Suggestions and case aligned:** the "Movie-night case" heading now sits on the same row as
  "Suggestions", list and case start flush; the veto rule sits below the list.
- **The case button stands out:** "Open for everyone" and, in evening mode, "Open the case for everyone" or
  "Take the baton & open the case" glow in a gradient and pulse subtly (off with "reduce motion").

## 0.19.0 – 2026-10-06

### Changed – easier to read and take in
- **Movie night:** "Suggestions · 4" instead of a heading plus an explanatory sentence; the veto hint only
  shows while you haven't used your veto; the case just says "4 films in the case." (the rest is behind
  ⓘ). On phones and tablets the case sits below the suggestions – see what's in it first.
- **History by month:** "October 2026 · 3" as subheadings (with "Newest first"). The guestbook field only
  expands on "Write in the guestbook"; Hide/Delete are plainer.
- **News by day:** Today · Yesterday · This week · Older.
- **Awards:** "Up next" shows the three awards you're closest to; the catalog is collapsed per category
  (with "3/14"), "Recently unlocked" shows only five.
- **Wishes:** open ones sorted by votes, "Done" collapsed.
- **Empty lists** lead on with a button (watchlist → Find films, history → To the movie night).

## 0.18.0 – 2026-10-06

### Changed
- **Settings with tabs:** Profile · Appearance · Notifications (with calendar subscription) · Services –
  instead of one long page. Every tab has its own address (e.g. `#/profil/einstellungen/dienste`); hints
  like "Add your streaming services" link straight there.
- **More compact page headers on phones:** smaller heading, no subtitle (the bottom bar shows where you
  are); the profile header is smaller too.

### Fixed
- The bottom bar on phones was translucent in Safari; it now has a solid background.

## 0.17.0 – 2026-10-06

### Changed
- **Phone: navigation at the bottom.** Movie night · Find · Our films · Cinema · **More** sit in a fixed bar
  at the bottom edge (thumb height, above the iPhone home indicator). At the top a slim row remains with the
  logo, group picker (only with several groups), bell and profile picture. "More" opens profile, settings,
  news, wishes, admin, about and sign out; the profile picture leads to the profile.
- **Calmer suggestion cards:** year, rating, odds and prediction on one line, below that who suggested it
  and where it's streaming; titles at most two lines. On phones "+1/Withdraw" and "Veto" are compact icon
  buttons.
- **Red only for what matters most:** your own suggestion is marked green, admin labels and group cards are
  neutral; red stays reserved for the main action (e.g. "Open for everyone") and warnings.
- **Better legibility:** gray hint texts have more contrast, and everything is a notch larger on phones.
  The long group explanation in the admin area now sits behind an ⓘ.

## 0.16.0 – 2026-10-06

### Changed
- **Admin area with tabs:** Groups · People (with the number of open requests) · System (AI usage,
  catalog) · Danger zone. Group admins only see their groups. Every tab has its own address
  (e.g. `#/verwaltung/gefahr`).
- **Groups at a glance:** a picker of all groups on top, below it only the selected one as its own framed
  card – header with name, rename and delete, below that members, invitation links and "Next night" in
  separate sections. "New group" is an entry in the picker.

### Fixed
- "Not in a group yet" was still German in the English UI.

## 0.15.0 – 2026-10-06

### Added
- **First steps:** in their first 30 days, new people see a small checklist at the top of the movie-night
  page – reply for the next night, suggest a film, add streaming services, turn on notifications. Each item
  links straight there and checks itself off; once done or hidden, the card disappears (on all devices).
- **ⓘ explanations** for our own terms: suggestions and odds, veto, movie-night case and host – tap, read
  a sentence or two.

### Fixed
- "Open"/"Done" on the wishes page were still German in the English UI.

## 0.14.1 – 2026-10-06

### Fixed
- **Phones in portrait:** on narrow screens the content was cut off on the right (e.g. "Withdraw"/"Veto"
  and the case on the movie-night page), because long provider chips like "Amazon Prime Video · Alice,
  Bob" made the single-column view wider than the screen. Columns now adapt and long chips are truncated.
  Tested with Safari's engine at 390 px (iPhone 13) and 320 px (display zoom).
- The tabs in "Our films" and the header (on very narrow displays only the profile picture) fit at 320 px
  width too.

## 0.14.0 – 2026-10-06

### Changed
- **Only one card on movie night:** on the day of the date, evening mode replaces the planning card
  instead of showing both "Tonight" and "Today". Replies ("I'm here", "Can't make it") sit in the "Who's
  here?" step, Invite is top right, change date, calendar and host baton are behind "⋯".
- **The header knows the time:** before, "Tonight · 20:00 · in 2 hours"; from the start, "● Running since
  20:00". Once the film is logged as watched, planning for the next night comes back.

### Added
- **"Starting soon":** five minutes before the start, everyone who said yes or maybe and doesn't have
  screenmates open gets a notification – even with the app closed, if notifications are on for the device
  (setting "Reminders on movie-night day").

## 0.13.1 – 2026-10-06

### Changed
- **Evening mode:** if nothing has been suggested on movie night, a **Find films** button in the "What are
  we watching?" step leads straight to Find.
- **Case without a host:** non-hosts now see who opens the case in the "What are we watching?" step. If the
  host isn't around (or nobody holds the baton), it's one click: **Take the baton & open the case**. If the
  host is there, "Take over yourself?" starts the short vote.

### Fixed
- The welcome could reopen right away when an older server response arrived late.

## 0.13.0 – 2026-10-06

### Added
- **English throughout, stage 2:** what the server writes now also comes in the app's language – error
  messages, awards (names, descriptions, level titles), shelves in Find, the facts in the sidebar, the
  notification choices, the AI's reasoning and the roles in film details.
- **For everyone in their own language:** push messages, bell entries and the calendar feed follow the
  language of the person receiving them (date and time included).
- Also translated now: admin area, groups, invitation links, AI usage, the danger zone (confirm with
  "LÖSCHEN" or "DELETE") and the about page.

### Notes
- Film data (titles, descriptions, genres) follows the server's `TMDB_LANGUAGE`; texts that admins write
  themselves (house rules, imprint) and notifications already sent stay as they are.

## 0.12.0 – 2026-10-06

### Added
- **German and English:** screenmates now speaks both languages. New people first choose **language and
  color theme** in the welcome; later both live under Settings → Appearance. The language belongs to the
  profile and applies on all devices; before signing in, the browser language decides (switchable on the
  invitation page).
- All main pages are translated: movie night (including case, host baton, date planning, invitation),
  Find, Our films with year in review, cinema, profile, awards, settings, news and wishes. Date, time and
  numbers follow the language.

### Notes
- Still German at this stage (next step): texts from the server (award catalog, shelf names, sidebar facts,
  push messages, error messages), admin area, danger zone and the about page.

## 0.11.2 – 2026-10-06

### Changed
- **Compact Find:** below the search there is just one bar – Browse/All films, **"Where's it on?"**
  (services, "Streams for us" and "Free" in one menu, the button shows the choice) and **Genre** (chips in
  the menu, the button shows e.g. "Horror, Thriller"), plus filters, sorting and the result count. Films
  start much higher up as a result.
- **"Back to top":** far down a list, a button appears bottom right that takes you back to the start.

## 0.11.1 – 2026-10-06

### Fixed
- **After "Start over" (danger zone) the case no longer opened.** Every browser remembered the number of
  the last reveal shown and only showed higher ones – but after clearing, the numbers start at 1 again. It
  now remembers the start time, which always increases.
- **Case sound on iPhone:** "Test spin", "Open for everyone" and evening mode unlock audio directly in your
  own click (iOS only allows sound to start then); the general unlock reacts to release and click instead
  of touch. The saved sound setting starts over once at "on", because the old bug may have switched it to
  "off" unintentionally.

## 0.11.0 – 2026-10-06

**Tidied up:** the movie-night page is split into clear parts, news has its own page, and in the cinema
picture and chat own the stage again.

### Changed
- **Movie night in three parts:** at the top the next night (date, who's in, your reply), below it, set
  apart, **"What are we watching?"** with suggestions and the case, and at the very bottom as a footer the
  house rules & info (and "On this day").
- **News** as its own page behind the bell: "For you" (your notifications) and "In the group" (the activity,
  with what's new since your last visit marked). The activity has left the movie-night page for it.
- **Streaming in the cinema slimmed down:** one row with "What's on?", film, source and start; quality,
  content and audio under "Settings", the OBS guide only for OBS. While streaming, only "live", pause and
  end.
- **The film from the case goes to the cinema:** once the case has drawn and nothing is set in the cinema,
  the film of the night is already in the program ("from the case").
- **Cinema on phones:** the control bar and close button appear on tap and fade out after three seconds;
  in iPhone fullscreen there is only one close button (top right).

### Fixed
- **No case sound on iPhone:** Safari only plays audio that was unlocked during a tap. Audio is now unlocked
  on the first tap anywhere in the app and reused, plays even with the silent switch on, and the speaker
  icon brings back blocked audio ("Tap for sound") instead of muting it.

## 0.10.2 – 2026-10-06

### Changed
- **The case no longer jumps:** the film reel stays in exactly the same spot in the middle of the screen
  during countdown, spin and reveal; whatever appears below (hint, "Skip", the winner with "Next") only
  grows downward.
- Flying reactions in the cinema now always show who sent them – before, only in fullscreen.
- The streaming panel correctly says where the stream comes from: "You're live", "You're streaming from
  another device", "Lena is streaming from the browser" or "Live via OBS". Before, everything not from this
  browser was labeled "via OBS".
- iPhone fullscreen in portrait: a dedicated close button top right is always clear (the reaction buttons
  used to cover the ✕). On touch devices the control bar wraps and the volume slider is dropped (iOS
  ignores it; the device buttons set the volume).

## 0.10.1 – 2026-10-06

### Fixed
- **House rules & info** looked broken (narrow pill, text overflowing): the new hints on the suggestions
  shared an internal name with the info card and gave it their shape.
- **Cinema dropouts in picture and sound:** the media server dropped incoming packets because the UDP
  receive buffer (Linux default 208 KB) overflowed on 1080p keyframes. MediaMTX can now be given a larger
  buffer with `MTX_UDPREADBUFFERSIZE` (README → Cinema); 8 MB in production.
- **Fullscreen on iPhone:** Safari can only show its own video player fullscreen there. The cinema picture
  now covers the whole screen itself – in the home-screen app just like real fullscreen, with reactions,
  pause and chat overlays. Double-tapping no longer zooms the page.
- The cinema's query to the media server no longer produces "path not found" in its log when nothing is
  running (thousands of lines a day, burying real warnings).

## 0.10.0 – 2026-10-06

**The whole evening, not just the planning:** screenmates now guides through the night itself, asks for
stars the day after, and helps choose with what the group likes and what's streaming where.

### Added
- **Evening mode:** on the day of the date, three steps at the top of the movie-night page guide through
  the night – *Who's here?* → *What are we watching?* (open the case for everyone) → *Roll film!* (to the
  cinema, or "Watched – log it" with everyone who said yes).
- **"How was it?":** films from the last few days that you attended but haven't rated yet appear at the top
  with stars to tap. The day after (10:00–20:00) a notification reminds you once.
- **For you ≈ 4.2 ★:** every suggestion shows how much the group is likely to enjoy it – with replies, for
  those who are in. Anyone who already rated the film counts with their real stars, the others with their
  prediction ("Who'll like it?"). Hover to see it per person.
- **Streaming on:** every suggestion shows the best way to watch – first a subscription in the group
  ("Netflix · Lena"), otherwise free, subscription, rent or buy.
- **The case odds sit on each suggestion** (in the rarity color). The case itself is now just the card
  with the button; its list only appears when it draws from the watchlist.
- **Welcome:** newcomers see three short cards once (Suggest → Case → Watch & rate) and can add their
  streaming services right away.
- **New since your last visit:** the activity feed marks what's new and collapses the rest.
- **The bell:** all notifications (date, poll, case, cinema, baton, replies, "How was it?") also live in
  the app, with an unread counter – even without push. They're kept for 30 days.
- **Kindred tastes** on the profile: "Lena ticks 87 % like you", from at least three films rated in
  common. Other people's profiles show how close you are to them.
- **Cinema:** the host can call a **pause** ("Short break – back in a moment" with a clock over the
  picture), viewers send **"Hang on, be right back"** into the picture.

### Fixed
- Under load (several cinema viewers, live updates, video encoding) the database connections could run
  out, because requests waiting on MediaMTX, TMDB or the AI held on to their connection. They now return
  it beforehand, and the pool is larger. This was probably also the cause of the occasionally red `docker`
  CI job.
- The prediction now trains a person's model only once and uses it for any number of films.

### Operations
- Migration `0012`: table `benachrichtigung` (the bell, 30 days).
- New push type `bewerten` (Settings → Notifications).

## 0.9.2 – 2026-10-06

### Added
- **Danger zone** in the admin area (server admins only): clear history, movie night, cinema chat, wishes,
  awards, and statistics & AI log individually – or **"Start over"**: additionally removes all other
  names, invitations and requests; the admin, the groups, the film catalog, the about page and the settings
  remain. You type "LÖSCHEN" first, and the server backs up the database
  (`backup-vor-reset-<time>.db` next to the database, the last five are kept).

### Changed
- **Cinema rearranged:** the chat sits to the right of the picture for everyone – the host too – with a
  fixed height to scroll. "Stream" now sits wide below the picture.
- **Cinema chat is kept for 30 days:** messages are stored (before, only in memory and gone after a
  restart) and age out after 30 days. Older messages can be loaded, day separators show when something was
  written. Reactions remain a moment in the picture.
- **Movie-night page tidied up:** planning is one row – date, who's in, your reply, invite. It only
  expands by itself when something is waiting for you (no reply yet, a poll to vote on or decide);
  otherwise via "Planning". On the day itself it says "Today".
- When a new date is set after a past night, replies start from scratch (before, "In: …" from last time
  simply stayed).
- **Case for everyone:** the transition from countdown to spin is now one motion. The reel starts moving
  slowly during the countdown and accelerates smoothly; the countdown fades out instead of vanishing.

### Fixed
- The case stuttered while spinning: the start time was recalculated from the server clock on every live
  poll and wobbled with the network. It is now fixed at opening, and clock sync uses the fastest
  measurement.
- **Push messages didn't arrive.** The contact address for the push services
  (`https://github.com/marcmeier/screenmates`) had a path, which the signature doesn't allow – every
  delivery failed. Now only the origin is sent (`https://github.com`), likewise for a custom `PUSH_KONTAKT`
  address. A test now really signs and encrypts.
- **"Send test"** waits for the push service's answer and reports whether the message was really
  delivered (before, it said "sent" as soon as it was queued).
- If the browser can't find its push service (Brave without Google push, Chromium builds without Google
  services), screenmates now explains what to do instead of "Registration failed".

### Operations
- Migration `0011`: table `kinonachricht` (cinema chat, 30 days).

## 0.9.0 – 2026-10-06

**Plan together, remember together:** the group finds the date by poll, everyone replies yes, maybe or no,
and the night lands in the calendar. screenmates now reaches you with the app closed, the cinema chats and
screams, and at the end of the year there's the year in review.

### Added
- **Date poll.** Instead of a fixed date, propose several ("Vote" next to the date); everyone answers each
  date with Yes, Maybe or No, the favorite is marked. Whoever decides sets the date, and the answers become
  replies for the night. Deciding is up to whoever started the poll, the host or an admin – or anyone, as
  long as nobody holds the baton. Proposals show up in the activity feed.
- **In, maybe, can't make it.** Besides "I'm in!" there is "Maybe" and "Can't make it"; who replied how
  shows below the attendee chips.
- **Calendar.** "Calendar" next to the date downloads the night as an `.ics` file (with location, the films
  up for choice, and a reminder two hours before). Settings offer a **calendar subscription** with the next
  dates of all your groups; if a date moves, the calendar follows. The link is personal and can be renewed
  or turned off.
- **Notifications (Web Push)** to phone and computer, even with the app closed: new or moved date, new date
  poll, a reminder on movie-night day (three hours before, not for those who declined), the case opens, the
  cinema is live, the host baton is offered to you, someone replies to your comment. Turned on per device,
  chosen per person, test message included. Things happening live only go to people who don't have the app
  open. On iPhone and iPad in the home-screen app.
- **Cinema chat and reactions.** Next to the picture, a chat for everyone currently in the cinema, and
  reactions (😂 😱 ❤️ 👏 🍿 🔥 😴 🤯) that fly across the picture for everyone. In fullscreen, new messages
  appear right in the picture, reactions go via the control bar.
- **Year in review** under "Our films": the group's film year – films, nights, hours, genres, best, most
  divisive and most unanimous film, records (weeks in a row, favorite day) and awards like "Regular",
  "Harshest critic" or "Heartbreaker". Plus a **story** to tap through. In December and January the home
  page points to it.
- **New awards:** 🤞 "Kept your word" (said yes and showed up, three tiers), 🗓️ "Date finder" (your poll date
  was chosen and the night happened) and a secret one.
- Sidebar statistics now also count cinema chat messages and reactions.
- New screenshots in the README.

### Fixed
- The changelog listed 0.7.0 and 0.8.0 with the wrong date.
- Two award tests failed when run after midnight (the test nights unlocked "Night owl" along the way).

### Operations
- Migration `0010`: tables `terminvorschlag`, `terminstimme`, `pushabo`; `mitglied.rueckmeldung`,
  `user.kalender`, `user.push`, `abend.erinnert`, `appmeta.vapid`.
- New dependency `pywebpush`. screenmates generates the VAPID keys on first use and stores them in the
  database (back it up!). `PUSH_KONTAKT` is optional. Push requires HTTPS.
- Newly reachable without sign-in: `/api/kalender/<token>.ics` (the token is the key).
- A background task checks every minute whether a reminder is due.
- Cinema chat and reactions live only in memory (the last 200, at most 6 hours) and don't trigger a reload
  in the other apps.
- A service worker (`/sw.js`) shows the notifications; it caches nothing.

## 0.8.0 – 2026-10-05

**The host baton:** who runs the night is now a role that moves – hand it over, take it over, vote. So even
without an admin someone can open the case for everyone and run the cinema.

### Added
- **Host baton.** One person per group holds it: they open the case for everyone and run the cinema (screen
  sharing, program, ending the show, a **personal OBS key** that only works with the baton). Group admins
  can still do everything.
  - Whoever sets a new date gets the baton if nobody currently holds it or the last night is over. Moving
    the date takes it from nobody.
  - **Hand over:** the host offers the baton to someone – accept or decline.
  - **Take over:** if the host isn't around (no app open for a minute) or there is none, you simply take
    the baton. If they're around, those present vote for 60 seconds: the host's vote counts double, their
    yes decides at once, more yes than no wins, and without objection silence counts as consent. Once the
    result is certain, the vote ends immediately. Whoever loses waits five minutes.
  - A stream running during a handover keeps running; the new host can end it and stream themselves.
  - Offers and votes appear everywhere in the app; handovers show up in the activity feed.
- **Behind the scenes:** between the sidebar statistics, what's being prepared flashes up – "Popping the
  popcorn …", "Shooing pigeons off the data line …" and more.
- **Support via Ko-fi and PayPal.** Admins enter their Ko-fi and PayPal.me names on the about page (or just
  paste the link). Each gets a button and, on desktop, a QR code to scan with a phone – generated in the
  browser, without a third-party service. Only the name is stored; only ko-fi.com and paypal.me are linked.
- New screenshots in the README.

### Fixed
- The profile page showed the "Awards" heading twice.
- Statistics: "1 group" instead of "1 groups" (singular for every number).
- The font picker shows each font in its own typeface right away, not only on hover.

### Operations
- Migration `0009`: `abend.gastgeber_id` (prefilled with whoever set the date), table `stabwechsel`,
  `user.obs_key`. Streaming, program and ending the show now check "host or group admin".

## 0.7.0 – 2026-10-05

**Together instead of side by side:** the host opens the movie-night case and everyone watches live,
friends' changes appear without reloading, and you only get in with an invitation link. Plus a profile with
awards and your own color theme, a tidier admin area with AI costs, statistics in the sidebar and an about
page with an imprint.

### Added
- **Open the case for everyone.** The host of the night (whoever set the date) or a group admin opens the
  movie-night case for everyone: anyone with screenmates open – on any page – sees the same reveal after a
  short countdown, with the same reel and the same winner, at the same time. Latecomers join midway. The
  winner stays as **"Film of the night"** until it's watched (or the host takes it back) and appears in the
  activity feed. The server draws the winner. Everyone else can still **test spin** – clearly marked as a
  test, doesn't count.
- **Live updates.** When someone rates, comments, saves or suggests something, the others see it
  immediately – without reloading. In a background tab screenmates polls less often.
- **Comments with replies stay as placeholders.** Deleting a comment that already has replies leaves
  "Deleted by the author" (or "Removed by an admin") – the replies keep their context. Without replies it
  disappears as before; when the last reply goes, the empty placeholder goes too.
- **Profile & awards in one place.** The profile button leads to your profile with level, awards and
  showcase; your settings live there too. Old links (`#/erfolge`, `#/einstellungen`) keep working.
- **Appearance: color theme and font.** Seven dark color themes (Cinema, Night, Neon, Forest, Amber,
  Violet, Black) and seven fonts, including an especially legible one. Applies only to you, on all your
  devices.
- **Admin area as its own section**, visible only to admins: groups and invitations, requests, users,
  catalog – separate from your own profile.
- **AI usage in the admin area:** requests, failures, tokens and cost (OpenRouter reports it in US dollars)
  – today, 7 and 30 days, total, per person and the latest requests.
- **Statistics in the sidebar** instead of the catalog count: rotating, e.g. how many films were watched
  together, hearts given, cases opened, how much was streamed in the cinema and how many packets were lost
  doing it. Only totals, never anything about individuals.
- **About screenmates** with version, source link and the sections **Support**, **Imprint** and
  **Privacy**, which admins write right on the page (Markdown). The page is reachable without an
  invitation; empty sections are hidden.
- **Invitation links instead of an access question.** A shared film question doesn't fit when one server
  hosts several groups without shared memories. Now it's invite-only. Group admins create links for their
  group – "add directly" or "with approval", with expiry and usage limit, revocable, to copy or share.
  Opening the link leads straight to choosing a name for that group; people who already have a name join
  with the link (or ask to). The group's admins decide requests and join requests – no server admin
  needed. Emergency exit: `python -m app.cli einladung`.
- **Phone: profile menu.** The profile button top right opens a menu with profile & awards (including
  level), settings, wishes & ideas, admin, about and sign out – on phones, awards and wishes weren't
  reachable at all before.

### Fixed
- The case animation now measures the width every frame – before, the marker could land next to the
  winner if the stage wasn't fully laid out at start.

### Removed
- The access question (replaced by invitations). Whoever is in stays in.

### Operations
- Migration `0007`: tables `einladung`, `beitrittsanfrage`; `session.einladung_id`,
  `user.antrag_gruppe_id`; table `zugang` is dropped. Afterwards create and send invitation links under
  Admin → Groups.
- Migration `0008`: tables `kistenoeffnung`, `kianfrage`, `zaehler`, `seitentext`;
  `watchednote.geloescht`, `user.design`.
- Live updates: every open app polls `GET /api/live` every 1.5 s (every 15 s in the background) – a small
  response, no WebSocket needed, works through any proxy.
- With the cinema enabled, a background task tallies traffic and lost packets of the MediaMTX sessions
  every 15 s (`/v3/webrtcsessions/list`). Whatever ran before the update isn't counted.
- Enter imprint and privacy under About → Edit if needed.

## 0.6.0 – 2026-10-05

**For your group – or several:** screenmates can sit behind an access question, new people request their
name, admins manage profiles, and one server hosts several independent circles of friends with their own
movie night and their own cinema. Plus awards with levels and a showcase, profile pictures, all genres
instead of just horror, and an AI search that runs cheaply with OpenRouter.

### Added
- **Groups: several independent circles of friends on one server.** Each group has its own movie night
  (who's in, suggestions, veto, case, date, info), its history with ratings and guestbook, its watchlist,
  its activity feed and **its own cinema** – several groups can stream at once. Only members can see it.
  Names, admins, profile pictures, levels and awards still apply server-wide. Server admins create groups
  and appoint group admins, who add people and do on movie night what was previously reserved for admins.
  People in several groups switch in the sidebar. With only one group, approved names land in it
  automatically. Everything so far lives in "Our group".
- **Awards** modeled on Xbox and Steam: 32 awards in Bronze, Silver, Gold and Platinum for movie nights,
  reviews, guestbook, dates, cinema and profile, plus six secret ones. Points add up to a level with a
  title, shown as a badge on every avatar. New awards appear as a pop-up and in the activity feed; everyone
  has a profile with a showcase for up to three awards. Rarity and progress like Steam, but no leaderboard.
  **Gaming it doesn't pay:** points only come from awards, liking and voting are never rewarded (only
  hearts *from different other people*), a movie night only counts once another attendee confirms it, and
  backdated entries don't count. What existed before the launch counts retroactively. All rules:
  [`docs/AWARDS.md`](docs/AWARDS.md).
- **Profile pictures.** Upload your own picture in settings; it replaces the initials everywhere. The
  browser shrinks phone photos before upload, the server crops them square (256 px, WebP) and re-encodes
  them – location data and other photo metadata are not kept. Admins can remove other people's pictures.
- **Access question: screenmates just for your group.** Admins set a question, e.g. "Which film did we
  watch together first?". Whoever opens the app has to click the right film first – nothing is visible
  before that, not even through the API. Failed attempts are throttled per IP. People already signed in
  don't notice a thing.
- **Request names, admins approve.** New people file a request behind the access question; admins see
  open requests as a count in the navigation and approve or reject.
- **Admins instead of a host film.** Admin is now a right of a person, no longer a shared film anyone might
  know. Admins appoint further admins; the last one can be neither deleted nor demoted. The first name of
  a new installation becomes admin; existing installations get their first admin with
  `python -m app.cli admin "<name>"`.
- **User management** in settings: rename, change color, grant or revoke admin, reset film password, sign
  out on all devices, delete – showing on how many devices someone is signed in.
- **Favicon** in the style of the collapsed sidebar ("sm"), plus home-screen icons for iPhone and Android
  (`apple-touch-icon`, web manifest).
- **AI search via OpenRouter.** Instead of an Anthropic key, an OpenRouter key (`sk-or-…`, detected
  automatically) works too – and with it any model there. The default is the inexpensive
  `deepseek/deepseek-v4.1-flash` (around 0.12 cents per search); every suggestion is checked against TMDB
  anyway. "Thinking" (reasoning) is turned off: with reasoning models it used up the whole answer budget
  before the list came – without it, search is faster, cheaper and reliable. AI errors are reported clearly
  (key rejected, credit exhausted, overloaded, truncated).
- **All genres instead of just horror.** Find, browse, search, people and AI search now cover every film.
  Horror is one genre among many and has its own shelf – right at the front.
- **Genre shelves** when browsing: horror, comedy, thriller, action, science fiction, drama, animation,
  documentary. The service shelves show the whole catalog.
- **Filmographies** show all of a person's films, optionally filtered by genre.
- Only films that have already been released are shown. For large result sets it says "More than 10,000
  films", because TMDB doesn't return more.
- "Hidden gems" retuned on real data: across all genres, films with a small, enthusiastic fan base crowded
  out everything else. Now at least two years old and in widely spoken original languages (e.g.
  *Harakiri*, *Seven Samurai*, *Cinema Paradiso*).

### Removed
- Host mode with a host film and `Ctrl+Shift+H` (replaced by admins).

### Fixed
- **Films from the starter catalog never got a poster** (e.g. Scream, Hereditary, The Shining, Midsommar):
  the detail view only completed films without a runtime, but the starter catalog has one. With a TMDB key
  it now fetches missing posters once too.
- **The sidebar no longer jumps when collapsing and expanding:** logo, group, navigation and profile keep
  their height; collapsed, the group shows its initials.
- **The cinema picture has a fixed size:** at most 1280 px wide and always small enough to fit the window
  together with the title row – on large monitors you had to scroll before. Full width on phones,
  fullscreen as before.
- **With TMDB, grids and search ended after 20 films**, although Netflix has e.g. 320 horror films: TMDB
  returns 20 films per page, the app asked for 24 and took "fewer than requested" as the end. Now the server
  reports whether there's more and how many there are in total.

### Improved
- Grids load more on scroll by themselves ("Load more" stays as a button), and "All films" shows the total
  ("320 films").

### Operations
- **Six migrations** (`0003`–`0006`) run automatically at startup: access question and per-person admins,
  profile pictures, awards, groups. Everything so far lands in "Our group"; whoever was signed in stays
  signed in.
- **First admin** of an existing installation: `python -m app.cli admin "<name>"` (in the container).
  `python -m app.cli namen` lists all names, `zugang-aus` lifts the access question.
- **Behind a reverse proxy** set `FORWARDED_ALLOW_IPS` (proxy IP, possibly Cloudflare ranges), so the
  access question's throttle sees the real client IP.
- **Profile pictures** live under `MEDIA_DIR` (Docker: `/data/media`, in the same volume as the database –
  include it in backups). New dependency: Pillow.
- **MediaMTX:** one path per group (`kino-<id>`, regex in `deploy/mediamtx.yml`) – restart the media server
  with the new configuration after the update.

### Tests
- 183 backend tests, 40 browser tests (also against the Docker stack). New among others: all of the awards'
  anti-gaming rules, access question including throttling, per-person and per-group permissions, profile
  picture processing (EXIF/GPS stripped, decompression-bomb protection), cinema per group, migrations from a
  real starting state.
- The invitation card gets 15 instead of 5 seconds to render in the browser test (occasional timing
  outlier on busy machines).

## 0.5.0 – 2026-10-03

**Browse, draw, invite:** "Find" shows what's on Netflix, Prime & co. in shelves, the movie-night case
replaces the wheel of fortune, and the night gets a date, an invitation card and reminders. Plus
screenmates estimates who will like a film – honestly measured.

### Added
- **Browse instead of having to search:** "Find" starts with shelves like a streaming service: "Streams for
  us" (your subscriptions), one shelf per service (Netflix, Prime Video, Disney+, Paramount+ … yours first,
  marked "Your subscription"), "Stream for free", "Just released", "Hidden gems" and "Classics". Swipe or
  page sideways; "Show all" opens the whole catalog as a grid.
- **"All films" with a service picker:** logos to filter by a service, plus "Free" and "Streams for us".
  The chosen view is remembered.
- **Movie-night case instead of a wheel of fortune**, like opening a case in Counter-Strike 2: a reel of
  posters races under the marker, slows down for a long time and reveals the film of the night. The
  **rarity colors** (Standard, Limited, Secret, Covert, ★ Legendary) reflect the real odds, and the case
  contents list them in percent. With click sounds and a fanfare (can be turned off), near misses, "Skip"
  (also Escape) and a short animation with "reduced motion".
- **"Who'll like it?"** in every film view: estimated stars per person from their own ratings, with a
  reason ("like Friday the 13th, ★ 5"). From 8 ratings on, up to 25 as a "first tendency". In the backtest
  up to 20 % more accurate than the person's average. What the prediction can and can't do is in
  [`docs/PREDICTION.md`](docs/PREDICTION.md).
- **Date and invitation:** date and place for the next night. "Invite" creates a card as an image (date,
  posters of the suggestions without a veto, who's in) and a text with a link. On phones both go straight
  to the share menu, otherwise save the image and copy the text.
- **"On this day":** the movie night shows what you watched around this date in earlier years, with your
  stars and the most popular comment.

### Operations
- First real migration (`0002`): table `abend` and column `movie.keywords`. The prediction gradually
  fetches missing keywords of older films from TMDB (at most 30 per request).
- `scripts/prognose-backtest.py` measures the prediction on real TMDB films.

### Tests
- 110 backend tests, 34 browser tests (also against the Docker stack and in UTC). New checks were each
  verified against deliberately introduced bugs; shelves and prediction additionally with real TMDB data,
  the migration on a copy of a real database.

## 0.4.0 – 2026-10-03

**Movie night gets personal:** where is the film streaming, who has which subscription, who thought what
of it – and who definitely doesn't want to see it. Plus a database that survives future updates without
data loss.

### Added
- **Collapsible sidebar:** icons only (with tooltips, short logo "sm", live counter on the cinema icon),
  remembered per device. Unchanged on phones.
- **Rate and comment directly in the detail view** of every watched film – no longer only under Our films →
  Watched. Plus the group average "You: ★ 4.7" next to the TMDB score.
- **"Where's it on?"** in every film view: subscription, free, rent, buy (data: JustWatch via TMDB).
  Subscriptions someone in the group has come first – with names.
- **My subscriptions** in settings (real subscription services only, no rental shops) and the filter
  **"Streams for us"** in Find. "Prime Video with ads" counts as Prime Video.
- **Trailer** in the detail view, preferring the configured language; YouTube (nocookie) only loads on
  click.
- **Veto:** everyone can reject one suggested film; the wheel leaves it out. Vetoes expire when the film
  is watched or the suggestions are cleared.

### Operations
- **Database migrations with Alembic.** The app brings the database up to date by itself at startup.
  Databases from 0.2/0.3 are taken over without data loss (missing tables are added). Future schema
  changes: `make migration name="…"`. A test fails if a model was changed but no migration written.
  Migrations run with foreign keys off, so a table rebuild under SQLite doesn't trigger cascades.

### Fixed
- Ratings and comments from one view only appeared in other open views after reloading.
- Escape no longer closed a dialog when focus fell out of it after an action.
- Ratings everywhere with a German decimal comma (4,7 instead of 4.7) in the German UI.

### Tests
- 92 backend tests, 28 browser tests (also against the full Docker stack). Providers and trailers
  additionally checked with real TMDB data, the migration on a copy of a real database.

## 0.3.0 – 2026-10-03

The **cinema**: watch live together, even when everyone is somewhere else.

### Added
- **Cinema** as its own section: the host shares a browser tab (or streams via WHIP from OBS), everyone
  sees the same picture live over WebRTC. The MediaMTX media server distributes; screenmates checks
  permissions and only relays the connection negotiation.
- "Cinema" menu item with a live indicator and viewer count, a "Now in the cinema" banner on the movie
  night, and after the show the film can be logged as watched with all viewers.
- Streaming panel with **quality** (High 1080p / Medium 720p / Economy 480p) and **content** (film / game
  up to 60 fps), plus a live readout of the actual streaming values.
- **Navigation in three sections** instead of ten items: Movie night · Find · Our films (plus Cinema). One
  search field for discovery, titles, people and AI. Old links redirect.
- Inter font, shipped with our own build.

### Improved (all measured, details in [`docs/CINEMA-QUALITY.md`](docs/CINEMA-QUALITY.md))
- **Picture:** 1080p from the first second instead of 480×270 for the first ~15 s – maintain resolution,
  start bitrate, H.264 instead of VP8.
- **Audio:** stereo at up to 192 kbit/s instead of mono at ~32 kbit/s (sender *and* viewer request stereo,
  otherwise Chrome downmixes).
- **Smoothness:** a 300 ms playback buffer at the viewer – largest deviation from the capture cadence
  65 → 24 ms.
- People search: people with a horror connection first; filmographies without documentary appearances,
  best-known films first.
- Discovery and TMDB sync: feature films of 60+ minutes only, "Top rated" only from 200 votes.

### Fixed
- Senders like OBS/FFmpeg dropped randomly when MediaMTX listed an ICE-TCP candidate first – they now only
  get UDP candidates.
- Some wheel-of-fortune labels were upside down.

### Operations & tests
- `make kino-install`, MediaMTX in `compose.yaml`; new table, existing databases stay valid.
- A CI job that starts the full `docker compose` stack and runs all E2E tests against it.
- 69 backend tests, 23 browser tests – including the cinema with a real media server, an OBS stand-in via
  FFmpeg, TCP fallback with UDP blocked, and stereo via frequency analysis.

### Not yet verified in real use
- Watching over the internet (checklist: [`docs/CINEMA-CHECKLIST.md`](docs/CINEMA-CHECKLIST.md)).
- Real OBS as a sender.

## 0.2.0 – 2026-10-03

A thorough review of the first version, with every finding fixed and covered by a test.

- Permission model (a name to write, the host to manage); protection and host films are never exposed;
  throttling against guessing.
- Schema with cascades and unique constraints, a schema version, validation everywhere.
- TMDB results with posters, a robust client; AI search via the Anthropic API.
- New frontend with all sections, error messages, keyboard support, mobile view.
- Tests, lint, CI, Docker.

## 0.1.0 – 2026-10-03

First working version (MVP): catalog, search, watchlist, watched, wishes, info, choosing a name.
