# Repository Guidelines

## Project Overview

- This is a Python 3.11+ CLI project for generating short Peter/Stewie-style explainer reels.
- `flow_main.py` is the main command-line entry point.
- Core pipeline code lives in `stewie_explainer/`.
- Unit tests live in `tests/`.
- Character image assets are in `image_assests/`; keep the existing misspelled directory name because the CLI defaults to it.
- Background videos are expected under `video_assets/backgrounds/`.

## Setup

- Install dependencies with:

```powershell
python -m pip install -r requirements.txt
```

- Runtime configuration is loaded from `.env`. Use `.env.template` as the reference for required Fish Audio values.
- Do not commit secrets from `.env`.

## Common Commands

- Run the test suite:

```powershell
python -m unittest discover -s tests
```

- Show CLI options:

```powershell
python flow_main.py --help
```

- Render from an existing run folder without spending TTS credits:

```powershell
python flow_main.py --render-only outputs\some_run_folder
```

## Generated Files

- `outputs/`, `runtime/`, `runtime_logs/`, `audio_assests/`, `downloaded_images/`, and `archives_audios/` are generated local artifacts and should stay untracked.
- Large local background videos in `video_assets/backgrounds/` are ignored except for `.gitkeep`.

## Development Notes

- Prefer extending the modules in `stewie_explainer/` over adding behavior directly to `flow_main.py`.
- Keep tests focused in `tests/` for pipeline, renderer, transcript, TTS, slugging, background, and artifact behavior.
- Rendering depends on FFmpeg and, for `MoviePy` text clips, ImageMagick availability in the same terminal environment.
