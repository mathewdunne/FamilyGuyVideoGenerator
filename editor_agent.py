from __future__ import annotations

from pathlib import Path

from stewie_explainer.models import ExplainerScript
from stewie_explainer.renderer import MoviePyReelRenderer


class DynamicVideoEditor:
    """Deprecated adapter around the maintained MoviePy renderer.

    The original online script mixed rendering, hard-coded local paths, and network image
    search. New code should use `flow_main.py --render-only` or `MoviePyReelRenderer`
    directly so renders stay repeatable from saved script and audio artifacts.
    """

    def __init__(
        self,
        video_path: str | Path,
        output_path: str | Path,
        script: ExplainerScript,
        assets_dir: str | Path = "image_assests",
        fps: int = 24,
    ) -> None:
        if not isinstance(script, ExplainerScript):
            raise TypeError(
                "DynamicVideoEditor now expects an ExplainerScript. "
                "Use `flow_main.py --render-only outputs\\<run_folder>` for saved runs."
            )

        self.video_path = Path(video_path)
        self.output_path = Path(output_path)
        self.script = script
        self.renderer = MoviePyReelRenderer(assets_dir=Path(assets_dir), fps=fps)

    def edit(self) -> Path:
        return self.renderer.render(self.script, self.video_path, self.output_path)
