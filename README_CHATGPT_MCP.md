# ChatGPT UI Access Across Repositories

Treat the ChatGPT web UI as a local tool provider: keep a dedicated Chrome profile logged in, then drive it with Selenium from any repository on the same computer. In MCP terms, the browser session is the service; each project is just a client that calls `apm.chatgpt_ui` or copies the Selenium driver pattern.

**For agentic LLMs:** Always run the session test in section 3 before attempting any ChatGPT automation. If the test fails, follow section 8 before writing any integration code.

---

## 1. Chrome Profile — Log In Once

The Selenium profile is stored at a fixed path so all repositories share the same cookies:

```text
C:\selenium\chatgpt-profile
```

This is **not** one of Chrome's regular user profiles (`Default`, `Profile 1`, etc.). It is a standalone profile directory created specifically for Selenium.

Verified working values (confirmed on this machine):

```text
Chrome exe:      C:\Program Files\Google\Chrome\Application\chrome.exe
Profile dir:     C:\selenium\chatgpt-profile
Profile name:    Default
Full path:       C:\selenium\chatgpt-profile\Default
```

### How to log in (one-time per computer)

Close all Chrome windows first — the profile cannot be shared between processes. Then run:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
    --user-data-dir="C:\selenium\chatgpt-profile" `
    --profile-directory="Default" `
    https://chatgpt.com
```

Complete sign-in. Once the ChatGPT home screen loads, close that Chrome window. The session cookie is now written to:

```text
C:\selenium\chatgpt-profile\Default\Cookies
```

All future Selenium runs from any repository read that cookie automatically.

---

## 2. Python Dependencies

Any Python environment on this machine can drive ChatGPT. Install once per environment:

```powershell
pip install selenium webdriver-manager
```

`webdriver-manager` downloads the correct ChromeDriver version automatically — no manual ChromeDriver install needed.

---

## 3. Session Test — Run This First

Before writing any integration code, verify the saved session is still valid. This is the authoritative smoke test.

**Close all Chrome windows before running.**

```powershell
cd C:\Users\balan\IdeaProjects\academic_paper_maker
python test_chatgpt_session.py
```

Expected output (verified passing):

```text
Opening ChatGPT...
Page title: ChatGPT
Session loaded. Locating textarea...
Prompt inserted. Submitting...
Waiting for response...

Response: SESSION OK

SUCCESS — session is working from Selenium.
```

If `Page title` contains "log in" or "sign in", the cookie has expired — re-login following section 1.

Source: `test_chatgpt_session.py` in this repository root.

---

## 4. Minimal Integration Pattern

This is the verified working pattern. Copy it into any repository on this machine.

```python
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
WAIT_SECONDS = 60


def send_to_chatgpt(prompt: str) -> str:
    options = Options()
    options.add_argument(f"--user-data-dir={CHROME_PROFILE}")
    options.add_argument("--profile-directory=Default")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    try:
        driver.get(CHATGPT_URL)
        wait = WebDriverWait(driver, WAIT_SECONDS)

        textarea = wait.until(
            EC.presence_of_element_located((By.ID, "prompt-textarea"))
        )
        driver.execute_script(
            "arguments[0].focus(); document.execCommand('insertText', false, arguments[1]);",
            textarea,
            prompt,
        )

        send_btn = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[data-testid='send-button']")
            )
        )
        send_btn.click()

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
        return messages[-1].text if messages else ""
    finally:
        driver.quit()
```

Known-good CSS selectors (verified 2026-06-12):

| Element | Selector |
|---|---|
| Textarea | `#prompt-textarea` (by ID) |
| Send button | `button[data-testid='send-button']` |
| Assistant reply | `[data-message-author-role='assistant']` |

If a selector stops working, the ChatGPT UI has been updated. Inspect the live page manually, update the selector, and re-run the session test.

---

## 5. What Code to Write — Agentic Integration Checklist

When integrating ChatGPT UI access into a new project, write these components in order:

### 5.1 Session guard (write first)

Before sending any prompt, check that the page loaded as the home screen — not a login page. Abort with a clear error if the session is dead so the agent knows to re-login rather than silently failing.

```python
def _assert_session(driver):
    title = driver.title.lower()
    if "log in" in title or "sign in" in title:
        raise RuntimeError(
            "ChatGPT session expired. Close Chrome, re-login via section 1 of "
            "README_CHATGPT_MCP.md, then retry."
        )
```

### 5.2 Prompt sender (the core function)

The `send_to_chatgpt(prompt: str) -> str` function from section 4. One driver per call, quit in `finally`.

### 5.3 Response wait (handle streaming)

ChatGPT streams its response. The safe pattern is:
1. Wait for the first assistant message element to appear.
2. Sleep 3–5 seconds for streaming to finish.
3. Re-query all assistant messages and take the last one.

Do **not** rely on a single fixed sleep — streaming time varies with response length.

### 5.4 Retry wrapper (optional but recommended for batch work)

```python
import time

def send_with_retry(prompt: str, retries: int = 3, delay: int = 10) -> str:
    for attempt in range(retries):
        try:
            return send_to_chatgpt(prompt)
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(delay)
```

### 5.5 Profile lock guard (required for batch work)

Only one Selenium process may use the profile at a time. If running multiple workers, use a file-based lock:

```python
import fcntl  # Unix; use msvcrt on Windows

# Or use threading.Lock() if workers are in the same process.
```

On Windows, the simplest guard is to catch `SessionNotCreatedException` and retry after killing stale Chrome:

```python
from selenium.common.exceptions import SessionNotCreatedException
import subprocess

def kill_chrome():
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
```

---

## 6. Access Via This Repository's Wrapper

If another repository wants `academic_paper_maker`'s full pipeline (SQLite tracking, batch processing, JSON output), set `PYTHONPATH`:

```powershell
$env:PYTHONPATH = "C:\Users\balan\IdeaProjects\academic_paper_maker\src"
python -c "
from apm.chatgpt_ui.selenium_client import ChatGPTClient
client = ChatGPTClient()
print(client.send('Explain p-value in one sentence.'))
"
```

The wrapper reads `setting/chatgpt_ui/config.yaml`. Relevant keys:

```yaml
selenium:
  chrome_exe: "C:/Program Files/Google/Chrome/Application/chrome.exe"
  chrome_profile: "C:/selenium/chatgpt-profile"
  wait_seconds: 60
```

---

## 7. Multi-Repository Rules

| Concern | Rule |
|---|---|
| Profile lock | Only one Chrome process may use `C:\selenium\chatgpt-profile` at a time. Close any manual Chrome window before starting Selenium. |
| Cookie expiry | Sessions last weeks. Re-run section 1 login when a login page appears during automation. |
| Multiple computers | Each computer needs its own `C:\selenium\chatgpt-profile` with its own one-time login. Cookies are machine-local. |
| `SessionNotCreatedException` | A previous run left the profile locked. Run `Stop-Process -Name chrome -Force` then retry. |

---

## 8. Troubleshooting

### Login page appears during automation

Cookie expired. Fix:

```powershell
Stop-Process -Name chrome -Force
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
    --user-data-dir="C:\selenium\chatgpt-profile" `
    --profile-directory="Default" `
    https://chatgpt.com
```

Log in, close Chrome, re-run.

### `SessionNotCreatedException: Chrome instance exited`

```powershell
Stop-Process -Name chrome -Force
```

Then re-run.

### Prompt text not appearing in textarea

The `execCommand` approach failed. Fallback:

```python
textarea.send_keys(prompt)
```

### Selector stopped matching

The ChatGPT UI was updated. Open the page manually in the Selenium profile, inspect the element, find the new selector, update the code, and re-run the session test.

### ChromeDriver version mismatch

`webdriver-manager` handles this automatically. If offline:

```text
https://googlechromelabs.github.io/chrome-for-testing/
```

Download the matching `chromedriver.exe` and pass its path to `Service(executable_path=r"C:\path\to\chromedriver.exe")`.
