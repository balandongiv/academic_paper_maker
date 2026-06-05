"""Configuration management for Scopus automation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

DEFAULT_CONFIG_FILE = "setting/scopus_setup/scopus_config.json"

_WINDOWS_CHROME_PROFILE = os.path.expandvars(
    r"%LOCALAPPDATA%\Google\Chrome\User Data"
)


@dataclass
class ScopusConfig:
    chromedriver_path: str = r"browser\chromedriver.exe"
    chrome_profile_path: str = _WINDOWS_CHROME_PROFILE
    chrome_profile_name: str = "Default"
    output_dir: str = "output"
    download_timeout_sec: int = 120
    page_load_timeout_sec: int = 60
    element_wait_sec: int = 30
    headless: bool = False

    # ------------------------------------------------------------------
    # Derived paths
    # ------------------------------------------------------------------
    def search_output_dir(self) -> Path:
        return Path(self.output_dir) / "search"

    def cited_by_output_dir(self) -> Path:
        return Path(self.output_dir) / "cited_by"

    def combined_output_dir(self) -> Path:
        return Path(self.output_dir) / "combined"

    def logs_dir(self) -> Path:
        return Path(self.output_dir) / "logs"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    @classmethod
    def from_file(cls, path: str = DEFAULT_CONFIG_FILE) -> "ScopusConfig":
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
            return cls(**known)
        return cls()

    def save(self, path: str = DEFAULT_CONFIG_FILE) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(self), fh, indent=2)

    # ------------------------------------------------------------------
    # Ensure output directories exist
    # ------------------------------------------------------------------
    def ensure_dirs(self) -> None:
        for d in (
            self.search_output_dir(),
            self.cited_by_output_dir(),
            self.combined_output_dir(),
            self.logs_dir(),
        ):
            d.mkdir(parents=True, exist_ok=True)
