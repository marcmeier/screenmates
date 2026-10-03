# Kino – Checkliste für den echten Test

Was sich nicht automatisch testen lässt: echtes OBS und Freunde, die über das Internet
zuschauen. Diese Liste dauert etwa 15 Minuten.

## 1. OBS (auf dem Rechner des Hosts)

1. In screenmates Host werden (`Strg+Shift+H`) → **Kino** → Reiter **OBS**.
2. OBS ≥ 30 → *Einstellungen → Stream*: Dienst **WHIP**, Server und Bearer-Token aus screenmates einfügen.
3. *Einstellungen → Ausgabe* (Modus „Erweitert“): Keyframe-Intervall **1 s**, **B-Frames 0**
   (bei x264 unter „x264-Optionen“: `bframes=0`).
4. Eine Szene mit Bewegung und Ton, dann **Streaming starten**. Für Filme die Datei als
   **„Medienquelle“** einbinden (nicht den Bildschirm aufnehmen): Das gibt gleichmäßige 24 fps
   ohne den 3:2-Ruckler des Bildschirms.

Prüfen:

- [ ] screenmates zeigt beim Host „Du bist live (über OBS)“, im Menü leuchtet „Kino“.
- [ ] Ein zweites Gerät im selben Netz schaut zu: Bild flüssig, nach „Ton an“ ist Ton da.
- [ ] Verzögerung: eine Uhr im Bild vergleichen – sollte unter 1 Sekunde liegen.
- [ ] Optional: B-Frames testweise auf 2 stellen und neu starten. Ruckelt oder springt das Bild?
      (Ergebnis bitte notieren – das ließ sich ohne OBS nicht nachstellen.)
- [ ] **Streaming beenden** in OBS → in screenmates nach wenigen Sekunden „Gerade läuft nichts“.
- [ ] Erneut starten, dann in screenmates **Übertragung beenden** → OBS meldet den Abbruch.

## 2. Über das Internet

Voraussetzung: screenmates ist öffentlich erreichbar (Server, Portfreigabe oder Tailscale),
Port **8189** UDP+TCP ist offen, `KINO_PUBLIC_HOST` ist gesetzt.

- [ ] Eine Person **außerhalb** deines Netzes (Mobilfunk reicht: WLAN am Handy aus) öffnet die
      Seite, wählt einen Namen und schaut zu.
- [ ] Im Browser unter `chrome://webrtc-internals` (bzw. `about:webrtc` in Firefox) beim Zuschauer:
      Die gewählte Verbindung („candidate pair“) geht an deine öffentliche Adresse auf Port 8189.
- [ ] Mehrere Zuschauende gleichzeitig: Upload des Servers reicht? (~5 Mbit/s pro Person in 1080p)

Klappt der Mobilfunk-Test nicht: Port 8189 an der Firewall/am Router prüfen und ob
`KINO_PUBLIC_HOST` die Adresse ist, unter der der Server von außen erreichbar ist.
