# Security

Only the latest release gets security fixes.

## Reporting

Please don't open public issues for security problems. Use GitHub's
[private vulnerability reporting](https://github.com/marcmeier/screenmates/security/advisories/new)
and include what you found, how to reproduce it, and the version (shown on the about page).

## Running it safely

- Serve it over HTTPS and set `COOKIE_SECURE=true`.
- Behind a reverse proxy, set `FORWARDED_ALLOW_IPS` so rate limiting sees real client IPs.
- Don't expose MediaMTX's HTTP ports (8889, 9997); only 8189 needs to be public. `compose.yaml`
  already does this.
- Back up the data volume (database, push keys, profile pictures).
