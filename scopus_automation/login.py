"""Scopus login: check session and wait for user confirmation if needed."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

SCOPUS_HOME = "https://www.scopus.com"


def _is_logged_in(driver) -> bool:
    """
    Quick check using JavaScript: look for 'Sign in' text on the page.
    If 'Sign in' is visible the user is NOT logged in.
    """
    try:
        result = driver.execute_script(
            "var t = document.body ? document.body.innerText : '';"
            "return !t.includes('Sign in') && !t.includes('Log in') && t.length > 200;"
        )
        return bool(result)
    except Exception:
        return False


def ensure_logged_in(driver, config) -> bool:
    """
    1. Navigate to Scopus.
    2. If already logged in (no 'Sign in' button) — proceed immediately.
    3. If login is needed — show prompt and wait for user to press Enter.
    """
    log.info("Opening Scopus...")
    try:
        driver.get(SCOPUS_HOME)
        driver.maximize_window()
    except Exception as exc:
        log.warning("Could not load Scopus: %s", exc)

    # Short wait for page JS to settle
    import time
    time.sleep(3)

    if _is_logged_in(driver):
        log.info("Already logged in — skipping login prompt.")
        print("\n[OK] Scopus session active — proceeding.\n")
        return True

    # Login required — ask user
    print()
    print("=" * 60)
    print("  ACTION: Log into Scopus in the Chrome window")
    print("=" * 60)
    print()
    print("  1. Click 'Sign in' in Chrome.")
    print("  2. Enter your credentials.")
    print("  3. Tick 'Keep me signed in' so future runs skip this.")
    print()
    print("  Once you are back on the Scopus page,")
    print("  press Enter here to continue.")
    print()

    input("  >> Press Enter when ready: ")
    print()
    log.info("User confirmed — proceeding.")
    return True
