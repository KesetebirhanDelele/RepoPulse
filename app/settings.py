import os
from pathlib import Path

_DEFAULT_DB_URL = "sqlite:///data/repopulse.sqlite3"


def _load_dotenv(path: Path) -> None:
    """Read a .env file and populate os.environ for keys not already set."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


class Settings:
    def __init__(self) -> None:
        _load_dotenv(Path(".env"))
        self.db_path: Path = Path("data/repopulse.sqlite3")
        self.github_token: str | None = os.environ.get("GITHUB_TOKEN", None)
        self.db_url: str = os.environ.get("DB_URL", _DEFAULT_DB_URL)
        # Ensure the data/ directory exists when using the default sqlite URL.
        if self.db_url == _DEFAULT_DB_URL:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
