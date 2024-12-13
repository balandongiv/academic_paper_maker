# from selenium import webdriver
#
#
# driver = webdriver.Firefox()
# driver.get('https://www.geeksforgeeks.org/how-to-install-selenium-in-python/')


from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options

# Path to the GeckoDriver executable
gecko_driver_path = r"C:\Users\rpb\Downloads\geckodriver"

# Path to your existing Firefox profile
firefox_profile_path = "/path/to/your/firefox/profile"

# Set up Firefox options
options = Options()
options.set_preference("browser.privatebrowsing.autostart", False)  # Ensure not in private mode

# Load the existing Firefox profile
options.set_preference("profile", firefox_profile_path)

# Start Firefox with the existing profile
service = Service(executable_path=gecko_driver_path)
driver = webdriver.Firefox(service=service, options=options)

# Example: Navigate to a site to confirm cookies are loaded
driver.get("https://www.example.com")

# Do your Selenium tasks...

# Quit the driver
driver.quit()
