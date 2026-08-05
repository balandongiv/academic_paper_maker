"""Check the DOI references one at a time in Scopus using Selenium."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import scopus_automation.browser as browser
from scopus_automation import search_export as se
from scopus_automation.config import ScopusConfig


DOIS = [
    "10.1016/j.sna.2020.112451",
    "10.1155/2022/7957148",
    "10.1109/ICACITE53722.2022.9823528",
    "10.1016/j.ultras.2022.106776",
    "10.21474/ijar01/17119",
    "10.1155/2016/9391850",
    "10.3390/s23218997",
    "10.1155/2022/1901058",
    "10.32604/cmc.2023.044140",
    "10.1109/ICACITE57410.2023.10182920",
    "10.3390/s23104830",
    "10.3390/s24237705",
    "10.1155/2020/6625797",
    "10.3390/s24092940",
    "10.3390/s23020719",
    "10.3390/s19030699",
    "10.1109/IC3IoT60841.2024.10550418",
    "10.30880/jeva.2024.05.02.004",
    "10.1016/j.aej.2020.10.001",
]


def logged_in(driver) -> bool:
    try:
        text = driver.execute_script(
            "return document.body ? document.body.innerText : '';"
        )
        lowered = text.lower()
        login_markers = (
            "sign in",
            "log in",
            "enter your email to continue",
            "sign in via your organization",
            "find your organization",
        )
        return len(text) > 200 and not any(marker in lowered for marker in login_markers)
    except Exception:
        return False


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    browser.CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    config = ScopusConfig.from_file()
    config.headless = False
    config.page_load_timeout_sec = max(config.page_load_timeout_sec, 90)
    output = Path("output/scopus_reference_check")
    output.mkdir(parents=True, exist_ok=True)
    driver = browser.build_driver(config, output)
    results = []
    try:
        driver.get("https://www.scopus.com")
        print("Scopus opened in Chrome. Complete sign-in in that window if required.", flush=True)
        deadline = time.monotonic() + 300
        while not logged_in(driver) and time.monotonic() < deadline:
            time.sleep(2)
        if not logged_in(driver):
            raise RuntimeError("Scopus login was not detected within 5 minutes")
        print("Scopus session detected; starting one-by-one DOI checks.", flush=True)

        for index, doi in enumerate(DOIS, 1):
            row = {"index": index, "doi": doi}
            print(f"[{index}/{len(DOIS)}] DOI({doi})", flush=True)
            try:
                if not se._navigate_to_advanced_search(driver, config):
                    row.update(status="ERROR", result_count=None, error="search form not found")
                else:
                    se._enter_query(driver, f"DOI({doi})")
                    se._submit_search(driver)
                    time.sleep(3)
                    count = se._wait_for_results(driver, timeout=60)
                    row.update(
                        status="FOUND" if count > 0 else "NOT_FOUND",
                        result_count=count,
                        search_url=se._current_url(driver),
                    )
                    print(f"  -> {row['status']} ({count})", flush=True)
            except Exception as exc:
                row.update(status="ERROR", result_count=None, error=str(exc))
                print(f"  -> ERROR: {exc}", flush=True)
            results.append(row)
            (output / "results.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )
        print(json.dumps(results, indent=2), flush=True)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
