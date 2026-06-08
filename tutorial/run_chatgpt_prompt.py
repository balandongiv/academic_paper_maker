"""Send a single prompt to ChatGPT and print the response.

This is a minimal example that delegates all logic to apm.chatgpt_ui.
For batch processing of an entire CSV, use:

    python -m apm.chatgpt_ui.run_batch

Usage:
    python tutorial/run_chatgpt_prompt.py
    python tutorial/run_chatgpt_prompt.py "Explain gradient descent in 3 bullet points"
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from apm.chatgpt_ui.config import load_config
from apm.chatgpt_ui.selenium_client import (
    build_driver,
    ensure_logged_in,
    navigate_to_new_chat,
    send_prompt_and_wait,
)

_DEFAULT_CONFIG  = _ROOT / "setting" / "chatgpt_ui" / "config.yaml"
_BUNDLED_DRIVER  = str(_ROOT / "apm" / "browser" / "chromedriver.exe")
_DEFAULT_PROMPT  = (
    "List 3 key differences between supervised and unsupervised machine learning. "
    "Use bullet points."
)


def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip() or _DEFAULT_PROMPT

    print(f"\nPrompt: {prompt}\n")

    cfg    = load_config(_DEFAULT_CONFIG)
    driver = build_driver(cfg.selenium, chromedriver_path=_BUNDLED_DRIVER, detach=True)

    try:
        driver.get("https://chatgpt.com/")
        time.sleep(3)
        ensure_logged_in(driver)
        navigate_to_new_chat(driver)

        response = send_prompt_and_wait(
            driver,
            prompt,
            wait_seconds=cfg.selenium.wait_seconds,
        )

        print("=" * 60)
        print("ChatGPT Response")
        print("=" * 60)
        print(response)
        print("=" * 60)

    finally:
        try:
            driver.service.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
