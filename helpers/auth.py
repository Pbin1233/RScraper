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


def get_jwt_token_selenium(keep_browser_open=False):
    print("🚀 Launching browser...")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(LOGIN_URL)

        # Check if the site failed to load
        if "This site can’t be reached" in driver.page_source or "ERR_CONNECTION_REFUSED" in driver.page_source:
            print("❌ Website appears offline or unreachable.")
            return (None, driver) if keep_browser_open else None

        try:
            print("🔑 Waiting for login fields...")
            username_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Digita il tuo nome utente']"))
            )
            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Digita la tua password']"))
            )

            print("⌨️ Entering credentials...")
            username_input.clear()
            username_input.send_keys(USERNAME)
            password_input.clear()
            password_input.send_keys(PASSWORD)

            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[.//span[text()='Entra']]"))
            )
            login_button.click()
            print("✅ Login button clicked")

        except Exception as e:
            print(f"❌ Failed during login interaction: {e}")
            return (None, driver) if keep_browser_open else None

        # Wait for the network request to complete
        time.sleep(3)

        logs = driver.get_log("performance")
        jwt_token = None

        for log in logs:
            try:
                message = json.loads(log["message"])["message"]
                if (
                    message["method"] == "Network.responseReceived"
                    and "auth/login" in message["params"]["response"]["url"]
                ):
                    request_id = message["params"]["requestId"]
                    response = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                    body = json.loads(response["body"])
                    if "data" in body and "token" in body["data"]:
                        jwt_token = body["data"]["token"]
                        break
            except Exception:
                continue

        if not jwt_token:
            print("🚨 Login succeeded, but no token was retrieved.")
            return (None, driver) if keep_browser_open else None

        print(f"✅ JWT Token Retrieved: {jwt_token[:50]}... (truncated)")
        return (jwt_token, driver) if keep_browser_open else jwt_token

    except Exception as e:
        print(f"❌ Unexpected error during login: {e}")
        return (None, driver) if keep_browser_open else None

    finally:
        if not keep_browser_open and driver:
            driver.quit()
