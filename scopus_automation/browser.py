"""Chrome browser setup and download management.

Uses a dedicated Selenium profile stored at C:\\selenium\\chrome-profile.

First run: Chrome opens, you log into Scopus and tick "Keep me signed in".
Subsequent runs: Chrome reopens with that saved session — no login needed.

If Chrome is already open you do NOT need to close it.
The dedicated profile is separate from your normal Chrome profile.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException

from .config import ScopusConfig

log = logging.getLogger(__name__)

#: Persistent Selenium profile holding the logged-in Scopus session. Override with the
#: SCOPUS_PROFILE_DIR environment variable when the session lives in a different profile
#: (the sign-in is stored per profile, so pointing at the wrong one forces a fresh login).
SELENIUM_PROFILE_DIR = os.environ.get(
    "SCOPUS_PROFILE_DIR", r"C:\selenium\chrome-profile"
)

# Chrome installs to either the per-user or the machine-wide location depending on how it
# was installed, so the binary must be resolved at runtime. Hardcoding one of these paths
# makes the driver fail with a bare "Chrome failed to start" on any machine using the other.
_CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Users\balan\AppData\Local\Google\Chrome\Application\chrome.exe",
)


def _resolve_chrome_exe() -> str:
    """First Chrome binary that actually exists; fail loudly rather than guessing."""
    override = os.environ.get("CHROME_EXE")
    candidates = (override, *_CHROME_CANDIDATES) if override else _CHROME_CANDIDATES
    for path in candidates:
        if path and Path(path).exists():
            return path
    raise RuntimeError(
        "Could not find chrome.exe. Checked:\n  "
        + "\n  ".join(c for c in candidates if c)
        + "\nSet the CHROME_EXE environment variable to the correct path."
    )


CHROME_EXE = _resolve_chrome_exe()


def _resolve_chromedriver(config_path: str) -> str:
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        path = ChromeDriverManager().install()
        log.debug("ChromeDriver via webdriver-manager: %s", path)
        return path
    except Exception as exc:
        log.warning("webdriver-manager failed (%s). Using bundled: %s", exc, config_path)
        return config_path


def build_driver(
    config: ScopusConfig,
    download_dir: Path,
    remote_port: int = 9222,   # kept for API compatibility
) -> webdriver.Chrome:
    """
    Open Chrome with the dedicated Selenium profile.

    The profile lives at C:\\selenium\\chrome-profile and is completely
    separate from your main Chrome — both can run at the same time.

    First run: log in to Scopus and tick "Keep me signed in".
    Subsequent runs: the saved cookie means no re-login is needed.
    """
    download_dir.mkdir(parents=True, exist_ok=True)
    Path(SELENIUM_PROFILE_DIR).mkdir(parents=True, exist_ok=True)

    options = Options()
    options.binary_location = CHROME_EXE

    # Dedicated profile — parent dir + profile name, split correctly
    options.add_argument(f"--user-data-dir={SELENIUM_PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")

    prefs = {
        "download.default_directory": str(download_dir.resolve()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if config.headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver_path = _resolve_chromedriver(str(config.chromedriver_path))
    service = Service(executable_path=driver_path)

    try:
        driver = webdriver.Chrome(service=service, options=options)
    except WebDriverException as exc:
        print(
            f"\nERROR: Chrome could not start.\n"
            f"Chrome binary: {CHROME_EXE}\n"
            f"Profile dir:   {SELENIUM_PROFILE_DIR}\n"
            f"Error: {exc}\n"
        )
        raise RuntimeError("Chrome failed to start.") from exc

    driver.set_page_load_timeout(config.page_load_timeout_sec)
    driver.maximize_window()

    log.info(
        "Chrome started. Profile=%s  Download=%s",
        SELENIUM_PROFILE_DIR, download_dir.resolve(),
    )
    return driver


def wait_for_download(
    download_dir: Path,
    timeout_sec: int = 120,
    min_mtime: float = 0,
) -> Path | None:
    """Wait for a new .ris file (no .crdownload present).
    `min_mtime`: only consider files modified at or after this Unix timestamp.
    """
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        partial   = list(download_dir.glob("*.crdownload"))
        ris_files = list(download_dir.glob("*.ris"))
        if min_mtime > 0:
            ris_files = [f for f in ris_files if f.stat().st_mtime >= min_mtime]
        if ris_files and not partial:
            latest = max(ris_files, key=lambda p: p.stat().st_mtime)
            log.info("Download complete: %s", latest)
            return latest
        time.sleep(1)

    log.warning("Timed out waiting for .ris in %s", download_dir)
    return None


def rename_download(src: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() == dest.resolve():
        log.info("Already named correctly: %s", dest)
        return dest
    if dest.exists():
        dest.unlink()
    src.rename(dest)
    log.info("Saved -> %s", dest)
    return dest


def set_download_dir(driver: webdriver.Chrome, download_dir: Path) -> None:
    download_dir.mkdir(parents=True, exist_ok=True)
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": str(download_dir.resolve())},
        )
        log.debug("Download dir set via CDP -> %s", download_dir.resolve())
    except Exception as exc:
        log.debug("CDP set-download skipped: %s", exc)
