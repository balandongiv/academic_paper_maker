from selenium import webdriver
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService


def create_driver_with_profile(geckodriver_path, firefox_binary_path, firefox_profile_path):
    """
    Creates a Firefox WebDriver using an existing profile.
    """
    options = FirefoxOptions()
    options.binary_location = firefox_binary_path
    profile = FirefoxProfile(firefox_profile_path)
    options.profile = profile  # Set the profile in options
    service = FirefoxService(executable_path=geckodriver_path)
    driver = webdriver.Firefox(service=service, options=options)
    return driver

