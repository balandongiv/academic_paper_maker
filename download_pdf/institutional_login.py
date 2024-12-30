import json
import logging
import os
import shutil
import sys
import time
import tkinter as tk
from tkinter import messagebox

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm

# Configure logger
logger = logging.getLogger("pdf_ieee")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def create_driver(geckodriver_path, firefox_binary_path, download_directory):
    """
    Creates a Firefox WebDriver with given download directory settings.
    """
    # Create a Firefox profile and configure preferences
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.download.folderList", 2)
    profile.set_preference("browser.download.dir", download_directory)
    profile.set_preference("browser.download.useDownloadDir", True)
    profile.set_preference("pdfjs.disabled", True)
    profile.set_preference("plugin.scan.plid.all", False)
    profile.set_preference("plugin.scan.Acrobat", "99.0")
    profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
    profile.set_preference("browser.helperApps.alwaysAsk.force", False)
    profile.set_preference("browser.download.manager.showWhenStarting", False)
    profile.set_preference("browser.download.manager.focusWhenStarting", False)
    profile.set_preference("browser.download.manager.useWindow", False)
    profile.set_preference("browser.download.manager.showAlertOnComplete", False)
    profile.set_preference("browser.download.manager.closeWhenDone", True)

    # Configure options and attach the profile
    options = Options()
    options.binary_location = firefox_binary_path
    options.profile = profile

    # Initialize the Service object with the path to geckodriver
    service = Service(geckodriver_path)
    driver = webdriver.Firefox(service=service, options=options)
    driver.maximize_window()
    return driver
