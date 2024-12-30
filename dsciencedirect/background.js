// Define the input data:
const inputTitles = [
  {
    code: "dummy_C_2023",
    titles: [
      "Bilateral Pallidotomy for Cervical Dystonia After Failed Selective Peripheral Denervation"
    ],
    note: "dummy Detection"
  },
  {
    code: "dummy_C_2018",
    titles: [
      "10.1016/j.cegh.2020.04.005"
    ],
    note: "dummy Interfaces"
  }
];

/**
 * When the user clicks the extension's button, open ScienceDirect
 * in a new tab and send the data to the content script.
 */
browser.browserAction.onClicked.addListener(() => {
  // Open a new tab pointing to the site
  browser.tabs.create({ url: "https://www.sciencedirect.com" })
    .then((tab) => {
      // Once the tab is created, send a message with our input data
      // to the content script. We'll do this with a small timeout
      // to ensure the page (and therefore content script) is loaded.
      setTimeout(() => {
        browser.tabs.sendMessage(tab.id, {
          action: "startAutomation",
          payload: inputTitles
        });
      }, 4000);
    });
});
