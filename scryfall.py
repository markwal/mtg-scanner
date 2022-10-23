import requests
import json

response = requests.get("https://api.scryfall.com/cards/named?fuzzy=muldrotha")
print(response.status_code)
card = response.json()
if "name" in card:
    print(card["name"])
print(card["set"])
print(card["collector_number"])

uri = card["prints_search_uri"]
response = requests.get(uri)
cards = response.json()

print(json.dumps(cards, indent=4))
for obj in cards["data"]:
    print(obj["set"], obj["collector_number"])
