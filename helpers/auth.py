import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("CBA_USERNAME")
PASSWORD = os.getenv("CBA_PASSWORD")
LOGIN_URL = "https://pvc003.zucchettihc.it:4445/cba/login.html"

def refresh_jwt_token():
    """Refreshes the JWT token when it expires."""
    print("🔄 Token expired! Refreshing...")
    new_token = get_jwt_token_selenium()  # Re-authenticate
    
    if not new_token:
        print("❌ Failed to refresh token. Exiting.")
        exit(1)
    
    print(f"✅ New JWT Token Retrieved: {new_token[:50]}... (truncated)")
    return new_token


def get_jwt_token_selenium():
    """Logs in via Selenium and extracts JWT token from the login response."""
    print("🚀 Launching browser...")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Disable this for debugging
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # ✅ Correct way to enable performance logging
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)  # ✅ No `desired_capabilities`

    try:
        driver.get(LOGIN_URL)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "username")))

        print("🔑 Entering credentials...")
        driver.find_element(By.NAME, "username").send_keys(USERNAME)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD)

        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Login']/ancestor::span[contains(@id, '-btnEl')]"))
        )
        login_button.click()
        print("✅ Login button clicked")

        time.sleep(3)  # Wait for login response

        # ✅ Check if performance logs are available before accessing them
        logs = driver.get_log("performance") if "performance" in driver.log_types else []
        jwt_token = None

        for log_entry in logs:
            try:
                log_data = json.loads(log_entry["message"])["message"]
                if log_data["method"] == "Network.responseReceived":
                    request_id = log_data["params"]["requestId"]
                    response = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                    response_body = json.loads(response["body"])

                    if "data" in response_body and "token" in response_body["data"]:
                        jwt_token = response_body["data"]["token"]
                        break
            except Exception:
                continue

        if not jwt_token:
            print("🚨 Login failed! No token retrieved.")
            return None

        print(f"✅ JWT Token Retrieved: {jwt_token[:50]}... (truncated)")
        return jwt_token

    finally:
        driver.quit()
