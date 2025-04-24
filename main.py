from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from playwright.async_api import async_playwright
import os

app = FastAPI()

@app.post("/scrape")
async def scrape(request: Request):
    data = await request.json()
    url = data.get("url")

    page = None
    browser = None

    if not url:
        return {"error": "Missing 'url' in request body"}

    try:
        async with async_playwright() as p:
            # Use full browser with stealth-like behavior
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                java_script_enabled=True,
                locale="en-US"
            )
            page = await context.new_page()

            # Go to the page
            await page.goto(url, timeout=60000)

            # Simulate human behavior
            await page.mouse.move(200, 300)
            await page.wait_for_timeout(1000)
            await page.keyboard.press("PageDown")
            await page.wait_for_timeout(1500)
            await page.mouse.move(400, 500)
            await page.wait_for_timeout(1000)
            await page.keyboard.press("PageDown")
            await page.wait_for_timeout(2000)

            # Wait for actual content
            await page.wait_for_selector("h1", timeout=30000, state="attached")
            await page.wait_for_selector("a.breadcrumb", timeout=30000, state="attached")
            await page.wait_for_selector(".description", timeout=30000, state="attached")

            # Scrape
            title = await page.text_content("h1") or "N/A"
            category = await page.locator("a.breadcrumb").first.text_content()
            category = category.strip() if category else "N/A"
            content = await page.text_content(".description") or "N/A"

            return {
                "title": title.strip(),
                "category": category,
                "content": content.strip()
            }

    except Exception as e:
        if page:
            try:
                await page.screenshot(path="debug.png", full_page=True)
            except:
                pass
        return {"error": str(e), "debug": "/debug"}

    finally:
        if browser:
            await browser.close()

@app.get("/debug")
async def get_debug_screenshot():
    path = "debug.png"
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png")
    return {"error": "debug.png not found"}