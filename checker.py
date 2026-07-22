from playwright.async_api import async_playwright
import re
import json
from pathlib import Path
import asyncio
from datetime import datetime
import smtplib
from email.message import EmailMessage
import os
from constants import URL, STATE_FILE, LOGS_FILE

def update_logs(previous_earliest_date, new_earliest_date):
    today_date = datetime.today().date().isoformat()


    with open(LOGS_FILE, "r") as f:
        logs = json.load(f)

    if logs[-1]["today_date"] != today_date:
        logs.append({
            "previous_earliest_date": previous_earliest_date.isoformat(),
            "new_earliest_date": new_earliest_date.isoformat(),
            "today_date": datetime.today().date().isoformat()
        })

    if  (logs[-1]["today_date"] == today_date) and (logs[-1]["previous_earliest_date"]!=logs[-1]["new_earliest_date"]):
        logs.append({
            "previous_earliest_date": previous_earliest_date.isoformat(),
            "new_earliest_date": new_earliest_date.isoformat(),
            "today_date": datetime.today().date().isoformat()
        })

    with open(LOGS_FILE, "w") as f:
        json.dump(logs, f, indent=4)

async def get_browser_date(browser):
    page = await browser.new_page()
    await page.goto(URL)
    button = page.get_by_role("button", name=re.compile(r"Jump to"))

    text = await button.text_content()
    date = text.split(" ")[2:]
    date = " ".join(date)

    DATE_MAPPING_FILE = Path("date_mapping.json")
    with open(DATE_MAPPING_FILE, "r") as f:
        date_mapping = json.load(f)

    date = date_mapping[date]
    return date


def get_date_boundaries(date):
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            state = json.load(f)
    else:
        state = {}

    if LOGS_FILE.exists():
        with open(LOGS_FILE) as f:
            logs = json.load(f)
    else:
        logs = {}

    # string
    left_date_boundary_value = state.get("left_date_boundary")
    right_date_boundary_value = state.get("right_date_boundary")
    new_date_found_value = date
    today_date = datetime.today().strftime("%Y-%m-%d")

# Replace state.json and logs.json files
    state["right_date_boundary"] = new_date_found_value

    # Date Obj
    left_date_boundary = datetime.strptime(left_date_boundary_value, "%Y-%m-%d").date()
    right_date_boundary = datetime.strptime(right_date_boundary_value, "%Y-%m-%d").date()
    new_date_found = datetime.strptime(new_date_found_value, "%Y-%m-%d").date()

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    return left_date_boundary, right_date_boundary, new_date_found

def email_alert(right_date_boundary, new_date_found):
    print("Earlier appointment found!")

    EMAIL = os.environ["EMAIL"]
    EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

    msg = EmailMessage()
    msg["Subject"] = "New Safe Refuge Availability"
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    msg.set_content(f"""
                A new earlier appointment was found.

                Previous: {right_date_boundary}
                New: {new_date_found}

                Booking Portal:
                {URL}

                Github: 
                https://github.com/soniaeya/check-safe-refuge-availability
                """)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL, EMAIL_PASSWORD)
        smtp.send_message(msg)
    print("Email sent!")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        date = await get_browser_date(browser)

        left_date_boundary, right_date_boundary, new_date_found = get_date_boundaries(date)

        if left_date_boundary < new_date_found < right_date_boundary:
            email_alert(right_date_boundary, new_date_found)

        update_logs(previous_earliest_date=right_date_boundary, new_earliest_date=new_date_found)

        await browser.close()

asyncio.run(main())
