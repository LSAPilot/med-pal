"""Entry point for Hugging Face Spaces (`app_file: app.py`) and for local runs (`uv run python app.py`)."""
import os
import sys
from pathlib import Path

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))  # in the Space the package is not pip-installed

# ZeroGPU: a Space on that hardware refuses to start without at least one @spaces.GPU function.
# This app needs no GPU (query embeddings run on CPU, see retrieval.get_model), so the function is never called.
try:
    import spaces

    @spaces.GPU
    def _zerogpu_marker():  # pragma: no cover
        return None
except ImportError:  # local run or CPU hardware
    pass

from regulatory_helper.app import launch  # noqa: E402

if __name__ == "__main__":
    launch()
