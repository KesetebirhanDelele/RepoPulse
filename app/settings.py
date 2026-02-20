import os
from pathlib import Path

_DEFAULT_DB_URL = "sqlite:///data/repopulse.sqlite3"


class Settings:
    def __init__(self) -> None:
        self.db_path: Path = Path("data/repopulse.sqlite3")
        self.github_token: str | None = os.environ.get("GITHUB_TOKEN", None)
        self.db_url: str = os.environ.get("DB_URL", _DEFAULT_DB_URL)
        # Ensure the data/ directory exists when using the default sqlite URL.
        if self.db_url == _DEFAULT_DB_URL:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
