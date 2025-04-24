from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from playwright.async_api import async_playwright
import os

app = FastAPI()

@app.post("/scrape")
async def scrape(request: Request):
    data = await request.json()
    url = data.get("url")

    # Init objects for wider scope
    page = None
    browser = None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            )
            page = await context.new_page()

            # Try to visit the URL
            try:
                await page.goto(url, timeout=60000)
                await page.wait_for_timeout(3000)

                # Try to wait for the elements
                await page.wait_for_selector("h1", timeout=30000, state="attached")
                await page.wait_for_selector("a.breadcrumb", timeout=30000, state="attached")
                await page.wait_for_selector(".description", timeout=30000, state="attached")

                # Try to extract
                title = await page.text_content("h1") or "N/A"
                category = await page.locator("a.breadcrumb").first.text_content()
                category = category.strip() if category else "N/A"
                content = await page.text_content(".description") or "N/A"

                return {
                    "title": title.strip(),
                    "category": category,
                    "content": content.strip()
                }

            except Exception as scrape_error:
                # Screenshot on scraping failure
                if page:
                    await page.screenshot(path="debug.png", full_page=True)
                return {
                    "error": f"Scraping failed: {str(scrape_error)}",
                    "debug": "/debug"
                }

    except Exception as setup_error:
        return {
            "error": f"Setup failed: {str(setup_error)}"
        }

    finally:
        # Close browser even if there's an error
        if browser:
            await browser.close()

@app.get("/debug")
async def get_debug_screenshot():
    path = "debug.png"
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png")
    return {"error": "debug.png not found"}
