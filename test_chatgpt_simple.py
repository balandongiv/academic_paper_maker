"""Simple, honest ChatGPT-UI smoke test.

Opens a visible Chrome with the saved session, sends one real prompt, waits for
streaming to finish, and prints the actual answer. Reports PASS only if a real
(non-error, non-Cloudflare) answer came back.
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

CHROME_PROFILE = r"C:\selenium\chatgpt-profile"
CHATGPT_URL = "https://chatgpt.com"
PROMPT = "What is 17 + 25? Reply with only the number."
TEXTAREA_WAIT = 180   # allow Cloudflare 'Just a moment' to clear (manual if needed)
STREAM_WAIT = 90      # max time to let the answer finish streaming

ERROR_MARKERS = (
    "something went wrong while generating",
    "error in moderation",
    "you've reached our limit",
)


def wait_for_textarea(driver):
    """Wait for the prompt box, tolerating a Cloudflare interstitial."""
    deadline = time.time() + TEXTAREA_WAIT
    while time.time() < deadline:
        title = driver.title
        if "just a moment" in title.lower():
            print(f"  Cloudflare challenge ('{title}') - "
                  "if a checkbox is shown, CLICK IT in the open window. Waiting...")
            time.sleep(5)
            continue
        if "log in" in title.lower() or "sign in" in title.lower():
            raise RuntimeError("Login page appeared - session cookie expired.")
        try:
            el = driver.find_element(By.ID, "prompt-textarea")
            if el.is_displayed():
                print(f"  Page title: {title}")
                return el
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError("Textarea never appeared (Cloudflare or UI change).")


def wait_for_answer(driver):
    """Let the assistant message stream, return when its text stops changing."""
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "[data-message-author-role='assistant']")
        )
    )
    last, stable, deadline = "", 0, time.time() + STREAM_WAIT
    while time.time() < deadline:
        msgs = driver.find_elements(
            By.CSS_SELECTOR, "[data-message-author-role='assistant']"
        )
        text = msgs[-1].text if msgs else ""
        if text and text == last:
            stable += 1
            if stable >= 3:          # ~3s unchanged => streaming done
                return text
        else:
            stable = 0
        last = text
        time.sleep(1)
    return last


def main():
    options = Options()
    options.add_argument(f"--user-data-dir={CHROME_PROFILE}")
    options.add_argument("--profile-directory=Default")
    # Reduce automation fingerprint so Cloudflare is less likely to challenge.
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    print("Launching Chrome (visible)...")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )
    try:
        print("Opening ChatGPT...")
        driver.get(CHATGPT_URL)

        textarea = wait_for_textarea(driver)

        print(f"Sending prompt: {PROMPT!r}")
        driver.execute_script(
            "arguments[0].focus(); document.execCommand('insertText', false, arguments[1]);",
            textarea, PROMPT,
        )
        send = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[data-testid='send-button']")
            )
        )
        send.click()

        print("Waiting for the answer to finish streaming...")
        answer = wait_for_answer(driver)

        print("\n" + "=" * 50)
        print("CHATGPT RESPONSE:")
        print(answer if answer else "(empty)")
        print("=" * 50)

        low = answer.lower()
        if not answer:
            print("RESULT: FAIL - empty response.")
        elif any(m in low for m in ERROR_MARKERS):
            print("RESULT: FAIL - ChatGPT returned an error/limit message.")
        else:
            print("RESULT: PASS - browser opened, prompt sent, real answer printed.")
    finally:
        time.sleep(2)
        driver.quit()


if __name__ == "__main__":
    main()
