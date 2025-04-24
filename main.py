from fastapi import FastAPI, Request
from playwright.async_api import async_playwright
import asyncio

app = FastAPI()

@app.post("/scrape")
async def scrape(request: Request):
    data = await request.json()
    url = data.get("url")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            )
            page = await context.new_page()

            await page.goto(url, timeout=60000)

            # Simulate human-like interaction (stealthy behavior)
            await page.mouse.move(200, 300)
            await page.wait_for_timeout(1500)
            await page.keyboard.press("PageDown")
            await page.wait_for_timeout(1000)

            # Optional: Detect if blocked
            if "Attention Required!" in await page.title():
                return {"error": "Blocked by Cloudflare or CAPTCHA"}

            title = await page.text_content("h1") or "N/A"
            category = await page.text_content(".tag") or "N/A"
            content = await page.text_content(".description") or "N/A"

            await browser.close()

            return {
                "title": title.strip(),
                "category": category.strip(),
                "content": content.strip()
            }

    except Exception as e:
        return {"error": str(e)}
