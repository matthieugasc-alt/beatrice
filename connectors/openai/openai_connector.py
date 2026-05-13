from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path("/opt/factures-v1/connectors/openai")
PROFILE_DIR = BASE_DIR / "profile"
DOWNLOADS_DIR = BASE_DIR / "downloads"
STATE_DIR = BASE_DIR / "state"

BILLING_URL = "https://chatgpt.com/admin/billing"

def main():
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=True,
            accept_downloads=True,
        )

        page = context.new_page()
        page.goto(BILLING_URL, wait_until="domcontentloaded", timeout=60000)

        print("URL courante:", page.url)
        print("Titre:", page.title())

        context.close()

if __name__ == "__main__":
    main()
