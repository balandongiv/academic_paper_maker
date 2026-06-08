"""Loop data_test.csv, send each Abstract Note to ChatGPT, save result.

For each row in data_test.csv:
  - Prepends the prompt from promp_check_blink.md
  - Sends to ChatGPT UI via Selenium
  - Extracts the response
  - Saves it to a new column 'chatgpt_blink_check' in data_test.csv

Rows already filled are skipped (safe to re-run after interruption).
"""

from __future__ import annotations

import sys
import time
import logging
from pathlib import Path

# Make stdout/stderr UTF-8 safe on Windows (handles emoji in responses)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

_ROOT         = Path(__file__).resolve().parent.parent
CHROME_EXE    = r"C:\Users\balan\AppData\Local\Google\Chrome\Application\chrome.exe"
CHROMEDRIVER  = str(_ROOT / "apm" / "browser" / "chromedriver.exe")
PROFILE_DIR   = r"C:\selenium\chrome-profile"
CHATGPT_URL   = "https://chatgpt.com/"
SCREENSHOT_DIR = _ROOT / "output" / "screenshots"

CSV_PATH      = _ROOT / "data_test.csv"
CSV_BACKUP    = _ROOT / "data_test_blink_results.csv"   # fallback if CSV_PATH is locked
PROMPT_PATH   = _ROOT / "promp_check_blink.md"
RESULT_COL    = "chatgpt_blink_check"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_chromedriver() -> str:
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        return ChromeDriverManager().install()
    except Exception as exc:
        log.warning("webdriver-manager failed (%s). Using bundled.", exc)
        return CHROMEDRIVER


def _screenshot(driver: webdriver.Chrome, name: str) -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_DIR / f"{name}.png"
    driver.save_screenshot(str(path))
    log.debug("Screenshot: %s", path)


# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------

def build_driver() -> webdriver.Chrome:
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)
    options = Options()
    options.binary_location = CHROME_EXE
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("detach", True)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-popup-blocking")

    service = Service(executable_path=_resolve_chromedriver())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    driver.maximize_window()
    return driver


# ---------------------------------------------------------------------------
# Login check
# ---------------------------------------------------------------------------

def _is_logged_in(driver: webdriver.Chrome) -> bool:
    if "chatgpt.com" not in driver.current_url:
        return False
    if driver.find_elements(By.XPATH, "//*[contains(text(),'Log in or sign up')]"):
        return False
    if driver.find_elements(By.XPATH,
            "//*[self::a or self::button][contains(normalize-space(.),'Log in')]"):
        return False
    if driver.find_elements(By.XPATH,
            "//*[self::a or self::button][contains(normalize-space(.),'Sign up')]"):
        return False
    return bool(driver.find_elements(By.ID, "prompt-textarea"))


def ensure_logged_in(driver: webdriver.Chrome) -> None:
    _screenshot(driver, "login_check")
    if _is_logged_in(driver):
        log.info("Already logged in.")
        return

    print()
    print("=" * 60)
    print("  ACTION REQUIRED: Log in to ChatGPT in the Chrome window.")
    print("  Click 'Continue with Google', complete the flow,")
    print("  then press Enter here.")
    print("=" * 60)
    try:
        input("  >> Press Enter when logged in: ")
    except EOFError:
        pass
    time.sleep(2)
    _screenshot(driver, "login_after")
    if not _is_logged_in(driver):
        raise RuntimeError("Not logged in after confirmation — aborting.")
    log.info("Login confirmed.")


# ---------------------------------------------------------------------------
# Send prompt and get response
# ---------------------------------------------------------------------------

def _new_chat(driver: webdriver.Chrome) -> None:
    """Navigate to a fresh chat page."""
    driver.get(CHATGPT_URL)
    # Wait for the textarea to appear
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "prompt-textarea"))
        )
    except TimeoutException:
        time.sleep(3)


def _get_input_box(driver: webdriver.Chrome):
    wait = WebDriverWait(driver, 30)
    try:
        return wait.until(EC.element_to_be_clickable((By.ID, "prompt-textarea")))
    except TimeoutException:
        return wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[contenteditable='true']"))
        )


def _box_text(driver: webdriver.Chrome, input_box) -> str:
    """Read back whatever is currently in the textarea."""
    return driver.execute_script("return arguments[0].innerText || '';", input_box)


def _send_text(driver: webdriver.Chrome, prompt: str, row_idx: int) -> None:
    input_box = _get_input_box(driver)
    driver.execute_script("arguments[0].scrollIntoView(true);", input_box)
    time.sleep(0.3)

    # --- Method 1: ClipboardEvent paste (best for ProseMirror) ---
    driver.execute_script("""
        const el = arguments[0];
        const text = arguments[1];
        el.focus();
        const dt = new DataTransfer();
        dt.setData('text/plain', text);
        el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true}));
    """, input_box, prompt)
    time.sleep(1.0)

    # Verify text landed; fall back to execCommand if the box is still empty
    if len(_box_text(driver, input_box).strip()) < 10:
        log.warning("Paste event produced no text — trying execCommand fallback.")
        driver.execute_script(
            "arguments[0].focus(); document.execCommand('insertText', false, arguments[1]);",
            input_box, prompt)
        time.sleep(1.0)

    # Final check: if still empty, use send_keys (slow but always works)
    if len(_box_text(driver, input_box).strip()) < 10:
        log.warning("execCommand also empty — using send_keys fallback.")
        driver.execute_script("arguments[0].focus();", input_box)
        input_box.send_keys(prompt)
        time.sleep(1.0)

    actual = _box_text(driver, input_box)
    log.info("Row %d: textarea has %d chars.", row_idx, len(actual))
    _screenshot(driver, f"row_{row_idx:02d}_before_send")

    if len(actual.strip()) < 10:
        raise RuntimeError(f"Row {row_idx}: Could not type text into ChatGPT textarea.")

    try:
        btn = driver.find_element(By.CSS_SELECTOR, '[data-testid="send-button"]')
        driver.execute_script("arguments[0].click();", btn)
        log.info("Row %d: clicked send button.", row_idx)
    except NoSuchElementException:
        input_box.send_keys(Keys.RETURN)
        log.info("Row %d: submitted via Enter.", row_idx)


def _is_generating(driver: webdriver.Chrome) -> bool:
    if driver.find_elements(By.CSS_SELECTOR, '[data-testid="stop-button"]'):
        return True
    if driver.find_elements(By.CSS_SELECTOR, 'button[aria-label*="Stop"]'):
        return True
    return False


def _count_assistant_messages(driver: webdriver.Chrome) -> int:
    return len(driver.find_elements(By.CSS_SELECTOR, '[data-message-author-role="assistant"]'))


def _wait_for_response(driver: webdriver.Chrome, row_idx: int,
                       msg_count_before: int, timeout: int = 120) -> str:
    log.info("Waiting for new response (existing msgs: %d)...", msg_count_before)

    # Wait up to 20 s for a NEW assistant message to appear
    for _ in range(40):
        if _count_assistant_messages(driver) > msg_count_before or _is_generating(driver):
            break
        time.sleep(0.5)

    # Wait for streaming to finish
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _is_generating(driver):
            break
        time.sleep(1)
    else:
        log.warning("Row %d: timed out.", row_idx)

    time.sleep(1)
    _screenshot(driver, f"row_{row_idx:02d}_response")

    messages = driver.find_elements(
        By.CSS_SELECTOR, '[data-message-author-role="assistant"]')
    if messages:
        text = messages[-1].text.strip()
        if text:
            return text

    turns = driver.find_elements(
        By.CSS_SELECTOR, 'article[data-testid*="conversation-turn"]')
    if turns:
        text = turns[-1].text.strip()
        if text:
            return text

    blocks = driver.find_elements(By.CSS_SELECTOR, '.markdown.prose')
    if blocks:
        return blocks[-1].text.strip()

    return "(extraction failed)"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _save_csv(df: pd.DataFrame) -> None:
    """Save to CSV_PATH; fall back to CSV_BACKUP if the file is locked."""
    for attempt, path in enumerate([CSV_PATH, CSV_BACKUP], 1):
        try:
            df.to_csv(path, index=False, encoding="utf-8-sig")
            if attempt > 1:
                print(f"  [saved to backup] {path}")
            return
        except PermissionError:
            if attempt == 1:
                log.warning("data_test.csv is locked (open in another app?). Saving to backup.")
    log.error("Could not save to either path.")


def load_prompt() -> str:
    text = PROMPT_PATH.read_text(encoding="utf-8").strip()
    return text


def main() -> None:
    prompt_prefix = load_prompt()
    log.info("Prompt prefix: %s", prompt_prefix[:80])

    # Load CSV
    df = pd.read_csv(CSV_PATH, encoding="latin1")
    if RESULT_COL not in df.columns:
        df[RESULT_COL] = ""
    # Ensure string dtype so assigning long text doesn't trigger FutureWarning
    df[RESULT_COL] = df[RESULT_COL].astype(str).replace("nan", "")

    pending = df[df[RESULT_COL].isna() | (df[RESULT_COL] == "")].index.tolist()
    log.info("Rows to process: %d  (already done: %d)", len(pending), len(df) - len(pending))

    if not pending:
        print("All rows already processed.")
        return

    driver = build_driver()
    try:
        driver.get(CHATGPT_URL)
        time.sleep(3)
        ensure_logged_in(driver)

        for row_idx in pending:
            abstract = df.at[row_idx, "Abstract Note"]
            if pd.isna(abstract) or str(abstract).strip() == "":
                log.info("Row %d: empty abstract — skipping.", row_idx)
                df.at[row_idx, RESULT_COL] = "Ignore"
                _save_csv(df)
                continue

            full_prompt = f"{prompt_prefix}\n\n{abstract}"
            print()
            print(f"[Row {row_idx}] Combined prompt ({len(full_prompt)} chars total):")
            print(f"  PROMPT : {prompt_prefix}")
            print(f"  ABSTRACT: {str(abstract)[:120]}...")

            _new_chat(driver)
            msg_count_before = _count_assistant_messages(driver)
            _send_text(driver, full_prompt, row_idx)
            response = _wait_for_response(driver, row_idx, msg_count_before)

            df.at[row_idx, RESULT_COL] = response

            # Save immediately after each row
            _save_csv(df)
            log.info("Row %d saved.", row_idx)

            print(f"  Response preview: {response[:200]}...")
            print()

            # Brief pause between rows to be polite to ChatGPT
            if row_idx != pending[-1]:
                time.sleep(3)

    finally:
        try:
            driver.service.stop()
        except Exception:
            pass

    print()
    print("=" * 60)
    out = CSV_BACKUP if not CSV_PATH.exists() else CSV_PATH
    print(f"Done. Results saved to {out}")
    print("=" * 60)

    # Print summary
    for row_idx in pending:
        resp = df.at[row_idx, RESULT_COL]
        print(f"\n[Row {row_idx}]")
        print(resp[:300])


if __name__ == "__main__":
    main()
