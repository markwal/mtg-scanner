import requests
import json
from urllib.parse import quote_plus

def CanonicalizeCard(title, set_code=None, collector_number=None):
    if set_code and collector_number:
        # try and look up by set_code and collector_number first
        set_code = set_code.split("/")[0]
        if len(set_code) in range(1, 4) and len(collector_number) in range(1, 4) and \
                set_code.isalnum() and collector_number.isdigit():
            response = requests.get(f'https://api.scryfall.com/cards/{set_code}/{collector_number}')
            if response.status_code == 200:
                card = response.json()
                if "name" in card and card["name"] == title:
                    return True, f'{title} ({set_code}) {collector_number}'

    # didn't find an exact match via set code and collector number
    response = requests.get(f'https://api.scryfall.com/cards/named?fuzzy={quote_plus(title)}')
    if response.status_code != 200:
        return False, title
    card = response.json()
    if not "name" in card:
        return False, title
    title = card["name"]

    if not "prints_search_uri" in card:
        return "fuzzy-title", title

    response = requests.get(card["prints_search_uri"])
    if response.status_code != 200:
        return "fuzzy-title", title

    json = response.json()
    data = json["data"] if "data" in json else None

    candidate = None
    for card in data:
        if "set" in card and card["set"] == set_code:
            candidate = card

            if 



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
