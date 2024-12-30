// Listen for messages from background.js
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "startAutomation") {
    const titlesData = request.payload;
    // Start iterating the provided inputTitles array
    automateSearch(titlesData);
  }
});

/**
 * Automate the search for each item in the array sequentially.
 */
async function automateSearch(titlesData) {
  for (const dataItem of titlesData) {
    const { code, titles, note } = dataItem;

    // Each dataItem can have multiple possible titles to search for.
    for (const paperTitle of titles) {
      console.log(`[INFO] Searching for: "${paperTitle}" under code=${code}, note=${note}`);

      // 1. Fill the search input (ID=qs) if available
      const searchInput = document.getElementById("qs");
      if (!searchInput) {
        console.warn("[WARN] Could not find search box with ID='qs'.");
        continue; // Go to next item
      }

      // Clear and type
      searchInput.value = "";
      searchInput.value = paperTitle;

      // 2. Click the "Search" button explicitly by unique aria-label
      const searchButton = document.querySelector("button[aria-label='Submit quick search']");
      if (searchButton) {
        searchButton.click();
        console.log("[INFO] 'Search' button clicked.");
      } else {
        console.warn("[WARN] Could not find the 'Search' button.");
        continue;
      }

      // Wait for results to appear in the DOM
      await waitForResults();

      // 3. Click "View PDF" on the first search result, if available
      const firstResult = document.querySelector("li.ResultItem");
      if (!firstResult) {
        console.warn("[WARN] No search results found for this query.");
        continue;
      }

      // Try to find the "View PDF" button within the first result
      const viewPdfBtn = firstResult.querySelector("a.anchor.download-link");
      if (viewPdfBtn) {
        viewPdfBtn.click();
        console.log("[INFO] 'View PDF' button clicked.");

        // Wait for the PDF link on the next page
        await waitForPDFLink();
      } else {
        console.warn("[WARN] 'View PDF' button not found in the first result.");
      }
    }
  }
  console.log("[INFO] Finished all searches.");
}

/**
 * Utility function: Wait for search results to appear.
 */
function waitForResults() {
  return new Promise((resolve) => {
    let checks = 0;
    const interval = setInterval(() => {
      checks++;
      const resultItem = document.querySelector("li.ResultItem");
      // Either we found at least one result, or we exceeded 30 seconds
      if (resultItem || checks > 30) {
        clearInterval(interval);
        resolve();
      }
    }, 1000);
  });
}

/**
 * Utility function: Wait for the PDF link to appear after the user clicks "View PDF".
 */
function waitForPDFLink() {
  return new Promise((resolve) => {
    let checks = 0;
    const interval = setInterval(() => {
      checks++;
      const pdfLink = document.querySelector(
        "a.link-button.accessbar-utility-link[aria-label*='View PDF']"
      );
      if (pdfLink) {
        pdfLink.click();
        console.log("[INFO] PDF link clicked.");
        clearInterval(interval);
        resolve();
      } else if (checks > 30) {
        console.warn("[WARN] PDF link not found after waiting.");
        clearInterval(interval);
        resolve();
      }
    }, 1000);
  });
}
