import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLASSES = ["0", "1", "2", "3", "4", "6", "W"]
RUNS_PER_CLASS = [0, 1, 2, 3, 4, 6, 0]
MODEL_PATH = Path(os.getenv("MM_MODEL_PATH", ROOT / "data" / "model.joblib"))
BALLS_CSV = Path(os.getenv("MM_BALLS_CSV", ROOT / "data" / "balls.csv"))


def phase_of(over: int) -> str:
    """T20 phases. over is 0-indexed (0..19)."""
    return "powerplay" if over < 6 else "middle" if over < 15 else "death"


PHASES = ["powerplay", "middle", "death"]
