"""Feature 1: Search Scopus advanced search and export results as RIS."""

from __future__ import annotations

import csv
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    WebDriverException,
)

from .browser import wait_for_download, rename_download
from .login import ensure_logged_in
from .config import ScopusConfig

log = logging.getLogger(__name__)

ADVANCED_SEARCH_URLS = [
    "https://www.scopus.com/search/form.uri?display=advanced",
    "https://www.scopus.com/pages/search/publications?type=advanced",
]


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _safe_click(driver, element) -> None:
    try:
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.4)
        driver.execute_script("arguments[0].click();", element)


def _wait(driver, sec: int) -> WebDriverWait:
    return WebDriverWait(driver, sec)


def _current_url(driver) -> str:
    try:
        return driver.current_url
    except Exception:
        return "unknown"


def _log_page_state(driver, label: str) -> None:
    try:
        url   = driver.current_url
        title = driver.title
        log.info("%s | url=%s | title=%s", label, url, title)
        print(f"  [{label}] {url}")
    except Exception as exc:
        log.debug("Could not read page state: %s", exc)


def _wait_for_page_ready(driver, timeout: int = 15) -> None:
    """Wait until document.readyState == 'complete'."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if driver.execute_script("return document.readyState") == "complete":
                return
        except Exception:
            pass
        time.sleep(0.5)


def _log_visible_text(driver) -> None:
    """Print first 400 chars of page body text — helps spot auth walls."""
    try:
        text = driver.execute_script(
            "return document.body ? document.body.innerText.substring(0, 600) : ''"
        )
        if text:
            preview = text[:400].replace("\n", " ").replace("\r", "")
            print(f"  [page-preview] {preview}")
            log.debug("Page text preview: %s", text[:600])
    except Exception:
        pass


def _save_screenshot(driver, name: str) -> None:
    """Save a PNG screenshot for visual debugging."""
    try:
        path = Path("output") / "logs" / f"{name}_{datetime.now().strftime('%H%M%S')}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        driver.save_screenshot(str(path))
        print(f"  [screenshot] {path}")
        log.info("Screenshot saved: %s", path)
    except Exception as exc:
        log.debug("Screenshot failed: %s", exc)


def _find_first(driver, selectors: list, timeout: int = 3):
    """Try each selector; return first found element or None."""
    for by, sel in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, sel))
            )
            log.debug("Found element with selector: %s", sel)
            return el
        except (TimeoutException, Exception):
            continue
    return None


def _query_to_filename(query: str) -> str:
    stem = re.sub(r'[^\w\s-]', '', query.lower())
    stem = re.sub(r'[\s_]+', '_', stem).strip('_')
    return stem[:80] or "scopus_export"


# ---------------------------------------------------------------------------
# Navigate to advanced search
# ---------------------------------------------------------------------------

_SEARCH_FIELD_SELECTORS = [
    (By.CSS_SELECTOR, "div#searchfield"),                          # Scopus 2024+ contenteditable
    (By.CSS_SELECTOR, "textarea#advancedQueryField"),
    (By.XPATH,        "//div[@contenteditable='true']"),
    (By.CSS_SELECTOR, "textarea[aria-label*='search' i]"),
    (By.CSS_SELECTOR, "textarea[placeholder*='search' i]"),
    (By.CSS_SELECTOR, "textarea[name='query']"),
    (By.CSS_SELECTOR, "textarea[name='search']"),
    (By.XPATH,        "//textarea[contains(@class,'search')]"),
    (By.CSS_SELECTOR, "[data-testid='advanced-search-input']"),
    (By.CSS_SELECTOR, ".search-form__input textarea"),
    (By.CSS_SELECTOR, "textarea"),
]

_SEARCH_BTN_SELECTORS = [
    (By.CSS_SELECTOR, "button[type='submit']"),
    (By.XPATH,        "//button[normalize-space(text())='Search']"),
    (By.XPATH,        "//button[contains(text(),'Search')]"),
    (By.CSS_SELECTOR, "[data-testid='search-button']"),
    (By.XPATH,        "//button[contains(@aria-label,'Search')]"),
    (By.CSS_SELECTOR, ".search-button"),
]


def _navigate_to_advanced_search(driver, config: ScopusConfig) -> bool:
    """
    Try each advanced search URL.  Returns True if the search form is found.
    """
    for url in ADVANCED_SEARCH_URLS:
        log.info("Navigating to: %s", url)
        print(f"\n  Trying search URL: {url}")
        try:
            driver.get(url)
        except TimeoutException:
            log.warning("Page load timed out for %s — continuing anyway.", url)
        except WebDriverException as exc:
            log.warning("Navigation error for %s: %s", url, exc)
            continue

        # Wait for JS rendering
        _wait_for_page_ready(driver, timeout=15)
        time.sleep(2)
        _log_page_state(driver, "after-nav")
        _log_visible_text(driver)

        # Try with JS first (most reliable for SPAs)
        field = _find_field_via_js(driver)
        if field:
            log.info("Advanced search form found via JS.")
            return True

        field = _find_first(driver, _SEARCH_FIELD_SELECTORS, timeout=3)
        if field:
            log.info("Advanced search form found.")
            return True

        log.warning("Search form not found at %s", url)

    # Save screenshot for diagnosis
    _save_screenshot(driver, "advanced_search_debug")

    # Manual fallback
    log.warning("Could not find advanced search form at any known URL.")
    print()
    print("  Could not find the Scopus advanced search form automatically.")
    print(f"  Current page: {_current_url(driver)}")
    print()
    print("  Please navigate MANUALLY in Chrome to:")
    print("  https://www.scopus.com/search/form.uri?display=advanced")
    print("  then press Enter here.")
    input("  >> Press Enter when you are on the advanced search page: ")
    print()

    field = _find_field_via_js(driver) or _find_first(driver, _SEARCH_FIELD_SELECTORS, timeout=5)
    return field is not None


def _find_field_via_js(driver):
    """Use JavaScript to locate the search field (contenteditable div or textarea)."""
    try:
        el = driver.execute_script("""
            // Scopus 2024+ uses a contenteditable div#searchfield
            var sf = document.querySelector('div#searchfield');
            if (sf) return sf;
            var ta = document.querySelector('textarea#advancedQueryField');
            if (ta) return ta;
            var ta2 = document.querySelector('textarea');
            if (ta2) return ta2;
            var ce = document.querySelector('[contenteditable="true"]');
            if (ce) return ce;
            return null;
        """)
        return el
    except Exception:
        return None


def _enter_query(driver, query: str) -> None:
    """Fill the advanced search field (textarea or contenteditable div) with the query."""
    field = _find_field_via_js(driver) or _find_first(driver, _SEARCH_FIELD_SELECTORS, timeout=10)
    if field is None:
        raise RuntimeError(
            f"Search input field not found on page: {_current_url(driver)}"
        )

    log.info("Entering query into search field (tag=%s).", field.tag_name)
    tag = field.tag_name.lower()

    if tag in ("input", "textarea"):
        # Standard input: JS click to bypass label overlap, then send_keys
        driver.execute_script("arguments[0].focus();", field)
        time.sleep(0.2)
        field.send_keys(Keys.CONTROL + "a")
        field.send_keys(Keys.DELETE)
        time.sleep(0.1)
        field.send_keys(query)
    else:
        # contenteditable div (Scopus 2024+): use execCommand so framework events fire
        driver.execute_script("""
            var el = arguments[0];
            var q  = arguments[1];
            el.focus();
            // Select all existing text and replace
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);
            document.execCommand('insertText', false, q);
        """, field, query)
        time.sleep(0.2)

    log.info("Query entered: %s", query[:80])


def _submit_search(driver) -> None:
    btn = _find_first(driver, _SEARCH_BTN_SELECTORS, timeout=10)
    if btn is None:
        # Try pressing Enter in the search field
        field = _find_first(driver, _SEARCH_FIELD_SELECTORS, timeout=5)
        if field:
            field.send_keys(Keys.ENTER)
            log.info("Submitted search via Enter key.")
            return
        raise RuntimeError("Could not find search submit button.")
    _safe_click(driver, btn)
    log.info("Search submitted.")


# ---------------------------------------------------------------------------
# Results page
# ---------------------------------------------------------------------------

_RESULT_COUNT_PATTERNS = [
    r"([\d,]+)\s+document",
    r"([\d,]+)\s+result",
    r"About\s+([\d,]+)",
]

_SELECT_ALL_SELECTORS = [
    (By.CSS_SELECTOR, "[data-testid='select-all-results']"),
    (By.CSS_SELECTOR, "input[aria-label*='Select all' i]"),
    (By.XPATH,        "//label[contains(normalize-space(),'Select all')]"),
    (By.XPATH,        "//button[contains(normalize-space(),'Select all')]"),
    (By.CSS_SELECTOR, ".select-all-checkbox input"),
    (By.XPATH,        "//input[@type='checkbox' and (contains(@id,'selectAll') or contains(@name,'selectAll'))]"),
]


def _get_result_count(driver) -> int:
    text = ""
    try:
        text = driver.page_source
    except Exception:
        return 0
    for pat in _RESULT_COUNT_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            digits = m.group(1).replace(",", "").strip()
            if digits:
                try:
                    return int(digits)
                except ValueError:
                    continue
    return 0


def _wait_for_results(driver, timeout: int = 60) -> int:
    """Wait until results page loads and return the count."""
    log.info("Waiting for search results...")
    print("  Waiting for search results to load...")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        _log_page_state(driver, "results-check")
        count = _get_result_count(driver)
        if count > 0:
            log.info("Found %d results.", count)
            print(f"  Found {count} results.")
            return count
        time.sleep(2)
    count = _get_result_count(driver)
    log.warning("Result count after timeout: %d", count)
    return count


def _select_all_documents(driver) -> bool:
    log.info("Selecting all documents...")
    print("  Selecting all documents...")

    # Fast JS text-based click first
    clicked = driver.execute_script("""
        var els = document.querySelectorAll('button, label, a, input[type="checkbox"]');
        for (var i = 0; i < els.length; i++) {
            var t = els[i].textContent.trim().toLowerCase();
            if (t.startsWith('select all') && els[i].offsetParent !== null) {
                els[i].click(); return true;
            }
        }
        // Try aria-label
        var ariaEl = document.querySelector('[aria-label*="Select all" i]');
        if (ariaEl) { ariaEl.click(); return true; }
        return false;
    """)

    if not clicked:
        # Fallback to CSS/XPATH selectors with short timeout
        el = _find_first(driver, _SELECT_ALL_SELECTORS, timeout=5)
        if el is None:
            log.warning("Select-all element not found.")
            return False
        driver.execute_script("arguments[0].click();", el)

    time.sleep(1)

    # Secondary "Select all N documents" banner (appears after checking the header checkbox)
    secondary = driver.execute_script("""
        var btns = document.querySelectorAll('button, a');
        for (var i = 0; i < btns.length; i++) {
            var t = btns[i].textContent.trim().toLowerCase();
            if (t.includes('select all') && t.includes('document') && btns[i].offsetParent !== null) {
                btns[i].click(); return true;
            }
        }
        return false;
    """)
    if secondary:
        log.info("Clicked secondary 'Select all documents' banner.")
    return True


# ---------------------------------------------------------------------------
# Export dialog
# ---------------------------------------------------------------------------

_EXPORT_BTN_SELECTORS = [
    (By.XPATH, "//button[normalize-space()='Export']"),
    (By.XPATH, "//button[contains(normalize-space(),'Export')]"),
    (By.CSS_SELECTOR, "[data-testid='export-button']"),
    (By.XPATH, "//a[contains(normalize-space(),'Export')]"),
]


def _wait_for_export_dialog(driver, timeout: int = 20):
    """Wait until the real export dialog (not the loading spinner) is visible."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            el = driver.execute_script("""
                // Skip the loading overlay (#loadingModal)
                var all = document.querySelectorAll('[role="dialog"]');
                for (var i = 0; i < all.length; i++) {
                    var d = all[i];
                    if (d.id === 'loadingModal') continue;
                    var s = window.getComputedStyle(d);
                    if (s.display !== 'none' && s.visibility !== 'hidden' && d.offsetParent !== null)
                        return d;
                }
                // Slide-in panel or export-specific container
                var candidates = [
                    '[data-testid*="export"]',
                    '[class*="exportModal"]',
                    '[class*="export-modal"]',
                    '[id*="exportModal"]',
                    '[id*="export-modal"]',
                    'form[action*="export"]',
                ];
                for (var j = 0; j < candidates.length; j++) {
                    var el = document.querySelector(candidates[j]);
                    if (el && el.offsetParent !== null) return el;
                }
                return null;
            """)
            if el:
                return el
        except Exception:
            pass
        time.sleep(0.5)
    return None


def _dump_dialog_html(driver) -> None:
    """Save the export dialog HTML to a file for visual inspection."""
    try:
        html = driver.execute_script("""
            // Prefer non-loading dialogs
            var all = document.querySelectorAll('[role="dialog"]');
            for (var i = 0; i < all.length; i++) {
                var d = all[i];
                if (d.id === 'loadingModal') continue;
                var s = window.getComputedStyle(d);
                if (s.display !== 'none' && d.offsetParent !== null) return d.outerHTML;
            }
            // Fallback: any export/modal container
            var fb = document.querySelector('[data-testid*="export"]') ||
                     document.querySelector('[class*="exportModal"]') ||
                     document.querySelector('[class*="export-modal"]') ||
                     document.querySelector('[id*="exportModal"]');
            if (fb) return fb.outerHTML;
            // Last resort: full body (capped)
            return document.body ? document.body.innerHTML.substring(0, 8000) : '';
        """)
        if html:
            path = Path("output") / "logs" / f"export_dialog_{datetime.now().strftime('%H%M%S')}.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html, encoding="utf-8")
            print(f"  [dialog HTML] {path}")
            log.info("Export dialog HTML saved: %s (%d chars)", path, len(html))
    except Exception as exc:
        log.debug("Could not dump dialog HTML: %s", exc)


def _dump_dropdown_html(driver) -> None:
    """Save the visible export dropdown HTML (menu/popover, not a dialog)."""
    try:
        html = driver.execute_script("""
            // Find the dropdown by looking for visible elements containing 'RIS' or 'CSV'
            var els = document.querySelectorAll('ul, ol, div[role="menu"], div[role="listbox"]');
            for (var i = 0; i < els.length; i++) {
                var el = els[i];
                if (el.offsetParent === null) continue;
                var txt = el.textContent;
                if (txt.includes('RIS') && txt.includes('CSV')) return el.outerHTML;
            }
            // Fallback: any visible div/section that contains 'RIS' text
            var divs = document.querySelectorAll('div, section, nav');
            for (var j = 0; j < divs.length; j++) {
                var d = divs[j];
                if (d.offsetParent === null) continue;
                if (d.textContent.includes('RIS') && d.textContent.includes('CSV') &&
                    d.children.length <= 20) {
                    return d.outerHTML.substring(0, 5000);
                }
            }
            return document.body ? document.body.innerHTML.substring(0, 8000) : '';
        """)
        if html:
            path = Path("output") / "logs" / f"export_dropdown_{datetime.now().strftime('%H%M%S')}.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html, encoding="utf-8")
            print(f"  [dropdown HTML] {path}")
            log.info("Export dropdown HTML saved: %s (%d chars)", path, len(html))
    except Exception as exc:
        log.debug("Could not dump dropdown HTML: %s", exc)


def _js_click_text(driver, text: str, exact: bool = False) -> bool:
    """JS-click the first visible element whose text contains (or equals) `text`."""
    try:
        clicked = driver.execute_script("""
            var needle = arguments[0].toLowerCase();
            var exact  = arguments[1];
            var root   = document.querySelector('[role="dialog"]') ||
                         document.querySelector('[class*="export"]') ||
                         document.querySelector('[class*="modal"]') ||
                         document.body;
            var tags = root.querySelectorAll('label, button, li, a, span, div[role="option"], div[role="radio"], div[role="button"]');
            for (var i = 0; i < tags.length; i++) {
                var el = tags[i];
                if (el.offsetParent === null) continue;
                var t = el.textContent.trim().toLowerCase();
                if (exact ? t === needle : t.includes(needle)) {
                    el.click();
                    return true;
                }
            }
            return false;
        """, text, exact)
        if clicked:
            log.info("JS-clicked element with text: %s", text)
        return bool(clicked)
    except Exception as exc:
        log.debug("_js_click_text(%s) failed: %s", text, exc)
        return False


def _js_click_export_confirm(driver) -> bool:
    """Click the confirm Export/Download button inside the dialog."""
    try:
        clicked = driver.execute_script("""
            var dialog = document.querySelector('[role="dialog"]') ||
                         document.querySelector('[class*="export"]') ||
                         document.querySelector('[class*="modal"]') ||
                         document.body;
            var btns = Array.from(dialog.querySelectorAll('button'));
            // Prefer exact 'Export' or 'Download' match
            for (var b of btns) {
                var t = b.textContent.trim().toLowerCase();
                if ((t === 'export' || t === 'download') && b.offsetParent !== null) {
                    b.click(); return 'exact:' + t;
                }
            }
            // Fallback: submit button
            var sub = dialog.querySelector('button[type="submit"]');
            if (sub && sub.offsetParent !== null) { sub.click(); return 'submit'; }
            // Fallback: last visible button
            var visible = btns.filter(function(b){ return b.offsetParent !== null; });
            if (visible.length) { visible[visible.length-1].click(); return 'last'; }
            return false;
        """)
        if clicked:
            log.info("Export confirm button clicked: %s", clicked)
        return bool(clicked)
    except Exception as exc:
        log.debug("_js_click_export_confirm failed: %s", exc)
        return False


def _wait_for_dropdown(driver, timeout: int = 8) -> bool:
    """Wait until the Export dropdown menu is visible (has visible menuitem buttons)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            visible = driver.execute_script("""
                // Scopus uses <button role="menuitem"> in its export dropdown
                var els = document.querySelectorAll('[role="menuitem"]');
                for (var i = 0; i < els.length; i++) {
                    var t = els[i].textContent.trim();
                    if ((t === 'RIS' || t === 'CSV' || t === 'BibTeX') && els[i].offsetParent !== null)
                        return true;
                }
                // Also check data-testid
                var ris = document.querySelector('[data-testid="export-to-ris"]');
                if (ris && ris.offsetParent !== null) return true;
                return false;
            """)
            if visible:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def _find_export_modal(driver):
    """Return the Scopus export confirmation modal element, or None."""
    try:
        return driver.execute_script("""
            // 1. Direct class selector (most reliable)
            var m = document.querySelector('[class*="Modal-module__HdKbm"]');
            if (m) return m;

            // 2. Modal embedded inside a table cell (Scopus SERP micro-UI pattern)
            var tdCandidates = document.querySelectorAll('td');
            for (var i = 0; i < tdCandidates.length; i++) {
                var mm = tdCandidates[i].querySelector('[class*="Modal-module"]');
                if (mm) return mm;
            }

            // 3. Open shadow DOM inside micro-ui / document-search-results-page
            var customEls = document.querySelectorAll(
                'micro-ui, document-search-results-page');
            for (var j = 0; j < customEls.length; j++) {
                var sr = customEls[j].shadowRoot;
                if (sr) {
                    var sm = sr.querySelector('[class*="Modal-module__HdKbm"]');
                    if (sm) return sm;
                }
            }

            // 4. role=dialog (excluding Bootstrap loading overlay)
            var dialogs = document.querySelectorAll('[role="dialog"]');
            for (var k = 0; k < dialogs.length; k++) {
                var d = dialogs[k];
                if (d.id === 'loadingModal') continue;
                if (d.textContent.trim().length > 50) return d;
            }
            return null;
        """)
    except Exception:
        return None


def _wait_for_export_modal(driver, timeout: int = 10) -> bool:
    """Wait for the RIS export confirmation modal that Scopus shows after format selection."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if _find_export_modal(driver) is not None:
                return True
        except Exception:
            pass
        time.sleep(0.4)
    return False


def _find_modal_export_button(driver):
    """
    Return the Export/Download button element inside the Scopus export modal.

    Follows the exact DOM path the user identified:
      Modal-module__HdKbm > ... > section > Modal-module__V53QT >
        div > div > span:nth-child(2) > div > div > button
    """
    try:
        return driver.execute_script("""
            // --- locate modal ---
            function findModal() {
                var m = document.querySelector('[class*="Modal-module__HdKbm"]');
                if (m) return m;
                var tds = document.querySelectorAll('td');
                for (var i = 0; i < tds.length; i++) {
                    var mm = tds[i].querySelector('[class*="Modal-module"]');
                    if (mm) return mm;
                }
                var ces = document.querySelectorAll(
                    'micro-ui, document-search-results-page');
                for (var j = 0; j < ces.length; j++) {
                    if (ces[j].shadowRoot) {
                        var sm = ces[j].shadowRoot.querySelector(
                            '[class*="Modal-module__HdKbm"]');
                        if (sm) return sm;
                    }
                }
                var dialogs = document.querySelectorAll('[role="dialog"]');
                for (var k = 0; k < dialogs.length; k++) {
                    if (dialogs[k].id !== 'loadingModal' &&
                        dialogs[k].textContent.trim().length > 50)
                        return dialogs[k];
                }
                return null;
            }

            // --- find the export button inside modal ---
            function findExportButton(modal) {
                // Exact path: section > [V53QT] > div > div > children[1 as span] > div > div > button
                var section = modal.querySelector('section');
                if (section) {
                    var body = section.querySelector('[class*="Modal-module__V53QT"]');
                    if (!body) body = section.querySelector('[class*="Modal-module__moSbS"]');
                    if (body) {
                        var d1 = body.firstElementChild;
                        var d2 = d1 ? d1.firstElementChild : null;
                        if (d2) {
                            // Collect direct child spans, return button inside 2nd span
                            var spansSeen = 0;
                            for (var c = 0; c < d2.children.length; c++) {
                                var child = d2.children[c];
                                if (child.tagName === 'SPAN') {
                                    spansSeen++;
                                    if (spansSeen === 2) {
                                        var btn = child.querySelector('button');
                                        if (btn) return btn;
                                    }
                                }
                            }
                            // Fallback: last span's button
                            for (var c2 = d2.children.length - 1; c2 >= 0; c2--) {
                                if (d2.children[c2].tagName === 'SPAN') {
                                    var btn2 = d2.children[c2].querySelector('button');
                                    if (btn2) return btn2;
                                }
                            }
                        }
                    }
                }

                // Fallback 1: button with text Export or Download
                var allBtns = Array.from(modal.querySelectorAll('button'));
                for (var b of allBtns) {
                    var t = b.textContent.trim().toLowerCase();
                    if (t === 'export' || t === 'download') return b;
                }

                // Fallback 2: any button with Button-module class (primary action)
                var primaries = allBtns.filter(function(b) {
                    return b.querySelector('[class*="Button-module__Imdmt"]') !== null;
                });
                if (primaries.length) return primaries[primaries.length - 1];

                // Last resort: last visible button in modal
                var visible = allBtns.filter(function(b) {
                    return b.offsetParent !== null;
                });
                if (visible.length) return visible[visible.length - 1];

                return null;
            }

            var modal = findModal();
            if (!modal) return null;
            return findExportButton(modal);
        """)
    except Exception as exc:
        log.debug("_find_modal_export_button failed: %s", exc)
        return None


def _select_abstract_in_modal(driver) -> bool:
    """Enable the Abstract checkbox in the Scopus export modal (searches Shadow DOM recursively)."""
    try:
        result = driver.execute_script("""
            // Recursively search root and all nested shadow roots for the Abstract checkbox.
            function deepSearch(root) {
                if (!root) return null;

                // 1. <label> whose direct text is exactly 'Abstract'
                var labels = root.querySelectorAll('label');
                for (var i = 0; i < labels.length; i++) {
                    var lbl = labels[i];
                    var text = lbl.textContent.trim();
                    if (text.toLowerCase() !== 'abstract') continue;
                    var inp = lbl.querySelector('input[type="checkbox"]');
                    if (!inp && lbl.htmlFor) {
                        inp = (root.getElementById ? root.getElementById(lbl.htmlFor) : null)
                              || document.getElementById(lbl.htmlFor);
                    }
                    if (inp) {
                        if (!inp.checked) { inp.click(); return 'checkbox'; }
                        return 'already-checked';
                    }
                    lbl.click();
                    return 'label-click';
                }

                // 2. <input type="checkbox"> whose containing label/span is exactly 'Abstract'
                var inputs = root.querySelectorAll('input[type="checkbox"]');
                for (var j = 0; j < inputs.length; j++) {
                    var el = inputs[j];
                    var container = el.closest('label') || el.parentElement;
                    if (container && container.textContent.trim().toLowerCase() === 'abstract') {
                        if (!el.checked) { el.click(); return 'inp-nearby'; }
                        return 'already-checked-2';
                    }
                }

                // 3. aria-label / data-testid containing 'abstract'
                var ariaEl = root.querySelector('[aria-label*="abstract" i]') ||
                             root.querySelector('[data-testid*="abstract" i]');
                if (ariaEl) { ariaEl.click(); return 'aria'; }

                // 4. Recurse into shadow roots
                var all = root.querySelectorAll('*');
                for (var k = 0; k < all.length; k++) {
                    if (all[k].shadowRoot) {
                        var res = deepSearch(all[k].shadowRoot);
                        if (res) return res;
                    }
                }
                return null;
            }

            return deepSearch(document);
        """)
        log.info("Abstract selection result: %s", result)
        return result is not None  # None == JS null == not found
    except Exception as exc:
        log.debug("_select_abstract_in_modal failed: %s", exc)
        return False


def _click_export_modal_button(driver) -> bool:
    """JS-only fallback: find + click the export modal button without ActionChains."""
    try:
        clicked = driver.execute_script("""
            // Inline version of findModal / findExportButton
            function findModal() {
                var m = document.querySelector('[class*="Modal-module__HdKbm"]');
                if (m) return m;
                var tds = document.querySelectorAll('td');
                for (var i = 0; i < tds.length; i++) {
                    var mm = tds[i].querySelector('[class*="Modal-module"]');
                    if (mm) return mm;
                }
                var dialogs = document.querySelectorAll('[role="dialog"]');
                for (var k = 0; k < dialogs.length; k++) {
                    if (dialogs[k].id !== 'loadingModal' &&
                        dialogs[k].textContent.trim().length > 50)
                        return dialogs[k];
                }
                return null;
            }
            var modal = findModal();
            if (!modal) return false;

            // Try exact path
            var section = modal.querySelector('section');
            if (section) {
                var body = section.querySelector('[class*="Modal-module__V53QT"]') ||
                           section.querySelector('[class*="Modal-module__moSbS"]');
                if (body) {
                    var d1 = body.firstElementChild;
                    var d2 = d1 ? d1.firstElementChild : null;
                    if (d2) {
                        var spansSeen = 0;
                        for (var c = 0; c < d2.children.length; c++) {
                            if (d2.children[c].tagName === 'SPAN') {
                                spansSeen++;
                                if (spansSeen === 2) {
                                    var btn = d2.children[c].querySelector('button');
                                    if (btn) { btn.click(); return 'span2'; }
                                }
                            }
                        }
                    }
                }
            }

            // Text fallback
            var btns = Array.from(modal.querySelectorAll('button'));
            for (var b of btns) {
                var t = b.textContent.trim().toLowerCase();
                if (t === 'export' || t === 'download') { b.click(); return 'text:'+t; }
            }

            // Last visible button
            var vis = btns.filter(function(b){ return b.offsetParent !== null; });
            if (vis.length) { vis[vis.length-1].click(); return 'last'; }
            return false;
        """)
        if clicked:
            log.info("Export modal button clicked (JS fallback): %s", clicked)
        return bool(clicked)
    except Exception as exc:
        log.debug("_click_export_modal_button failed: %s", exc)
        return False


def _perform_export(driver) -> None:
    """
    Scopus 2024 export flow:
      1. Click "Export ^" button  →  dropdown appears
      2. Click the "RIS" menu item (data-testid="export-to-ris")  →  download starts
    Uses ActionChains so React event handlers fire correctly.
    """
    log.info("Opening export dropdown...")
    print("  Opening export dropdown...")

    # Screenshot before export to verify document selection state
    _save_screenshot(driver, "pre_export")

    btn = _find_first(driver, _EXPORT_BTN_SELECTORS, timeout=15)
    if btn is None:
        raise RuntimeError(f"Export button not found. Page: {_current_url(driver)}")

    # ActionChains gives a real mouse-move + click that React event handlers pick up
    ActionChains(driver).move_to_element(btn).click().perform()

    # Wait for dropdown to be visible
    appeared = _wait_for_dropdown(driver, timeout=8)
    if appeared:
        log.info("Export dropdown visible.")
    else:
        log.warning("Dropdown not detected within 8s — proceeding anyway.")
    time.sleep(0.5)

    # Diagnostics
    _save_screenshot(driver, "export_dropdown")
    _dump_dropdown_html(driver)

    # Find the RIS button by its data-testid (most reliable)
    print("  Selecting RIS from dropdown...")
    ris_btn = _find_first(driver, [
        (By.CSS_SELECTOR, '[data-testid="export-to-ris"]'),
        (By.XPATH,        '//button[@data-testid="export-to-ris"]'),
    ], timeout=5)

    if ris_btn is None:
        # Fallback: find by exact text match using Selenium
        ris_btn = _find_first(driver, [
            (By.XPATH, '//button[@role="menuitem" and normalize-space()="RIS"]'),
            (By.XPATH, '//button[@role="menuitem"]//span[normalize-space()="RIS"]/..'),
        ], timeout=3)

    if ris_btn is None:
        raise RuntimeError(
            "RIS button (data-testid='export-to-ris') not found in dropdown. "
            "Check output/logs/export_dropdown_*.png"
        )

    log.info("Found RIS button: %s", ris_btn.get_attribute("data-testid"))
    ActionChains(driver).move_to_element(ris_btn).click().perform()
    log.info("RIS button clicked via ActionChains.")
    print("  RIS clicked — checking for confirmation modal...")

    # Scopus may show a confirmation modal before the download starts
    time.sleep(2)
    modal_appeared = _wait_for_export_modal(driver, timeout=10)
    if modal_appeared:
        log.info("Export confirmation modal appeared.")
        print("  Export modal detected — enabling Abstract option...")
        _save_screenshot(driver, "export_modal")
        _dump_dialog_html(driver)

        selected = _select_abstract_in_modal(driver)
        if selected:
            print("  Abstract option enabled.")
            time.sleep(0.5)
        else:
            log.warning("Abstract option not found in modal — exporting without abstract.")
            print("  Warning: Abstract option not found — proceeding without it.")

        # Use the JS-based finder that follows the exact DOM path the user identified:
        # Modal-module__HdKbm > section > Modal-module__V53QT > div > div > span[2] > ... > button
        export_btn_el = _find_modal_export_button(driver)
        if export_btn_el is not None:
            log.info("Export modal button found — clicking via ActionChains.")
            print("  Export button found — clicking...")
            ActionChains(driver).move_to_element(export_btn_el).click().perform()
            log.info("Export modal button clicked via ActionChains.")
        else:
            log.warning("_find_modal_export_button returned None — trying JS fallback.")
            print("  Primary finder failed — trying JS click fallback...")
            if not _click_export_modal_button(driver):
                log.warning("JS fallback also failed — download may not start.")
    else:
        log.info("No confirmation modal detected — direct download expected.")
    print("  Waiting for download...")


# ---------------------------------------------------------------------------
# Top-level: search + export
# ---------------------------------------------------------------------------

def search_and_export(
    driver,
    query: str,
    config: ScopusConfig,
    output_dir: Path | None = None,
    index_csv: Path | None = None,
) -> dict[str, Any]:
    """Run an advanced search and export all results as RIS. Returns metadata dict."""
    if output_dir is None:
        output_dir = config.search_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    ensure_logged_in(driver, config)

    # --- Navigate to advanced search ---
    found = _navigate_to_advanced_search(driver, config)
    if not found:
        return {"query": query, "error": "Could not find advanced search form", "ris_file": None}

    # --- Enter query ---
    _log_page_state(driver, "before-query")
    _enter_query(driver, query)

    # --- Submit ---
    _submit_search(driver)
    time.sleep(3)
    _log_page_state(driver, "after-submit")

    # --- Wait for results ---
    result_count = _wait_for_results(driver, timeout=60)
    search_url = _current_url(driver)

    if result_count == 0:
        log.warning("No results for: %s", query)
        return {
            "query": query, "result_count": 0,
            "search_url": search_url, "ris_file": None,
            "downloaded_at": datetime.now().isoformat(),
            "error": "No results",
        }

    # --- Select all ---
    _select_all_documents(driver)

    # --- Export ---
    export_start_mtime = time.time() - 1  # 1s buffer for clock skew
    _perform_export(driver)

    # --- Wait for download (only files newer than export start) ---
    log.info("Waiting for download (up to %ds)...", config.download_timeout_sec)
    print(f"  Waiting for download (up to {config.download_timeout_sec}s)...")
    ris_raw = wait_for_download(output_dir, config.download_timeout_sec, min_mtime=export_start_mtime)
    if ris_raw is None:
        raise RuntimeError(
            f"Download timed out after {config.download_timeout_sec}s. "
            "Check the export dialog in Chrome."
        )

    stem    = _query_to_filename(query)
    ris_dest = rename_download(ris_raw, output_dir / f"{stem}.ris")

    meta = {
        "query": query,
        "result_count": result_count,
        "search_url": search_url,
        "downloaded_at": datetime.now().isoformat(),
        "ris_file": str(ris_dest),
    }

    if index_csv is None:
        index_csv = output_dir.parent / "search_results_index.csv"
    _append_to_index(index_csv, meta)

    print(f"\n  Done! {result_count} documents -> {ris_dest}\n")
    return meta


def _append_to_index(index_csv: Path, meta: dict) -> None:
    fields = ["query", "result_count", "search_url", "downloaded_at", "ris_file"]
    write_header = not index_csv.exists()
    with open(index_csv, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if write_header:
            w.writeheader()
        w.writerow({k: meta.get(k, "") for k in fields})


# ---------------------------------------------------------------------------
# Batch from file
# ---------------------------------------------------------------------------

def search_from_file(
    driver,
    queries_file: str | Path,
    config: ScopusConfig,
    output_dir: Path | None = None,
) -> list[dict[str, Any]]:
    queries_file = Path(queries_file)
    queries = [
        ln.strip()
        for ln in queries_file.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    log.info("Loaded %d queries from %s", len(queries), queries_file)
    results = []
    for q in queries:
        try:
            results.append(search_and_export(driver, q, config, output_dir))
        except Exception as exc:
            log.error("Failed: %s — %s", q, exc)
            results.append({"query": q, "error": str(exc)})
    return results
