"""Quick smoke test: open ChatGPT with the saved session and send one prompt."""
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
PROMPT = "Reply with exactly: SESSION OK"
WAIT = 60


def main():
    options = Options()
    options.add_argument(f"--user-data-dir={CHROME_PROFILE}")
    options.add_argument("--profile-directory=Default")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    try:
        print("Opening ChatGPT...")
        driver.get(CHATGPT_URL)

        wait = WebDriverWait(driver, WAIT)

        # Confirm we are NOT on a login page
        title = driver.title
        print(f"Page title: {title}")
        if "log in" in title.lower() or "sign in" in title.lower():
            print("FAIL — login page appeared. Session cookie not loaded.")
            return

        print("Session loaded. Locating textarea...")
        textarea = wait.until(
            EC.presence_of_element_located((By.ID, "prompt-textarea"))
        )

        driver.execute_script(
            "arguments[0].focus(); document.execCommand('insertText', false, arguments[1]);",
            textarea,
            PROMPT,
        )
        print("Prompt inserted. Submitting...")

        # Click the send button
        send_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='send-button']"))
        )
        send_btn.click()

        print("Waiting for response...")
        time.sleep(5)
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[data-message-author-role='assistant']")
            )
        )
        time.sleep(3)

        messages = driver.find_elements(
            By.CSS_SELECTOR, "[data-message-author-role='assistant']"
        )
        response = messages[-1].text if messages else "(no response found)"
        print(f"\nResponse: {response}")
        print("\nSUCCESS — session is working from Selenium.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
