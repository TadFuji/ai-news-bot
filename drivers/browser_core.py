import os
# Disable SSL verification for webdriver_manager (Fix for Python 3.14 / Network issues)
os.environ['WDM_SSL_VERIFY'] = '0'

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

# Persistent User Data Directory
# IMPORTANT: Store this in LOCAL APPDATA to avoid Google Drive / Cloud Sync locking issues!
# Do NOT store in os.getcwd() if it's in a synced folder.
import tempfile
BASE_TEMP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "AntigravityBrowserProfiles")
USER_DATA_DIR = os.path.join(BASE_TEMP_DIR, "MainProfile")

def get_driver(headless=False, use_profile=True, force_attach=False):
    """
    Initializes and returns a Chrome WebDriver.
    Args:
        headless (bool): Run in headless mode.
        use_profile (bool): Use the persistent user profile.
        force_attach (bool): Force connection to existing Chrome on port 9222.
    """
    options = Options()
    
    # User Agent - REMOVED HARDCODED VALUE
    
    # Ensure base dir exists
    if not os.path.exists(BASE_TEMP_DIR):
        try:
            os.makedirs(BASE_TEMP_DIR)
        except:
            pass

    # Logic for Force Attach (User High-Jack Mode)
    if force_attach:
        print("🔌 Force Attach Mode: Connecting to 127.0.0.1:9222")
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        
        # When attaching, we usually skip other profile args as they are set by the target browser
        # But we still need the driver binary
        
    else:
        # Standard Launch Logic
        # (Only do socket check if NOT forcing, or maybe just skip detection if not forcing?)
        # For now, let's keep the user profile logic for standard launch
        
        # User Data Dir
        if use_profile:
             if not os.path.exists(USER_DATA_DIR):
                 os.makedirs(USER_DATA_DIR)
             options.add_argument(f"user-data-dir={USER_DATA_DIR}")
        else:
             pdf_profile = os.path.join(BASE_TEMP_DIR, "PDFProfile")
             if not os.path.exists(pdf_profile):
                 os.makedirs(pdf_profile)
             options.add_argument(f"user-data-dir={pdf_profile}")

        # Stability Flags (Apply to standard launch)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        if headless:
            options.add_argument("--headless")

    # Common Settings (Anti-bot)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # Additional stealth script
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    
    return driver

if __name__ == "__main__":
    print("🚀 Launching Browser for Setup...")
    print(f"📂 Profile Path: {USER_DATA_DIR}")
    print("Please log in to X (Twitter) and Note manually in this window.")
    print("When finished, close the browser or press Enter here.")
    
    driver = get_driver(headless=False)
    driver.get("https://twitter.com/login")
    
    # Open Note in a new tab
    driver.execute_script("window.open('https://note.com/login', '_blank');")
    
    input("Press Enter to close browser...")
    driver.quit()
