# FRC Explainer Video Generator

Generate short Peter/Stewie-style explainer reels for FRC and coding topics.

The local workflow is:

1. Run the CLI with a topic prompt and, optionally, an article URL.
2. Claude CLI generates a structured 40-60 second dialogue script.
3. Fish Audio generates one MP3 per dialogue turn.
4. MoviePy assembles the background video, character images, audio, and word-by-word captions.
5. The final MP4 and review artifacts are saved together in one output folder.

## Requirements

- Python 3.11+
- Claude CLI
- FFmpeg on PATH
- ImageMagick usable by MoviePy `TextClip`
- Fish Audio API key and voice IDs

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Configuration

Copy `.env.template` to `.env` and fill in your Fish Audio values:

```text
FISH_AUDIO_API_KEY=your_key_here
FISH_AUDIO_PETER_VOICE_ID=your_peter_voice_id
FISH_AUDIO_STEWIE_VOICE_ID=your_stewie_voice_id
FISH_AUDIO_MODEL=s2-pro
```

`FISH_API_KEY` is also accepted as an alias for `FISH_AUDIO_API_KEY`.

If MoviePy cannot find ImageMagick on Windows, set this too:

```text
IMAGEMAGICK_BINARY=C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe
```

Usually this is not needed if `magick -version` works in the same terminal.

## Usage

```powershell
python flow_main.py `
  --prompt "Explain PID control for an FRC swerve module" `
  --url "https://example.com/optional-source-article" `
  --out outputs
```

`--out` defaults to `outputs`, so it can be omitted. If `--background` is omitted, the CLI picks a random video from `video_assets/backgrounds/`.

You can still override the background explicitly:

```powershell
python flow_main.py `
  --prompt "Explain PID control for an FRC swerve module" `
  --background "path\to\vertical_gameplay.mp4"
```

To debug rendering without spending more TTS credits, resume from an existing run folder:

```powershell
python flow_main.py `
  --render-only outputs\swerve_drive_pid
```

This reloads the saved `*_script.json` and `audio/*.mp3`, then reruns only the MoviePy render step.

The output folder is named from the generated topic slug:

```text
outputs/
  swerve_drive_pid/
    audio/
      01_peter.mp3
      02_stewie.mp3
    swerve_drive_pid_prompt.md
    swerve_drive_pid_script.json
    swerve_drive_pid_script.md
    swerve_drive_pid_manifest.json
    swerve_drive_pid.mp4
```

If a folder already exists, the CLI adds a suffix such as `_2`.

## Notes

- The old Telegram bot, SQLite staging database, AWS VM shutdown, and Parrot/Selenium scraping flow have been removed.
- Fish Audio is the first TTS provider, but the code is organized so additional providers can be added behind the same interface.
- Video Use is intentionally not part of the MVP render path. It is a better future fit for optional advanced finishing, overlays, or agentic editing passes.

## Tests

```powershell
python -m unittest discover -s tests
```

The render smoke test skips automatically when the current terminal cannot see `ffmpeg`.
