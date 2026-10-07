# Cinema – why these streaming settings

Measured on 2026-10-03 with a demanding 1080p test pattern (moving gradient, fine noise, small
text), a real MediaMTX and one viewer, using WebRTC statistics (`outbound-rtp` / `inbound-rtp`).
Resolution and bitrate as received by the viewer.

## Starting point (v0.3): blurry

VP8, `degradationPreference: maintain-framerate`, max. 6 Mbit/s, no start bitrate:

| after | Resolution | Bitrate | Limit reported by the browser |
|---|---|---|---|
| 3 s | **480×270** | 4.8 Mbit/s | bandwidth |
| 8 s | **640×360** | 5.2 Mbit/s | bandwidth |
| 15 s | 1920×1080 | 5.1 Mbit/s | none |

Chrome starts with a cautious bandwidth estimate and, with "maintain framerate", sacrifices
resolution – even though the bitrate is long sufficient. Every short dip repeats this.

## Comparison (same source, after 10 s)

| Variant | Viewer sees | Impression (crop at original size) |
|---|---|---|
| VP8, maintain framerate (old) | 640×360 | tiny, blurry |
| VP8, maintain resolution, 6 M | 1920×1080 | sharp text, blocking around fine dots |
| VP9, maintain resolution, 8 M | 1920×1080 reported | **black picture** for the viewer |
| **H.264, maintain resolution, 8 M, start 4 M** | 1920×1080 | **clean and sharp** |
| AV1, maintain resolution, 8 M | 1920×1080 | about as good as H.264 |
| VP8, balanced, 10 M | 480×270 → 960×540, 15 fps | poor |

Start bitrate (Chrome hint `x-google-start-bitrate` in the SDP): with it, 1080p from the first
second; without it, the first seconds run at 15 fps with a coarser picture.

## Decision

- **Prefer H.264** (cleanest picture, every device decodes it, iPhones in hardware),
  VP8 as fallback, VP9 last.
- **Start bitrate** matched to the quality level.
- **Film**: maintain resolution. **Game**: maintain framerate, up to 60 fps – thanks to the
  start bitrate also 1080p from second one.
- Levels and measured bitrate (H.264, film):

| Level | Resolution | Measured | Upload per viewer |
|---|---|---|---|
| High | 1920×1080 | ~6.5 Mbit/s | up to 8 Mbit/s |
| Medium | 1280×720 | ~3.3 Mbit/s | up to 4 Mbit/s |
| Economy | 853×480 | ~1.7 Mbit/s | up to 2 Mbit/s |

The streaming panel shows live what is actually being sent, and warns when the browser throttles
because of the processor ("cpu") or the connection ("bandwidth").

## Limits of this measurement

Measured on one machine (12 cores, software encoder in Chromium) with the server on the same
device. Over the internet the server's upload bandwidth is the limit; on weaker machines the
encoder ("cpu") can be – then "Medium" helps.

## Real film, real machine (live measurement during the first test)

Measured on a running stream (Brave, shared tab with a film, one viewer in a private window),
as an additional measuring viewer over 20 s:

| | Value |
|---|---|
| Video | H.264, 1850×920 (window size), 23.8 fps (film: 24 fps), 6.1 Mbit/s |
| Picture quality | QP ⌀ 21.7 – very good |
| Glitches | 0 dropped frames, 0 freezes, 0 packet loss |
| Viewer buffer | ~100 ms |
| CPU | browser in total ~1.7 of 12 cores – not a limit |
| **Audio** | **Opus, mono, ~31 kbit/s** – the weakest link |

There was little left to gain on the picture; full 1080p comes when the shared tab is fullscreen.

## Audio: stereo instead of phone quality

Without extra parameters, Chrome sends Opus as mono at ~32 kbit/s, tuned for speech. Measured with
440 Hz left / 880 Hz right and a frequency analysis per channel at the viewer:

| | sent | MediaMTX | at the viewer | left 440/880 Hz | right 440/880 Hz |
|---|---|---|---|---|---|
| before | mono | 1 channel | 33 kbit/s | -34 / -34 dB | -34 / -34 dB |
| sender stereo only | stereo | 2 channels | 191 kbit/s | -34 / -34 dB | -34 / -34 dB |
| **sender + viewer** | stereo | 2 channels | **194 kbit/s** | **-28 / -119 dB** | **-109 / -28 dB** |

Two things were needed: the sender sends `stereo=1;sprop-stereo=1;maxaveragebitrate=…`
(High 192, Medium 128, Economy 96 kbit/s) and captures without voice processing (no echo
cancellation, noise suppression or auto gain). **And the viewer must announce with `stereo=1`
that it wants stereo** – otherwise Chrome mixes the signal back down to mono.
The E2E suite checks this with the same two-tone measurement.

## Smoothness: buffering at the viewer

Impression from the test: "runs a little jittery". Measured per frame with
`requestVideoFrameCallback`: spacing of capture timestamps vs. spacing of display at the viewer
(running stream, 20 s per measurement, one after another):

| Buffer (`jitterBufferTarget`) | Display jitter | Capture jitter | Display↔capture deviation p95 / max |
|---|---|---|---|
| default (~46 ms) | 16.1 ms | 14.0 ms | 23 ms / **65 ms** |
| **300 ms** | **13.5 ms** | 13.1 ms | **14 ms / 24 ms** |
| 600 ms | 14.3 ms | 11.1 ms | 20 ms / 31 ms |

WebRTC is tuned for video calls and shows frames as early as possible. With a 300 ms buffer the
transport adds practically no jitter anymore; more buffer didn't help. All viewers use the same
value and so stay in sync with each other. Over the internet the buffer helps too: lost packets
can still be re-requested before the frame is shown – fewer blocks, fewer requested keyframes.

What no buffer can smooth out: jitter that already happens at capture. A 24 fps film on a 60 Hz
screen plays in a 3:2 cadence, and a shared tab inherits that cadence (measured: spacing of
17–67 ms instead of an even 42 ms). The fix: **OBS with the film as a Media Source** – OBS reads
the file directly and sends perfectly even frames, with more thorough encoding on top.
