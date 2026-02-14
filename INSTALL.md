# Installing Scribble

Video transcription app for macOS with local Whisper models.

## System Requirements

- **macOS 11.0 (Big Sur) or later**
- **Apple Silicon (M1/M2/M3/M4)** - Intel Macs not currently supported
- **2GB free disk space**

## Download

Download `Scribble-v0.1.0-macOS.dmg` from the releases page.

## Installation Steps

### 1. Mount the DMG
Double-click `Scribble-v0.1.0-macOS.dmg` to mount the disk image.

### 2. Install the App
Drag **Video Transcriber.app** to your **Applications** folder.

### 3. Eject the DMG
Right-click on the mounted disk image and select "Eject".

### 4. First Launch

The first time you launch Scribble, macOS will show a security warning:

> **"Video Transcriber cannot be opened because it is from an unidentified developer"**

This happens because the app is not code-signed with an Apple Developer certificate.

**To bypass this warning:**

1. **Right-click** (or Ctrl+click) on **Video Transcriber** in your Applications folder
2. Select **Open** from the context menu
3. Click **Open** in the security dialog
4. The app will launch

**Note:** You only need to do this once. After the first launch, you can open the app normally by double-clicking.

## Verifying the Installation

Once the app launches, you should see:

- The main window with a file upload area
- A green **"Backend Connected"** indicator in the top-right corner
- This indicates the Python transcription engine is running

## First Transcription

1. Click **"Add Video Files"** or drag a video file into the window
2. Select **Large-v3** model (recommended for accuracy)
3. Click **Start Transcription**
4. The first transcription takes 30-60 seconds longer as it downloads the Whisper model
5. Subsequent transcriptions are much faster

## Output Files

Transcribed files are saved in the same directory as the source video:
- `video_name_transcription.txt` - Plain text transcript
- `video_name_transcription.json` - Detailed JSON with timestamps

Click **"Open Folder"** to view the output files.

## Uninstalling

To uninstall Scribble:

1. Quit the app if it's running
2. Drag **Video Transcriber.app** from Applications to Trash
3. Empty Trash

## Troubleshooting

### "Backend Disconnected" Error

**Symptom:** App shows red "Backend Disconnected" indicator.

**Solution:**
- Wait 5-10 seconds - the backend takes time to initialize
- If it doesn't connect, restart the app
- Check Activity Monitor for orphaned `scribble-backend` processes and quit them

### Orphan Backend Processes (Known Issue)

**Symptom:** After quitting and relaunching the app multiple times, it won't connect or runs slowly.

**Cause:** On macOS, when you quit the app with Cmd+Q, backend processes may not terminate immediately. These orphan processes can interfere with new launches.

**Solution - Manual Cleanup:**

1. Open **Activity Monitor** (Applications → Utilities → Activity Monitor)
2. Search for `scribble-backend`
3. Select all `scribble-backend` processes
4. Click the **X** button (Force Quit) in the toolbar
5. Relaunch Video Transcriber

**Solution - Terminal Cleanup:**
```bash
killall scribble-backend
```

**Note:** This is a known limitation in v0.1.0. Future versions will implement proper process cleanup.

### App Won't Open

**Symptom:** Double-clicking the app does nothing.

**Solution:**
- Follow the First Launch instructions above (right-click → Open)
- Check Console.app for error messages (search for "Video Transcriber")

### Transcription Fails

**Symptom:** Transcription starts but fails with an error.

**Common causes:**
- Video file is corrupted or unsupported format
- Not enough disk space (models can be 1-3GB)
- Port 8765 is in use by another application

**Solution:**
- Try a different video file
- Free up disk space
- Restart your computer to clear port conflicts

### Performance Issues

**Symptom:** Transcription is very slow.

**Note:** This is expected for CPU-only transcription. M1/M2/M3 Macs use CPU mode and process about 1-2 minutes of audio per minute of processing time.

**Tips:**
- Use the "Turbo" model for faster (but less accurate) transcription
- Close other resource-intensive applications
- For very long videos (>1 hour), consider splitting them

## Getting Help

For issues not covered here:
- Check the GitHub Issues page
- Include your macOS version and Mac model (M1/M2/M3)
- Attach relevant error messages from Console.app

## Privacy

All transcription happens **locally on your Mac**. No audio or video is sent to external servers. The app requires internet only for downloading Whisper models on first use.
