import requests
import json
from urllib.parse import quote_plus
import logging

def canonicalizeCard(title, set_code=None, collector_number=None):
    logging.info("calling scryfall")
    if set_code and collector_number:
        # try and look up by set_code and collector_number first
        set_code = set_code.casefold()
        collector_number = collector_number.split("/")[0]
        logging.info(f'set_code: {set_code}')
        logging.info(f'collector_number: {collector_number}')
        if len(set_code) in range(1, 4) and len(collector_number) in range(1, 4) and \
                set_code.isalnum() and collector_number.isdigit():
            url = f'https://api.scryfall.com/cards/{set_code}/{collector_number}'
            logging.info(f'GET {url}')
            response = requests.get(url)
            logging.info(f'response.status = {response.status_code}')
            if response.status_code == 200:
                card = response.json()
                if "name" in card and card["name"] == title:
                    return True, f'{title} ({set_code}) {collector_number}'

    # didn't find an exact match via set code and collector number
    url = f'https://api.scryfall.com/cards/named?fuzzy={quote_plus(title)}'
    logging.info(f'fuzzy: GET {url}')
    response = requests.get(url)
    logging.info(f'response.status = {response.status_code}')
    if response.status_code != 200:
        return False, title
    card = response.json()
    if not "name" in card:
        return False, title
    title = card["name"]

    if not "prints_search_uri" in card or set_code is None or collector_number is None:
        return "fuzzy-title", title

    logging.info(f'prints: GET {card["prints_search_uri"]}')
    response = requests.get(card["prints_search_uri"])
    logging.info(f'response.status = {response.status_code}')
    if response.status_code != 200:
        return "fuzzy-title", title

    json = response.json()
    data = json["data"] if "data" in json else None

    candidate = None
    for card in data:
        if "set" in card and card["set"].casefold() == set_code:
            candidate = card

            if "collector_number" in card and card["collector_number"] == collector_number:
                return True, f'{title} ({card["set"]}) {card["collector_number"]}'

    if candidate:
        return "fuzzy-title-set", f'{title} ({candidate["set"]}) {candidate["collector_number"]}'

    return "fuzzy-title", title

