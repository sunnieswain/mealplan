import requests
from datetime import date, timedelta
import json
import os

# API_URL = f"https://api.notion.com/v1/data_sources/{DATA_SOURCE_ID}/query"
# #API_URL = f"https://api.notion.com/v1/databases/{DATABASE_ID}"
# OUTPUT_FILE = "public/output.json"
TOKEN = os.environ["NOTION_TOKEN"]

# def getRecipeName():
#     recipe_db_id = "d78cdf5b46e34bfb9ebcfe52d67235d4"
#     data_source_id = "395b1fcb-a217-4786-b8c1-a35129a8c503"
#     # This url is for getting a DB object
#     # url = f"https://api.notion.com/v1/databases/{recipe_db_id}"
#     url = f"https://api.notion.com/v1/data_sources/{data_source_id}/query?filter_properties[]=title"

#     response = getResponse(url)
#     print(response.text)

def getMealPlan():
    meal_plan_db_id = "f8ef2799fff648f6b3ad0ea4324826c5"
    data_source_id = "8c31a78f-85de-4735-bd3f-66ead3f7bcfa"
    url = f"https://api.notion.com/v1/data_sources/{data_source_id}/query?filter_properties[]=Day of Week&filter_properties[]=Recipe Name&filter_properties[]=Note"

    today = date.today()

    # Sunday of this week
    week_start = today - timedelta(days=(today.weekday() + 1) % 7)

    # Sunday of next week
    week_end = week_start + timedelta(days=7)

    filter_body = {
        "and": [
            {
                "property": "Date",
                "date": {
                    "on_or_after": week_start.isoformat()
                }
            },
            {
                "property": "Date",
                "date": {
                    "before": week_end.isoformat()
                }
            }
        ]
    }

    payload = {
        "sorts": [
            {
                "property": "Date",
                "direction": "ascending"
            }
        ],
        "filter": filter_body,
        #"start_cursor": "<string>",
        "page_size": 8,
        "is_archived": False
    }

    response = getResponse(url, payload)

    if(response):
        results = response["results"]
        meals = {}

        for recipe_obj in results:
            day = recipe_obj["properties"]["Day of Week"]["formula"]["string"]
            recipes_arr = recipe_obj["properties"]["Recipe Name"]["rollup"]["array"] # returns an array
            recipes_text = ""
            recipes = ""
            if len(recipes_arr) > 0:
                for recipe in recipes_arr:
                    if recipes_text:
                        recipes_text += ", "
                    recipes_text += recipe["title"][0]["plain_text"]

            note = recipe_obj["properties"]["Note"]["rich_text"]
            note_text = ""
            if len(note) > 0:
                note_text = note[0]["plain_text"]

            if recipes_text:
                if note_text:
                    recipes = f"{recipes_text}: {note_text}"
                else:
                    recipes = recipes_text
            elif note_text:
                recipes = note_text


            meals[day] = recipes

        print(meals)
        with open("public/mealplan.json", "w") as file:
            json.dump(meals, file, indent=4)


    

def getResponse(url, payload = None):
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f"Bearer {TOKEN}"
    }

    response = None

    try:
        if payload:
            headers["Content-Type"] = "application/json"
            response = requests.post(url, json=payload, headers=headers)
        else:
            response = requests.get(url, headers=headers)

        # Raise an exception for HTTP errors (e.g., 404, 500)
        response.raise_for_status() 
        
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.JSONDecodeError:
        # Triggered if the response body is not valid JSON (e.g., raw HTML)
        print("Response could not be parsed as JSON.")
    except Exception as err:
        print(f"An unexpected error occurred: {err}")
        print(f"Notion response: {response.text}")




# def getMealPlan():
#     headers = {
#         "Notion-Version": f"2026-03-11",
#         "Authorization": f"Bearer {TOKEN}"
#     }

#     payload = {
#         "sorts": [{ "property": "<string>" }],
#         "filter": { "or": [
#                 {
#                     "title": { "equals": "<string>" },
#                     "property": "<string>",
#                     "type": "title"
#                 }
#             ] },
#         "start_cursor": "<string>",
#         "page_size": 123,
#         "is_archived": True
#     }

#     response = requests.post(API_URL, headers=headers, json=payload)

#     response.raise_for_status()

#     data = response.json()

#     print(data)


def main():
    # Download the JSON from the API
    getMealPlan()
    #getRecipeName()
    # response = requests.get(API_URL, timeout=30)

    # # Stop if the API returned an error
    # response.raise_for_status()

    # # Convert the API response into Python data
    # data = response.json()

    # # Do whatever processing you need here
    # output = {
    #     "items": [
    #         item
    #         for item in data["items"]
    #         if item["active"]
    #     ]
    # }

    # # Write the result to a JSON file
    # with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    #     json.dump(output, file, indent=2)

    # print(f"Wrote {len(output['items'])} items to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()