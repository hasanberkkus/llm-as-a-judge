from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = BASE_DIR / "src" / "prompts"
REPORTS_DIR = BASE_DIR / "reports"

WORKER_MODEL = "qwen3:4b-instruct"

JUDGE_MODEL = "qwen3:8b"