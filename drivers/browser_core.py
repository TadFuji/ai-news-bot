import os
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

def get_driver(headless=False, use_profile=True):
    """
    Initializes and returns a Chrome WebDriver.
    Args:
        headless (bool): Run in headless mode.
        use_profile (bool): Use the persistent user profile (needed for X/Note login). 
                            Set to False for lightweight tasks like PDF generation.
    """
    options = Options()
    
    # User Agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Ensure base dir exists
    if not os.path.exists(BASE_TEMP_DIR):
        try:
            os.makedirs(BASE_TEMP_DIR)
        except:
            pass

    # Persistent Profile (Only if requested)
    if use_profile:
        if not os.path.exists(USER_DATA_DIR):
            os.makedirs(USER_DATA_DIR)
        options.add_argument(f"user-data-dir={USER_DATA_DIR}")
    else:
        # Create a temporary profile for isolation
        # Use a consistent temp path for PDF to avoid creating millions of folders, 
        # but separate from MainProfile
        pdf_profile = os.path.join(BASE_TEMP_DIR, "PDFProfile")
        if not os.path.exists(pdf_profile):
            os.makedirs(pdf_profile)
        options.add_argument(f"user-data-dir={pdf_profile}")
    
    # Anti-bot detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # Stability Flags
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    if headless:
        # Fallback to classic headless to solve "Not Reachable" / Hang issues
        options.add_argument("--headless") 
    
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
