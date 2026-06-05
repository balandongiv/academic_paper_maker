"""YAML configuration loading for the Scopus pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class RunConfig:
    mode: str = "citation_discovery"  # "citation_discovery" | "keyword_search"
    force_rerun: bool = False
    output_filename: Optional[str] = None


@dataclass
class ZoteroApiConfig:
    library_type: str = "user"
    library_id: str = ""
    collection_key: str = ""
    include_subcollections: bool = False
    api_key: str = ""


@dataclass
class InputConfig:
    mode: str = "csv"  # "csv" | "zotero_api"
    csv_path: Optional[str] = None
    zotero: Optional[ZoteroApiConfig] = None


@dataclass
class ZoteroExportConfig:
    deduplicate_against_master_list: bool = True
    export_format: str = "ris"


@dataclass
class MasterListConfig:
    path: str = "complete_file_available_in_zotero.csv"
    reuse_existing: bool = True


@dataclass
class OutputConfig:
    directory: str = "output/"
    filename: Optional[str] = None


@dataclass
class PipelineConfig:
    run: RunConfig = field(default_factory=RunConfig)
    input: InputConfig = field(default_factory=InputConfig)
    zotero: ZoteroExportConfig = field(default_factory=ZoteroExportConfig)
    master_list: MasterListConfig = field(default_factory=MasterListConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    keywords: list[str] = field(default_factory=list)
    scopus_config_path: str = "scopus_config.json"


def load_config(config_path: str) -> PipelineConfig:
    """Load pipeline configuration from a YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {config_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Config must be a YAML mapping: {config_path}")

    cfg = PipelineConfig()

    if run_d := data.get("run"):
        cfg.run = RunConfig(
            mode=run_d.get("mode", "citation_discovery"),
            force_rerun=bool(run_d.get("force_rerun", False)),
            output_filename=run_d.get("output_filename") or None,
        )

    if inp_d := data.get("input"):
        zotero_api = None
        if z := inp_d.get("zotero"):
            zotero_api = ZoteroApiConfig(
                library_type=z.get("library_type", "user"),
                library_id=str(z.get("library_id", "")),
                collection_key=z.get("collection_key", ""),
                include_subcollections=bool(z.get("include_subcollections", False)),
                api_key=z.get("api_key", ""),
            )
        cfg.input = InputConfig(
            mode=inp_d.get("mode", "csv"),
            csv_path=inp_d.get("csv_path") or None,
            zotero=zotero_api,
        )

    if z_d := data.get("zotero"):
        cfg.zotero = ZoteroExportConfig(
            deduplicate_against_master_list=bool(
                z_d.get("deduplicate_against_master_list", True)
            ),
            export_format=z_d.get("export_format", "ris"),
        )

    if ml_d := data.get("master_list"):
        cfg.master_list = MasterListConfig(
            path=ml_d.get("path", "complete_file_available_in_zotero.csv"),
            reuse_existing=bool(ml_d.get("reuse_existing", True)),
        )

    if out_d := data.get("output"):
        cfg.output = OutputConfig(
            directory=out_d.get("directory", "output/"),
            filename=out_d.get("filename") or None,
        )

    cfg.keywords = [str(k) for k in data.get("keywords", [])]
    cfg.scopus_config_path = data.get("scopus_config_path", "scopus_config.json")

    return cfg
