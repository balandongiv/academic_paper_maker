import json
import os
from pathlib import Path
from typing import Iterable, Optional

import requests


class ServerUnavailableException(RuntimeError):
    """Raised when the configured GROBID server cannot be reached."""


class GrobidClient:
    def __init__(
            self,
            grobid_server: str = "http://localhost:8070",
            batch_size: int = 1000,
            coordinates: Optional[list[str]] = None,
            sleep_time: int = 5,
            timeout: int = 60,
            config_path: Optional[str] = None,
            check_server: bool = True,
    ):
        if config_path:
            with open(config_path, "r", encoding="utf-8") as config_file:
                config = json.load(config_file)
            grobid_server = config.get("grobid_server", grobid_server)
            batch_size = config.get("batch_size", batch_size)
            coordinates = config.get("coordinates", coordinates)
            sleep_time = config.get("sleep_time", sleep_time)
            timeout = config.get("timeout", timeout)

        self.grobid_server = grobid_server.rstrip("/")
        self.batch_size = batch_size
        self.coordinates = coordinates or []
        self.sleep_time = sleep_time
        self.timeout = timeout

        if check_server:
            self.check_server()

    def check_server(self) -> None:
        try:
            response = requests.get(f"{self.grobid_server}/api/isalive", timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ServerUnavailableException(
                f"GROBID server is not available at {self.grobid_server}"
            ) from exc

        if response.text.strip().lower() != "true":
            raise ServerUnavailableException(
                f"GROBID server at {self.grobid_server} returned {response.text!r}"
            )

    def process(
            self,
            service: str,
            input_path: str,
            output: str,
            n: int = 10,
            generateIDs: bool = False,
            consolidate_header: bool = True,
            consolidate_citations: bool = False,
            include_raw_citations: bool = False,
            include_raw_affiliations: bool = False,
            tei_coordinates: bool = False,
            segment_sentences: bool = False,
            force: bool = False,
            verbose: bool = False,
    ) -> list[Path]:
        del n

        input_paths = list(self._pdf_paths(input_path))[:self.batch_size]
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        written_files: list[Path] = []
        for pdf_path in input_paths:
            xml_path = output_path / f"{pdf_path.stem}.grobid.tei.xml"
            if xml_path.exists() and not force:
                if verbose:
                    print(f"Skipping existing XML: {xml_path}")
                written_files.append(xml_path)
                continue

            xml_text = self._process_pdf(
                service=service,
                pdf_path=pdf_path,
                generate_ids=generateIDs,
                consolidate_header=consolidate_header,
                consolidate_citations=consolidate_citations,
                include_raw_citations=include_raw_citations,
                include_raw_affiliations=include_raw_affiliations,
                tei_coordinates=tei_coordinates,
                segment_sentences=segment_sentences,
            )
            xml_path.write_text(xml_text, encoding="utf-8")
            written_files.append(xml_path)
            if verbose:
                print(f"Processed {pdf_path} -> {xml_path}")

        return written_files

    def _process_pdf(
            self,
            service: str,
            pdf_path: Path,
            generate_ids: bool,
            consolidate_header: bool,
            consolidate_citations: bool,
            include_raw_citations: bool,
            include_raw_affiliations: bool,
            tei_coordinates: bool,
            segment_sentences: bool,
    ) -> str:
        data = {
            "generateIDs": str(generate_ids).lower(),
            "consolidateHeader": "1" if consolidate_header else "0",
            "consolidateCitations": "1" if consolidate_citations else "0",
            "includeRawCitations": str(include_raw_citations).lower(),
            "includeRawAffiliations": str(include_raw_affiliations).lower(),
            "segmentSentences": str(segment_sentences).lower(),
        }
        if tei_coordinates and self.coordinates:
            data["teiCoordinates"] = self.coordinates

        with pdf_path.open("rb") as pdf_file:
            response = requests.post(
                f"{self.grobid_server}/api/{service}",
                files={"input": (pdf_path.name, pdf_file, "application/pdf")},
                data=data,
                timeout=self.timeout,
            )

        response.raise_for_status()
        return response.text

    @staticmethod
    def _pdf_paths(input_path: str) -> Iterable[Path]:
        path = Path(input_path)
        if path.is_file():
            if path.suffix.lower() != ".pdf":
                raise ValueError(f"Input file is not a PDF: {path}")
            return [path]
        if path.is_dir():
            return sorted(path.glob("*.pdf"))
        raise FileNotFoundError(f"Input path does not exist: {input_path}")
