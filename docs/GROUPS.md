# Groups

One screenmates server can host several independent circles of friends. For example: group 1
with six people, group 2 with four – some in both, some in just one.

| Applies to … | What |
|---|---|
| the whole server | names, admins, profile pictures, devices and login codes, streaming subscriptions, levels and **awards**, wishes & ideas, the film catalog, AI search |
| one group | movie night (who's in, suggestions, vetoes, the case, date, info), history with ratings and guestbook, watchlist, activity feed, "On this day", **cinema** |

- **Members only** see a group's content – through the API as well (`401`/`409`/`404`).
- **Active group:** per browser session (`session.gruppe_id`), switched with the picker in the sidebar. Without a choice, the group with the lowest ID applies.
- **Roles:** server admins create, rename and delete groups and appoint group admins. Group admins add and remove people in *their* group, rename it, and hold the movie-night rights there (clear suggestions, reset attendance, edit info, manage watched entries, delete comments, stream in the cinema). Server admins have these rights in every group they belong to.
- **Invitations:** screenmates is invite-only. Group admins create links for their group under Admin → Groups:
  - **add directly** – whoever opens the link and creates a name is a member right away (for links you send personally),
  - **with approval** – the new name becomes a request to the admins of *this* group (e.g. for a group chat),
  - plus an expiry (1/7/30 days or never) and a usage limit; revocable at any time (people already in stay in).

  Someone who already has a name joins (or asks to join) another group with that group's link. Requests show up for each group's admins.
- **Without an invitation** (e.g. names created directly by an admin): if there is only one group, they land in it automatically; otherwise an admin decides.
- **Emergency exit:** `python -m app.cli einladung [<group>]` creates a one-time link (24 h, direct); `python -m app.cli login <name>` a login code for an existing name.
- **Cinema:** one per group, MediaMTX path `kino-<group id>` (regex path in `deploy/mediamtx.yml`), its own secret, its own OBS stream key (the key decides the group; the WHIP URL is the same for everyone), its own audience. Several groups can stream at once – mind your upload bandwidth.
- **Awards** count across all groups: a confirmed movie night is one night, no matter in which group (at most one per day).
- **Ratings stay in their group:** predictions ("Who will like it?"), the forecast for suggestions and taste matching only use the active group's members and evenings.
- **Under the hood:** `watched`, `wishlist`, `suggestion` and `veto` carry a `gruppe_id`; their uniqueness applies per group. `abend`, `info` and `kinostate` use the group ID as their ID. Migration `0006` created "Our group" (ID 1) with all existing data and approved names; former admins became its group admins.
