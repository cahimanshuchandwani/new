import os
import time
from playwright.sync_api import sync_playwright

def publish_to_tradingview():
    session_id = os.getenv("TV_SESSION_ID")
    if not session_id:
        print("[Error] TV_SESSION_ID secret is missing from GitHub Secrets.")
        return

    if not os.path.exists("generated_indicator.pine"):
        print("[Error] generated_indicator.pine file not found.")
        return

    with open("generated_indicator.pine", "r", encoding="utf-8") as f:
        pine_code = f.read()

    print("[Info] Launching Headless Chromium Browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})

        # Inject session cookie
        context.add_cookies([{
            'name': 'sessionid',
            'value': session_id,
            'domain': '.tradingview.com',
            'path': '/'
        }])

        page = context.new_page()
        print("[Info] Navigating to TradingView Chart...")
        page.goto("https://www.tradingview.com/chart/", wait_until="networkidle")
        time.sleep(6)

        # 1. Open Pine Editor Panel via UI Button or Hotkey
        print("[Info] Opening Pine Editor...")
        editor_btn = page.locator('button[data-name="editor"]')
        if editor_btn.is_visible():
            editor_btn.click()
        else:
            page.keyboard.press("Alt+e")
        time.sleep(3)

        # 2. Target Monaco Code Editor
        monaco_line = page.locator('.monaco-editor .view-line').first
        if monaco_line.is_visible():
            monaco_line.click()
            time.sleep(1)

            # Clear existing script and insert updated code
            page.keyboard.press("Control+a")
            page.keyboard.press("Backspace")
            time.sleep(1)
            
            page.keyboard.insert_text(pine_code)
            time.sleep(2)

            # 3. Save Script via Save Button or Hotkey
            save_btn = page.locator('button[data-name="save"], button:has-text("Save")').first
            if save_btn.is_visible():
                save_btn.click()
                print("[Info] Clicked Pine Editor Save button.")
            else:
                page.keyboard.press("Control+s")
                print("[Info] Pressed Ctrl+S shortcut.")

            time.sleep(5)
            print("[Success] Script updated and saved on TradingView!")
        else:
            print("[Error] Could not locate active Pine Editor window. Ensure Pine Editor is open on chart.")

        browser.close()

if __name__ == "__main__":
    publish_to_tradingview()
