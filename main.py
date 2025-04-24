from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from playwright.async_api import async_playwright
import random
import os
import asyncio

app = FastAPI()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118 Safari/537.36",
]

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
            user_agent = random.choice(USER_AGENTS)
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=user_agent,
                java_script_enabled=True,
                locale="en-US"
            )
            page = await context.new_page()

            await page.goto(url, timeout=60000)
            await page.wait_for_timeout(2000)

            # Save screenshot immediately after page load
            await page.screenshot(path="debug.png", full_page=True)

            # Simulate human behavior
            for y in range(0, 1000, 100):
                await page.mouse.move(random.randint(200, 600), y)
                await page.mouse.wheel(0, 100)
                await page.wait_for_timeout(random.randint(300, 700))

            await page.mouse.move(500, 300)
            await page.wait_for_timeout(1000)
            await page.mouse.move(700, 500)
            await page.wait_for_timeout(1500)

            # Wait for actual content
            await page.wait_for_selector("h1", timeout=30000, state="attached")
            await page.wait_for_selector("a.breadcrumb", timeout=30000, state="attached")
            await page.wait_for_selector(".description", timeout=30000, state="attached")

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
        # Try to capture screenshot even if scraping failed early
        try:
            if page:
                await page.screenshot(path="debug.png", full_page=True)
        except Exception as err:
            print("Screenshot failed:", err)

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
