"""Selenium browser helpers for ChatGPT automation.

Extracted and generalised from tutorial/run_chatgpt_prompt.py.
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .config import SeleniumConfig

log = logging.getLogger(__name__)

CHATGPT_URL = "https://chatgpt.com/"


# ---------------------------------------------------------------------------
# Driver setup
# ---------------------------------------------------------------------------

def _resolve_chromedriver(bundled: str) -> str:
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        path = ChromeDriverManager().install()
        log.debug("ChromeDriver via webdriver-manager: %s", path)
        return path
    except Exception as exc:
        log.warning("webdriver-manager failed (%s) — using bundled chromedriver.", exc)
        return bundled


def _clean_chrome_profile(profile_root: str) -> None:
    """Delete cached/storage data from the Chrome profile before launching.

    Accumulated conversation cache in IndexedDB/LocalStorage makes Chrome
    progressively slower on each new run.  Cookies are intentionally left
    intact so the ChatGPT login session survives.
    """
    default_dir = Path(profile_root) / "Default"
    dirs_to_clear = [
        "Cache",
        "Code Cache",
        "IndexedDB",
        "GPUCache",
    ]
    for subdir in dirs_to_clear:
        target = default_dir / subdir
        if target.exists():
            try:
                shutil.rmtree(target)
                log.info("Cleared Chrome profile dir: %s", target)
            except Exception as exc:
                log.warning("Could not clear %s: %s", target, exc)


def build_driver(
    cfg: SeleniumConfig,
    chromedriver_path: str,
    detach: bool = False,
) -> webdriver.Chrome:
    Path(cfg.chrome_profile).mkdir(parents=True, exist_ok=True)
    _clean_chrome_profile(cfg.chrome_profile)

    options = Options()
    options.binary_location = cfg.chrome_exe
    options.add_argument(f"--user-data-dir={cfg.chrome_profile}")
    options.add_argument("--profile-directory=Default")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    if detach:
        options.add_experimental_option("detach", True)   # keep browser alive after script exits
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-background-timer-throttling")

    if cfg.headless:
        options.add_argument("--headless=new")

    service = Service(executable_path=_resolve_chromedriver(chromedriver_path))
    driver  = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(120)
    driver.set_script_timeout(600)
    driver.maximize_window()
    return driver


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def _is_logged_in(driver: webdriver.Chrome) -> bool:
    if "chatgpt.com" not in driver.current_url:
        return False
    if driver.find_elements(By.XPATH, "//*[contains(text(),'Log in or sign up')]"):
        return False
    if driver.find_elements(
        By.XPATH, "//*[self::a or self::button][contains(normalize-space(.),'Log in')]"
    ):
        return False
    if driver.find_elements(
        By.XPATH, "//*[self::a or self::button][contains(normalize-space(.),'Sign up')]"
    ):
        return False
    return bool(driver.find_elements(By.ID, "prompt-textarea"))


def ensure_logged_in(driver: webdriver.Chrome) -> None:
    if _is_logged_in(driver):
        log.info("Already logged in — proceeding.")
        return

    log.warning("Not logged in — waiting up to 3 minutes for login in the Chrome window...")
    print()
    print("=" * 60)
    print("  ACTION REQUIRED in the Chrome window:")
    print("  1. Click 'Continue with Google' (or Log in).")
    print("  2. Complete Google credentials.")
    print("  3. Wait until you are back on the ChatGPT chat page.")
    print("=" * 60)
    print()
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        time.sleep(3)
        if _is_logged_in(driver):
            break
    else:
        raise RuntimeError(
            "Still not logged in after 3 minutes. "
            "Please log in to ChatGPT in the Chrome window that opened."
        )
    log.info("Login confirmed.")


# ---------------------------------------------------------------------------
# New chat navigation
# ---------------------------------------------------------------------------

def navigate_to_new_chat(driver: webdriver.Chrome) -> None:
    """Navigate to ChatGPT root URL to start a fresh conversation."""
    driver.get(CHATGPT_URL)
    time.sleep(2)


# ---------------------------------------------------------------------------
# Input box
# ---------------------------------------------------------------------------

def _get_input_box(driver: webdriver.Chrome, wait_seconds: int = 30):
    wait = WebDriverWait(driver, wait_seconds)
    try:
        return wait.until(EC.element_to_be_clickable((By.ID, "prompt-textarea")))
    except TimeoutException:
        return wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[contenteditable='true']"))
        )


def _send_text_to_box(driver: webdriver.Chrome, input_box, text: str) -> None:
    driver.execute_script("arguments[0].scrollIntoView(true);", input_box)
    time.sleep(0.3)
    driver.execute_script("arguments[0].focus();", input_box)
    time.sleep(0.3)

    # Chunk execCommand so each HTTP round-trip stays well under urllib3's 120s read
    # timeout. Chrome executes each small insertText synchronously; sequential chunks
    # append at the cursor position, so the full text lands in order.
    chunk_size = 8000
    for i in range(0, len(text), chunk_size):
        driver.execute_script(
            "document.execCommand('insertText', false, arguments[0]);",
            text[i:i + chunk_size],
        )
        time.sleep(0.05)
    time.sleep(0.5)

    # Fallback: if execCommand left the box empty use chunked send_keys
    box_content = input_box.text or input_box.get_attribute("textContent") or ""
    if not box_content.strip():
        log.debug("execCommand produced no content — chunked send_keys fallback.")
        chunk = 2000
        for i in range(0, len(text), chunk):
            input_box.send_keys(text[i:i + chunk])
            time.sleep(0.1)
        time.sleep(0.5)
        box_content = input_box.text or input_box.get_attribute("textContent") or ""

    log.info("Input box contains %d chars (prompt was %d chars).", len(box_content), len(text))

    try:
        btn = driver.find_element(By.CSS_SELECTOR, '[data-testid="send-button"]')
        driver.execute_script("arguments[0].click();", btn)
        log.info("Clicked send button.")
    except NoSuchElementException:
        input_box.send_keys(Keys.RETURN)
        log.info("Submitted via Enter key.")


# ---------------------------------------------------------------------------
# Response extraction
# ---------------------------------------------------------------------------

def _is_generating(driver: webdriver.Chrome) -> bool:
    if driver.find_elements(By.CSS_SELECTOR, '[data-testid="stop-button"]'):
        return True
    if driver.find_elements(By.CSS_SELECTOR, 'button[aria-label*="Stop"]'):
        return True
    return False


def _generation_started(driver: webdriver.Chrome) -> bool:
    return bool(
        driver.find_elements(By.CSS_SELECTOR, '[data-message-author-role="assistant"]')
    )


def _extract_last_response(driver: webdriver.Chrome) -> str:
    messages = driver.find_elements(By.CSS_SELECTOR, '[data-message-author-role="assistant"]')
    if messages:
        text = messages[-1].text.strip()
        if text:
            return text

    turns = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid*="conversation-turn"]')
    if turns:
        text = turns[-1].text.strip()
        if text:
            return text

    blocks = driver.find_elements(By.CSS_SELECTOR, ".markdown.prose")
    if blocks:
        return blocks[-1].text.strip()

    return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_prompt_and_wait(
    driver: webdriver.Chrome,
    prompt: str,
    wait_seconds: int = 120,
) -> str:
    """Type *prompt* into the ChatGPT input box and wait for the full response.

    Returns the response text, or an empty string if nothing could be extracted.
    """
    input_box = _get_input_box(driver, wait_seconds=30)
    _send_text_to_box(driver, input_box, prompt)

    log.info("Waiting for ChatGPT to start responding (up to 90 s)...")
    start_deadline = time.monotonic() + 90
    while time.monotonic() < start_deadline:
        if _generation_started(driver) or _is_generating(driver):
            break
        time.sleep(0.5)
    else:
        log.warning("ChatGPT did not start responding within 90 s — proceeding anyway.")

    log.info("Response started — waiting for completion...")
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if not _is_generating(driver):
            break
        time.sleep(1)
    else:
        log.warning("Timed out after %ds waiting for ChatGPT.", wait_seconds)

    time.sleep(1)   # allow DOM to settle
    return _extract_last_response(driver)
