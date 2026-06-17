import sys
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_login():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Add user agent to make it look like a normal browser
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    print("Launching Chrome...")
    driver = webdriver.Chrome(options=chrome_options)
    try:
        print("Navigating to login page...")
        driver.get("https://www.overleaf.com/login")
        time.sleep(3)
        
        print(f"Page URL: {driver.current_url}")
        print(f"Page Title: {driver.title}")
        
        # Check if Cloudflare turnstile is blocking
        if "cloudflare" in driver.page_source.lower() or "challenge" in driver.current_url:
            print("Warning: Cloudflare challenge detected.")
            
        print("Locating form elements...")
        # Email input field
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
        )
        email_input.send_keys("uignitehq@gmail.com")
        print("Typed email.")
        
        # Password input field
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
        password_input.send_keys("f2DE#Xb@c$wYV!a")
        print("Typed password.")
        
        # Click login button
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        print("Clicked login submit button.")
        
        # Wait for redirect
        time.sleep(5)
        print(f"Post-Login Page URL: {driver.current_url}")
        print(f"Post-Login Page Title: {driver.title}")
        
        if "project" in driver.current_url or "dashboard" in driver.current_url or "home" in driver.current_url:
            print("Login successful!")
        else:
            print("Login failed or redirect did not occur. Current page source contains:")
            print(driver.page_source[:500])
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_login()
