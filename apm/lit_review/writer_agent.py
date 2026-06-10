"""ChatGPT UI writing agent — sends prompts via Selenium, returns responses.

Wraps apm.chatgpt_ui.selenium_client for the literature-review pipeline.
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from pathlib import Path

from apm.chatgpt_ui.selenium_client import (
    build_driver,
    ensure_logged_in,
    navigate_to_new_chat,
    send_prompt_and_wait,
)

log = logging.getLogger(__name__)

CHROMEDRIVER_BUNDLED = str(
    Path(__file__).resolve().parent.parent.parent / "apm" / "browser" / "chromedriver.exe"
)


# ---------------------------------------------------------------------------
# Driver lifecycle
# ---------------------------------------------------------------------------

class WriterAgent:
    """Stateful wrapper around a Selenium Chrome session for ChatGPT writing."""

    def __init__(self, selenium_cfg, chromedriver_path: str = CHROMEDRIVER_BUNDLED):
        self._cfg = selenium_cfg
        self._chromedriver = chromedriver_path
        self._driver = None

    @staticmethod
    def _kill_chrome_processes() -> None:
        """Kill any lingering Chrome/chromedriver processes before a fresh launch."""
        for proc in ("chrome.exe", "chromedriver.exe"):
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", proc],
                    capture_output=True, check=False,
                )
            except Exception:
                pass
        time.sleep(3)

    def _launch_browser(self) -> None:
        """Build a driver, load chatgpt.com, and verify login. Retries up to 3 times."""
        self._kill_chrome_processes()
        for attempt in range(1, 4):
            try:
                self._driver = build_driver(self._cfg, self._chromedriver)
                self._driver.get("https://chatgpt.com/")
                time.sleep(3)
                ensure_logged_in(self._driver)
                return
            except Exception as exc:
                log.warning("Chrome launch attempt %d/3 failed: %s", attempt, exc)
                try:
                    if self._driver:
                        self._driver.quit()
                except Exception:
                    pass
                self._driver = None
                self._kill_chrome_processes()
                if attempt < 3:
                    log.info("Waiting 10s before retry...")
                    time.sleep(10)
        raise RuntimeError("Chrome failed to launch after 3 attempts.")

    def start(self) -> None:
        if self._driver is not None:
            return
        log.info("Starting Chrome for ChatGPT writing agent...")
        self._launch_browser()
        log.info("ChatGPT writing agent ready.")

    def stop(self) -> None:
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
            log.info("Chrome closed.")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()

    def _restart(self) -> None:
        """Quit Chrome, clean the profile, and launch a fresh instance.

        Called before every new-chat navigation so the renderer never
        accumulates enough DOM state to become unresponsive.
        """
        self.stop()
        self._launch_browser()

    # ------------------------------------------------------------------
    # Core send method
    # ------------------------------------------------------------------

    def send(self, prompt: str, new_chat: bool = True) -> str:
        """Send *prompt* to ChatGPT and return the response text."""
        if self._driver is None:
            raise RuntimeError("Agent not started — call start() or use as context manager.")
        if new_chat:
            # Restart Chrome before every new conversation so each send
            # begins with a clean renderer (no accumulated DOM state).
            self._restart()
            navigate_to_new_chat(self._driver)
            time.sleep(2)
        response = send_prompt_and_wait(
            self._driver, prompt, wait_seconds=self._cfg.wait_seconds
        )
        if not response:
            raise ValueError("ChatGPT returned an empty response.")
        return response

    # ------------------------------------------------------------------
    # High-level writing helpers
    # ------------------------------------------------------------------

    def write_paragraph(self, prompt: str) -> str:
        log.info("Sending writing prompt to ChatGPT...")
        return self.send(prompt, new_chat=True)

    def check_consistency(self, prompt: str) -> str:
        """Send consistency-check prompt; return the prose response from ChatGPT."""
        log.info("Sending consistency-check prompt to ChatGPT...")
        return self.send(prompt, new_chat=True)

    def revise_paragraph(self, prompt: str) -> str:
        log.info("Sending revision prompt to ChatGPT...")
        return self.send(prompt, new_chat=True)

    def write_dataset_comparison(self, prompt: str) -> str:
        log.info("Sending dataset comparison prompt to ChatGPT...")
        return self.send(prompt, new_chat=True)


# ---------------------------------------------------------------------------
# Consistency verdict detector
# ---------------------------------------------------------------------------

def detect_pass(auditor_response: str) -> bool:
    """Return True if the auditor prose response indicates PASS."""
    first_lines = auditor_response.strip()[:300].upper()
    if "VERDICT: PASS" in first_lines:
        return True
    if "VERDICT: FAIL" in first_lines:
        return False
    # Fallback: treat as FAIL if any issue language is present
    fail_signals = ["issue", "incorrect", "unsupported", "mismatch", "inaccurate", "error", "wrong"]
    lower = auditor_response.lower()
    return not any(sig in lower for sig in fail_signals)


# ---------------------------------------------------------------------------
# Response cleaner
# ---------------------------------------------------------------------------

def clean_paragraph_response(text: str) -> str:
    """Strip markdown artifacts from ChatGPT responses intended for LaTeX."""
    # Remove ```latex or ``` blocks
    text = re.sub(r"```(?:latex|tex)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*", "", text)
    # Remove "Here is the paragraph:" type preambles
    text = re.sub(
        r"^(here is[^:]*:|here's[^:]*:|below is[^:]*:|the paragraph[^:]*:)\s*",
        "",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    # Remove trailing whitespace per line
    lines = [ln.rstrip() for ln in text.splitlines()]
    return "\n".join(lines).strip()
