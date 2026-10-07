# Open work

Things that are known and planned, but not done yet. Bigger items get an issue when someone starts on them.

## English names in the code

The repository is English, much of the code isn't. The public interfaces (environment variables, the
command line, the language header) are English since 1.0, with the old names still accepted. The rest
follows module by module, each step with its own pull request and tests:

1. Backend modules and routers: `abend` → `evening`, `kiste` → `case`, `gastgeber` → `host`,
   `kino`/`kinochat` → `cinema`/`cinema_chat`, `erfolge` → `awards`, `umfrage` → `date_poll`,
   `rueckblick` → `year_review`, `zugang` → `door`, `einladungen` → `invitations`, `gruppen` → `groups`,
   `glocke` → `bell`, `statistik` → `stats`, `ueber` → `about`, `sprache` → `language`,
   `prognose` → `prediction`, `bilder` → `pictures`, `ki` → `ai_search`.
2. Model classes and columns (`Gruppe`, `Mitglied`, `Einladung`, `Abend`, `Erfolg` …). Needs migrations
   that rename tables and columns; SQLite batch mode can do that without losing data.
3. API paths and JSON fields (`/api/kiste`, `termin`, `dabei` …). This breaks clients, so: new English
   paths next to the old ones for one release, then remove the old ones in the next major version.
4. Frontend components, stores and i18n keys (`AbendTab.vue`, `useKiste`, `namen.*` …), and the
   server-side translation table (German source texts in `texte_en.py` → message keys).

## Other

- Live updates: for 2.5 s after its own change, a page takes every change as its own, so a friend's
  change in that moment only shows with the next one. The server could return the new counters with
  every write instead.
- The backend tests take about six minutes because every test migrates a fresh database from scratch.
  Migrating once and copying the file per test would make them several times faster.
