# Cinema – checklist for a real-world test

What can't be tested automatically: real OBS, and friends watching over the internet. This list
takes about 15 minutes. Everything else – browser streaming, an OBS-like WHIP sender, viewers with
audio, TCP fallback – is covered by the E2E suite in CI.

## 1. OBS (on the streaming computer)

1. In screenmates, as an admin of the group (or holder of the host baton): **Cinema** → tab **OBS**.
2. OBS ≥ 30 → *Settings → Stream*: service **WHIP**, paste server and bearer token from screenmates.
3. *Settings → Output* ("Advanced" mode): keyframe interval **1 s**, **B-frames 0**
   (for x264 under "x264 options": `bframes=0`).
4. A scene with motion and sound, then **Start Streaming**. For films, add the file as a
   **Media Source** (don't capture the screen): that gives an even 24 fps without the screen's
   3:2 judder.

Check:

- [ ] screenmates shows "Live via OBS" to the streamer, and "Cinema" lights up in the menu.
- [ ] A second device on the same network watches: smooth picture, sound after "Sound on".
- [ ] Latency: compare a clock in the picture – should be under 1 second.
- [ ] Optional: set B-frames to 2 and restart. Does the picture stutter or jump?
      (Please note the result – this couldn't be reproduced without OBS.)
- [ ] **Stop Streaming** in OBS → after a few seconds screenmates shows "Nothing showing right now."
- [ ] Start again, then **End stream** in screenmates → OBS reports the disconnect.

## 2. Over the internet

Prerequisite: screenmates is publicly reachable (server, port forwarding or Tailscale),
port **8189** UDP+TCP is open, and `CINEMA_PUBLIC_HOST` is set.

- [ ] Someone **outside** your network (mobile data is enough: turn off Wi-Fi on a phone) opens the
      page, picks a name and watches.
- [ ] In the viewer's browser under `chrome://webrtc-internals` (or `about:webrtc` in Firefox):
      the selected candidate pair goes to your public address on port 8189.
- [ ] Several viewers at once: is the server's upload enough? (~5 Mbit/s per person at 1080p)

If the mobile test fails: check port 8189 on the firewall/router and whether `CINEMA_PUBLIC_HOST`
is the address under which the server is reachable from outside.
