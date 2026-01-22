import time
import os
import urllib.parse
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from .browser_core import get_driver

def post_to_x(text, image_path=None, reply_text=None, headless=False):
    """
    Posts content to X (Twitter).
    If reply_text is provided, it posts as a reply to the main post (Thread).
    """
    driver = get_driver(headless=headless)
    wait = WebDriverWait(driver, 20)
    
    try:
        print("🐦 Navigating to X...")
        driver.get("https://twitter.com/compose/tweet")
        
        # --- 1. Main Post ---
        # Check login status
        try:
            input_box = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]')
            ))
            print("✅ Logged in successfully.")
        except TimeoutException:
            print("❌ Not logged in. Please log in manually.")
            driver.get("https://twitter.com/login")
            input("🛑 Please Log In to X in the browser, then press Enter to retry...")
            driver.get("https://twitter.com/compose/tweet")
            input_box = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]')
            ))

        print("✍️ Inputting text...")
        input_box.send_keys(text)
        time.sleep(1)

        if image_path and os.path.exists(image_path):
            print(f"🖼️ Uploading media: {image_path}")
            file_input = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
            file_input.send_keys(image_path)
            time.sleep(3)

        print("🚀 Clicking Post button...")
        post_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="tweetButton"]')
        
        if post_button.get_attribute("aria-disabled") == "true":
            raise Exception("❌ Post button is disabled. Text might be too long.")
            
        post_button.click()
        
        # Confirm post sent and handle Reply if needed
        print("⏳ Waiting for post confirmation...")
        
        # Look for the "Your post was sent" toast and the "View" link
        # This is critical for threading.
        try:
            view_link = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[@data-testid='toast']//a[contains(@href, '/status/')]")
            ))
            print("✅ Main Post sent! Detected 'View' link.")
            
            if reply_text:
                print("🔗 Clicking 'View' to start threading...")
                view_link.click()
                
                # --- 2. Reply Post ---
                print("↩️ Preparing Reply...")
                # Wait for reply input area in the detailed view
                reply_input = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]')
                ))
                reply_input.click() # Focus
                time.sleep(1)
                
                print("✍️ Inputting reply...")
                reply_input.send_keys(reply_text)
                time.sleep(1)
                
                print("🚀 Clicking Reply button...")
                reply_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="tweetButtonInline"]')
                reply_button.click()
                
                time.sleep(3)
                print("✅ Thread Reply posted!")
            else:
                print("ℹ️ No reply text provided. Done.")
                time.sleep(2)

        except TimeoutException:
            print("⚠️ Post might have been sent, but couldn't detect 'View' link for threading.")
        
        
    except Exception as e:
        print(f"❌ Error posting to X: {e}")
        raise e
    finally:
        pass

def hijack_top_trend(keyword, reply_text, image_path=None, headless=False):
    """
    Dominator Strategy: Search for a top trend and hijack the traffic by replying.
    Suitable for 0-follower accounts to get visibility.
    """
    driver = get_driver(headless=headless)
    wait = WebDriverWait(driver, 20)
    
    try:
        print(f"🕵️ Searching for high-traffic tweets about '{keyword}'...")
        encoded_query = urllib.parse.quote(f"{keyword} min_faves:500") # Filter for popular tweets
        search_url = f"https://twitter.com/search?q={encoded_query}&src=typed_query&f=top"
        driver.get(search_url)
        time.sleep(5) # Wait for load
        
        # Find first tweet
        try:
            first_tweet = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweet"]')))
            print("🎯 Target acquired. Engaging...")
            first_tweet.click()
            time.sleep(3)
        except TimeoutException:
            print("⚠️ No suitable tweets found for newsjacking.")
            return

        # Click Reply
        try:
            reply_area = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]')))
            reply_area.click()
            time.sleep(1)
            
            print("✍️ Deploying hijack reply...")
            reply_area.send_keys(reply_text)
            time.sleep(2)
            
            # Upload Image if provided (Project Paparazzi)
            if image_path and os.path.exists(image_path):
                print(f"🖼️ Attaching Infographic: {image_path}")
                file_input = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
                file_input.send_keys(image_path)
                time.sleep(3)
            
            reply_btn = driver.find_element(By.CSS_SELECTOR, '[data-testid="tweetButtonInline"]')
            reply_btn.click()
            print("✅ Newsjacking successful. Traffic diverted.")
            time.sleep(3)
            
            # --- LOGGING ---
            try:
                # Capture the URL of the tweet we just replied to
                target_url = driver.current_url
                
                log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "newsjacking_log.csv")
                file_exists = os.path.isfile(log_file)
                
                import csv
                with open(log_file, mode='a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(["Timestamp", "Keyword", "Target URL", "Reply Text", "Image Path"])
                    
                    writer.writerow([
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        keyword,
                        target_url,
                        reply_text,
                        image_path or "None"
                    ])
                print(f"📝 Action logged to: {os.path.basename(log_file)}")
                
            except Exception as log_err:
                print(f"⚠️ Failed to write log: {log_err}")

            
        except Exception as e:
            print(f"❌ Failed to reply: {e}")

    except Exception as e:
        print(f"❌ Hijack failed: {e}")
    finally:
        pass

if __name__ == "__main__":
    # Test run
    print("🧪 Testing X Poster...")
    test_text = f"🤖 Sentinel Test Post {datetime.now().strftime('%H:%M:%S')}\n#AntigravityTest"
    post_to_x(test_text)
