# Security policy

## Supported versions

screenmates is released continuously. Security fixes land in the latest release only – please keep
your installation up to date.

| Version | Supported |
|---|---|
| latest release | ✅ |
| older releases | ❌ |

## Reporting a vulnerability

**Please do not report security issues in public issues, discussions or pull requests.**

Report them privately through GitHub's
[private vulnerability reporting](https://github.com/marcmeier/screenmates/security/advisories/new).
Please include:

- a description of the issue and its impact,
- steps to reproduce (or a proof of concept),
- the affected version (shown on the app's about page).

You can expect an acknowledgement within a few days. Once the issue is confirmed, a fix is prepared and
released, and you'll be credited in the advisory unless you prefer otherwise.

## Hardening your installation

- Serve screenmates over **HTTPS** and set `COOKIE_SECURE=true`.
- Behind a reverse proxy, set `FORWARDED_ALLOW_IPS` to the proxy's address so rate limits see real
  client IPs.
- Keep the MediaMTX HTTP ports (8889, 9997) internal – only the WebRTC media port 8189 needs to be
  public. The provided `compose.yaml` already does this.
- Back up the data volume (database, VAPID keys, profile pictures) regularly.
