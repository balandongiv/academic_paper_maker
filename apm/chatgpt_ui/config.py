"""Load and expose typed configuration from a YAML file."""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class InputConfig:
    master_file: str
    prompt_file: str


@dataclass
class OutputConfig:
    json_output_folder: str


@dataclass
class ProcessingConfig:
    batch_size: int = 10
    machine_id: str = ""
    max_retries: int = 3
    stale_lock_hours: float = 2.0


@dataclass
class SeleniumConfig:
    browser: str = "chrome"
    headless: bool = False
    wait_seconds: int = 120
    chrome_exe: str = r"C:\Users\balan\AppData\Local\Google\Chrome\Application\chrome.exe"
    chrome_profile: str = r"C:\selenium\chrome-profile"


@dataclass
class Config:
    project_root: str
    input: InputConfig
    output: OutputConfig
    processing: ProcessingConfig
    selenium: SeleniumConfig

    def __post_init__(self) -> None:
        if not self.processing.machine_id:
            self.processing.machine_id = socket.gethostname()

    @property
    def project_path(self) -> Path:
        return Path(self.project_root)

    @property
    def master_csv_path(self) -> Path:
        return self.project_path / self.input.master_file

    @property
    def prompt_path(self) -> Path:
        p = Path(self.input.prompt_file)
        return p if p.is_absolute() else self.project_path / p

    @property
    def db_path(self) -> Path:
        return self.project_path / "chatgpt_processing.db"

    @property
    def output_path(self) -> Path:
        return self.project_path / self.output.json_output_folder


def load_config(config_path: str | Path) -> Config:
    with open(config_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    return Config(
        project_root=raw["project_root"],
        input=InputConfig(**raw["input"]),
        output=OutputConfig(**raw["output"]),
        processing=ProcessingConfig(**raw.get("processing", {})),
        selenium=SeleniumConfig(**raw.get("selenium", {})),
    )
