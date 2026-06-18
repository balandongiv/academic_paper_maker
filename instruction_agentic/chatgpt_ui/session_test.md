# ChatGPT Selenium Session Test — Agent Instructions

**Last verified:** 2026-06-14  
**Script:** `test_chatgpt_session.py` (repo root)  
**Purpose:** Verify the Selenium Chrome profile can open ChatGPT, send a prompt, and receive a response — without human login interaction.

---

## Environment

| Item | Value |
|---|---|
| Conda environment | `base` (`C:\Users\balan\anaconda3`) |
| Python version | 3.13.5 |
| selenium | 4.44.0 |
| webdriver-manager | 4.1.2 |
| Chrome exe | `C:\Program Files\Google\Chrome\Application\chrome.exe` |
| Selenium profile dir | `C:\selenium\chatgpt-profile` |
| Profile name | `Default` |

---

## How to Run the Session Test

**Step 1 — Kill any open Chrome windows (required — profile can only have one process):**
```powershell
Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
```

**Step 2 — Run the test:**
```powershell
cd C:\Users\balan\IdeaProjects\academic_paper_maker
python test_chatgpt_session.py
```

**Expected output:**
```
Opening ChatGPT...
Page title: ChatGPT
Session loaded. Locating textarea...
Prompt inserted. Submitting...
Waiting for response...

Response: SESSION OK

SUCCESS — session is working from Selenium.
```

---

## Why the Test Succeeds

1. **Pre-authenticated Chrome profile.** A one-time manual login was done with the dedicated Selenium profile at `C:\selenium\chatgpt-profile`. The session cookie is stored in `C:\selenium\chatgpt-profile\Default\Cookies` and reused automatically on every Selenium run.

2. **No profile lock conflict.** Killing Chrome before launching Selenium prevents `SessionNotCreatedException`, which occurs when another Chrome process holds the profile lock.

3. **ChromeDriver is auto-managed.** `webdriver-manager` downloads the correct `chromedriver.exe` for the installed Chrome version — no manual version pinning needed.

4. **CSS selectors match the live ChatGPT UI (verified 2026-06-14):**

| Element | Selector |
|---|---|
| Textarea | `#prompt-textarea` |
| Send button | `button[data-testid='send-button']` |
| Assistant reply | `[data-message-author-role='assistant']` |

5. **Streaming wait is handled.** The script waits 5 s after submit, waits for the assistant message element, then waits 3 more s before reading — handles variable-length streamed responses.

---

## If the Test Fails

### Login page appears (`Page title` contains "log in" or "sign in")
Cookie has expired. Re-authenticate manually once:
```powershell
Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
    --user-data-dir="C:\selenium\chatgpt-profile" `
    --profile-directory="Default" `
    https://chatgpt.com
```
Log in, wait for the ChatGPT home screen, close Chrome, then re-run the test.

### `SessionNotCreatedException: Chrome instance exited`
A previous run left the profile locked:
```powershell
Stop-Process -Name chrome -Force
```
Then re-run.

### Prompt text does not appear in textarea
The `execCommand` injection failed. Fallback in `test_chatgpt_session.py`:
```python
textarea.send_keys(prompt)
```

### Selector stopped matching
The ChatGPT UI was updated. Open `https://chatgpt.com` manually in the Selenium profile, inspect the element, find the new selector, update `test_chatgpt_session.py`, and re-run.

---

## Replication Checklist for Future Agents

- [ ] `Stop-Process -Name chrome -Force` before launching Selenium
- [ ] Run in the `base` conda environment (Python 3.13.5)
- [ ] `selenium` and `webdriver-manager` installed (`pip install selenium webdriver-manager`)
- [ ] Chrome at `C:\Program Files\Google\Chrome\Application\chrome.exe`
- [ ] Profile at `C:\selenium\chatgpt-profile\Default\Cookies` exists (if not, do one-time login above)
- [ ] Run `python test_chatgpt_session.py` and confirm `SUCCESS` line in output
