from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from playwright.async_api import async_playwright
import requests
import os
import asyncio

app = FastAPI()

CAPSOLVER_API_KEY = "CAP-AEA6E21EA89E1E97F2C5012A66086658273D3014539A9DB7BC5B66B2A7D43EA7"  # <- Replace with your CapSolver API key
SITE_KEY = "6LcqFAEaAAAAAKyGFh0HgS-0DKT47Z8F4Pj7-lrC"  # <- Replace with the sitekey from the target page

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
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            )
            page = await context.new_page()

            # Step 1: Solve CAPTCHA
            token = solve_captcha_v2(url, SITE_KEY)
            if not token:
                return {"error": "Captcha solving failed"}

            # Step 2: Go to page and inject CAPTCHA token
            await page.goto(url)
            await page.evaluate("""(token) => {
                const el = document.querySelector('textarea[name="g-recaptcha-response"]');
                if (el) {
                    el.style.display = 'block';
                    el.value = token;
                }
            }""", token)

            await page.wait_for_timeout(3000)  # Let Cloudflare redirect happen

            # Step 3: Scrape content
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

def solve_captcha_v2(website_url, sitekey):
    create_task_url = "https://api.capsolver.com/createTask"
    get_result_url = "https://api.capsolver.com/getTaskResult"

    payload = {
        "clientKey": CAPSOLVER_API_KEY,
        "task": {
            "type": "ReCaptchaV2TaskProxyless",
            "websiteURL": website_url,
            "websiteKey": sitekey
        }
    }

    response = requests.post(create_task_url, json=payload).json()
    task_id = response.get("taskId")
    if not task_id:
        return None

    for _ in range(30):
        asyncio.sleep(5)
        result = requests.post(get_result_url, json={
            "clientKey": CAPSOLVER_API_KEY,
            "taskId": task_id
        }).json()
        if result.get("status") == "ready":
            return result["solution"]["gRecaptchaResponse"]

    return None
