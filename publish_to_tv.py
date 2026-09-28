import os
import time
from playwright.sync_api import sync_playwright

def publish_to_tradingview():
    session_id = os.getenv("TV_SESSION_ID")
    if not session_id:
        print("[Error] TV_SESSION_ID secret is missing from GitHub Secrets.")
        return

    # 1. Read the generated Pine Script code
    if not os.path.exists("generated_indicator.pine"):
        print("[Error] generated_indicator.pine file not found.")
        return

    with open("generated_indicator.pine", "r", encoding="utf-8") as f:
        pine_code = f.read()

    print("[Info] Launching Headless Chromium Browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})

        # 2. Inject Session Cookie to log in automatically
        context.add_cookies([{
            'name': 'sessionid',
            'value': session_id,
            'domain': '.tradingview.com',
            'path': '/'
        }])

        page = context.new_page()
        
        print("[Info] Navigating to TradingView Chart...")
        page.goto("https://www.tradingview.com/chart/", wait_until="domcontentloaded")
        time.sleep(5)

        # 3. Open Pine Editor Panel (Alt + E)
        print("[Info] Opening Pine Editor...")
        page.keyboard.press("Alt+e")
        time.sleep(3)

        # Focus Pine Editor canvas area
        editor = page.locator('.monaco-editor').first
        if editor.is_visible():
            editor.click()
            time.sleep(1)

            # Select All and Replace with new code
            page.keyboard.press("Control+a")
            page.keyboard.press("Backspace")
            
            # Insert updated code into editor
            page.keyboard.insert_text(pine_code)
            time.sleep(2)

            # Save the indicator (Ctrl + S)
            print("[Info] Saving updated Pine Script on TradingView...")
            page.keyboard.press("Control+s")
            time.sleep(4)
            print("[Success] Script successfully updated and saved on TradingView!")
        else:
            print("[Error] Could not locate Pine Editor window on TradingView chart.")

        browser.close()

if __name__ == "__main__":
    publish_to_tradingview()
