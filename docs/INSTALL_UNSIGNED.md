# Installing Scribble

Scribble is free and open source. The `.dmg` is **not signed with an Apple Developer ID**, so macOS Gatekeeper will block it on first launch. This is a one-time, per-user workaround — not a bug, not a virus. You can read or compile the source yourself on GitHub.

The steps are different on macOS 15 (Sequoia) vs. earlier versions. **Pick the one that matches your Mac.**

---

## System requirements

- **macOS 11.0 (Big Sur) or later**
- **Apple Silicon (M1 / M2 / M3 / M4)** — Intel Macs are not supported
- ~2 GB free disk space for Whisper models

---

## Step 1 — Install the app

1. Download `Scribble_<version>_aarch64.dmg` from the [latest release](https://github.com/jeffclark/video-transcriber/releases/latest).
2. Double-click the downloaded `.dmg` to mount it.
3. Drag the **Scribble** icon onto the **Applications** folder.
4. Eject the disk image (drag to Trash, or right-click → Eject).

---

## Step 2 — First launch (choose your macOS version)

### macOS 14 Sonoma and earlier

1. Open the **Applications** folder in Finder.
2. **Right-click** (or Control-click) on **Scribble**.
3. Choose **Open** from the menu.
4. A warning dialog appears: *"macOS cannot verify the developer of 'Scribble'. Are you sure you want to open it?"*
5. Click **Open**.

That's it. From now on, Scribble launches normally like any other app.

### macOS 15 Sequoia and later

Apple removed the right-click shortcut in Sequoia. The steps are a bit longer, but still one-time:

1. Open the **Applications** folder.
2. Double-click **Scribble**.
3. A dialog says *"Scribble" cannot be opened because Apple cannot check it for malicious software.*
   Click **Done** to dismiss it.
4. Open **System Settings** (Apple menu → System Settings).
5. Go to **Privacy & Security** in the sidebar.
6. Scroll down to the **Security** section. You'll see a line reading *"Scribble was blocked to protect your Mac."*
7. Click **Open Anyway** next to that message.
8. You'll be prompted for your Mac password (or Touch ID). Authenticate.
9. A final confirmation dialog appears. Click **Open Anyway**.
10. Scribble launches.

After this, Scribble launches normally — you will not have to repeat these steps.

---

## Why the warning exists

macOS Gatekeeper warns about any app that isn't signed and notarized by Apple. Notarization costs $99/year and requires an Apple Developer Program membership. For a free, open-source tool I publish on my own time, that's not a cost I chose to take on.

You can verify the app is what it claims to be by:

- Comparing the `.dmg` SHA-256 hash against the one published on the [release page](https://github.com/jeffclark/video-transcriber/releases/latest).
- Inspecting the [source code](https://github.com/jeffclark/video-transcriber).
- Building it yourself from source (see the project README).

---

## First transcription is slow

The **first time** you transcribe a video, Scribble downloads the Whisper model (140 MB – 3 GB depending on the model size you pick). This is a one-time download per model; afterward, transcription is fully offline.

---

## Uninstalling

Drag **Scribble** from Applications to the Trash. To remove cached models as well:

```
rm -rf ~/.cache/huggingface/hub/models--Systran--faster-whisper-*
```

---

## Troubleshooting

### "Scribble quit unexpectedly" on first launch

Usually the backend process couldn't start. Open **Terminal** and run:

```
killall scribble-backend 2>/dev/null
```

Then re-launch Scribble from Applications.

### The app won't appear in Privacy & Security after being blocked

The "Open Anyway" button only appears for ~1 hour after you tried to open the app. If you missed the window, just double-click Scribble in Applications again; the button will re-appear.

### Still stuck?

[Open an issue](https://github.com/jeffclark/video-transcriber/issues) with your macOS version and what you saw.
