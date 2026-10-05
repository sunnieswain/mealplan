import os
import json
import calendar
from datetime import date
from zoneinfo import ZoneInfo

import requests


# ============================================================
# SETTINGS
# ============================================================

DATABASE_ID = "3ec49938057180639b57d62b8fa53b3e"

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_VERSION = "2026-03-11"

OUTPUT_FILE = "public/countdowns.json"

# Use Mountain Time so the countdown changes based on your
# actual local calendar date rather than GitHub's UTC date.
LOCAL_TIMEZONE = ZoneInfo("America/Denver")


# ============================================================
# NOTION API HELPERS
# ============================================================

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def notion_get(url):
    response = requests.get(url, headers=HEADERS)

    if not response.ok:
        print("Notion API error:")
        print(response.text)
        response.raise_for_status()

    return response.json()


def notion_post(url, body):
    response = requests.post(
        url,
        headers=HEADERS,
        json=body
    )

    if not response.ok:
        print("Notion API error:")
        print(response.text)
        response.raise_for_status()

    return response.json()


# ============================================================
# FIND THE DATABASE'S DATA SOURCE
# ============================================================

print("Retrieving Notion database...")

database_url = (
    f"https://api.notion.com/v1/databases/{DATABASE_ID}"
)

database = notion_get(database_url)

data_sources = database.get("data_sources", [])

if not data_sources:
    raise RuntimeError(
        "No data sources were found for this Notion database. "
        "Make sure your Notion integration has access to the database."
    )

# This database normally has one data source.
DATA_SOURCE_ID = data_sources[0]["id"]

print(f"Database: {DATABASE_ID}")
print(f"Data source: {DATA_SOURCE_ID}")


# ============================================================
# QUERY THE DATA SOURCE
# ============================================================

query_url = (
    f"https://api.notion.com/v1/data_sources/"
    f"{DATA_SOURCE_ID}/query"
)

pages = []
start_cursor = None

while True:

    body = {}

    if start_cursor:
        body["start_cursor"] = start_cursor

    data = notion_post(query_url, body)

    pages.extend(data.get("results", []))

    if not data.get("has_more"):
        break

    start_cursor = data.get("next_cursor")


print(f"Notion pages found: {len(pages)}")


# ============================================================
# PROPERTY HELPERS
# ============================================================

def get_property(properties, name):
    """
    Find a property by name, ignoring capitalization.
    """

    if name in properties:
        return properties[name]

    for key, value in properties.items():
        if key.lower() == name.lower():
            return value

    return None


def get_title(properties):
    """
    Get the database title/name.
    """

    prop = get_property(properties, "Name")

    # If the title property isn't called Name, find
    # whichever property is actually the title.
    if not prop:

        for value in properties.values():

            if value.get("type") == "title":
                prop = value
                break

    if not prop:
        return ""

    title_parts = prop.get("title", [])

    return "".join(
        part.get("plain_text", "")
        for part in title_parts
    ).strip()


def get_date(properties):
    """
    Get the Date property as YYYY-MM-DD.
    """

    prop = get_property(properties, "Date")

    if not prop:
        return None

    if prop.get("type") != "date":
        return None

    date_value = prop.get("date")

    if not date_value:
        return None

    start = date_value.get("start")

    if not start:
        return None

    return start[:10]


def get_select(properties, name):
    """
    Get the selected value of a Select property.
    """

    prop = get_property(properties, name)

    if not prop:
        return ""

    if prop.get("type") != "select":
        return ""

    selected = prop.get("select")

    if not selected:
        return ""

    return selected.get("name", "")


# ============================================================
# YEARLY DATE CALCULATION
# ============================================================

def next_yearly_occurrence(original_date, today):
    """
    Turn a stored birthday/event date into the next occurrence.

    Example:

        Stored: 2020-10-15
        Today:  2026-10-05

        Result: 2026-10-15
    """

    month = original_date.month
    day = original_date.day

    year = today.year

    # February 29 needs special handling.
    if month == 2 and day == 29:

        if calendar.isleap(year):
            candidate = date(year, 2, 29)
        else:
            candidate = date(year, 2, 28)

    else:

        candidate = date(year, month, day)

    # If this year's occurrence already happened,
    # use next year.
    if candidate < today:

        year += 1

        if month == 2 and day == 29:

            if calendar.isleap(year):
                candidate = date(year, 2, 29)
            else:
                candidate = date(year, 2, 28)

        else:

            candidate = date(year, month, day)

    return candidate


# ============================================================
# DETERMINE TODAY IN MOUNTAIN TIME
# ============================================================

today = date.today()

# Python's date.today() uses the machine's timezone.
# GitHub Actions runs in UTC, so get the date explicitly
# in Mountain Time instead.

from datetime import datetime

today = datetime.now(LOCAL_TIMEZONE).date()

print(f"Local date: {today}")


# ============================================================
# DETERMINE END OF NEXT MONTH
# ============================================================

if today.month == 12:

    next_month = 1
    next_month_year = today.year + 1

else:

    next_month = today.month + 1
    next_month_year = today.year


last_day = calendar.monthrange(
    next_month_year,
    next_month
)[1]

end_date = date(
    next_month_year,
    next_month,
    last_day
)

print(f"Looking through: {end_date}")


# ============================================================
# BUILD COUNTDOWN LIST
# ============================================================

countdowns = []

for page in pages:

    properties = page.get("properties", {})

    name = get_title(properties)
    date_string = get_date(properties)
    frequency = get_select(properties, "Frequency")
    countdown_type = get_select(properties, "Type")

    # Skip incomplete entries.
    if not name or not date_string:
        continue

    try:

        original_date = date.fromisoformat(date_string)

    except ValueError:

        print(
            f"Skipping {name}: "
            f"invalid date {date_string}"
        )

        continue


    # --------------------------------------------------------
    # Calculate next occurrence
    # --------------------------------------------------------

    if frequency.lower() == "yearly":

        event_date = next_yearly_occurrence(
            original_date,
            today
        )

    else:

        # Non-yearly dates are treated as one-time events.
        event_date = original_date


    # --------------------------------------------------------
    # Keep only dates from today through end of next month
    # --------------------------------------------------------

    if event_date < today:
        continue

    if event_date > end_date:
        continue


    # --------------------------------------------------------
    # Calculate days remaining
    # --------------------------------------------------------

    days = (event_date - today).days


    if days == 1:

        day_text = "1 day"

    else:

        day_text = f"{days} days"


    display_text = (
        f"{day_text} until {name}"
    )


    countdowns.append({
        "name": name,
        "date": event_date.isoformat(),
        "days": days,
        "frequency": frequency,
        "type": countdown_type,
        "text": display_text
    })


# ============================================================
# SORT BY DATE
# ============================================================

countdowns.sort(
    key=lambda item: (
        item["date"],
        item["name"].lower()
    )
)


# ============================================================
# LIMIT TO THREE
# ============================================================

countdowns = countdowns[:3]


# ============================================================
# CREATE JSON
# ============================================================

output = {
    "updated": today.isoformat(),
    "through": end_date.isoformat(),
    "count": len(countdowns),
    "countdowns": countdowns
}


# Make sure public exists.
os.makedirs("public", exist_ok=True)


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        output,
        file,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# PRINT RESULTS FOR GITHUB ACTIONS
# ============================================================

print("")
print("========================================")
print("COUNTDOWNS")
print("========================================")

if not countdowns:

    print("No upcoming countdowns.")

else:

    for item in countdowns:

        print(
            f"{item['date']} | "
            f"{item['text']}"
        )

print("")
print(f"Created: {OUTPUT_FILE}")
print(f"Showing: {len(countdowns)} countdown(s)")
print("========================================")