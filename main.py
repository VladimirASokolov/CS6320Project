import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText

import spacy
import requests
from difflib import get_close_matches
import re

nlp = spacy.load("en_core_web_sm")

API_KEY = "API KEY"

user_state = {
    "location": {"latitude": 40.7128, "longitude": -74.0060},
    "radius": 50000,
    "includedTypes": [],
    "excludedTypes": [],
    "max_results": 5
}

PLACE_TYPE_SET = {
    "acai_shop", "afghani_restaurant", "african_restaurant", "american_restaurant", "asian_restaurant",
    "bagel_shop", "bakery", "bar", "bar_and_grill", "barbecue_restaurant", "brazilian_restaurant",
    "breakfast_restaurant", "brunch_restaurant", "buffet_restaurant", "cafe", "cafeteria", "candy_store",
    "cat_cafe", "chinese_restaurant", "chocolate_factory", "chocolate_shop", "coffee_shop", "confectionery",
    "deli", "dessert_restaurant", "dessert_shop", "diner", "dog_cafe", "donut_shop", "fast_food_restaurant",
    "fine_dining_restaurant", "food_court", "french_restaurant", "greek_restaurant", "hamburger_restaurant",
    "ice_cream_shop", "indian_restaurant", "indonesian_restaurant", "italian_restaurant", "japanese_restaurant",
    "juice_shop", "korean_restaurant", "lebanese_restaurant", "meal_delivery", "meal_takeaway",
    "mediterranean_restaurant", "mexican_restaurant", "middle_eastern_restaurant", "pizza_restaurant", "pub",
    "ramen_restaurant", "restaurant", "sandwich_shop", "seafood_restaurant", "spanish_restaurant", "steak_house",
    "sushi_restaurant", "tea_house", "thai_restaurant", "turkish_restaurant", "vegan_restaurant",
    "vegetarian_restaurant", "vietnamese_restaurant", "wine_bar"
}

KEYWORD_TO_TYPE = {t.replace('_', ' ').replace('restaurant', '').strip(): t for t in PLACE_TYPE_SET}

app = ttk.Window(themename="darkly")
app.title("Food Recommendation Chatbot")
app.geometry("1000x600")

main_frame = ttk.Frame(app)
main_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

chat_frame = ttk.Frame(main_frame)
chat_frame.pack(side=LEFT, fill=BOTH, expand=True)

chat_history = ScrolledText(chat_frame, wrap='word', width=80, height=30)
chat_history.pack(padx=5, pady=5, fill=BOTH, expand=True)
chat_history._text.configure(state="disabled")

entry_frame = ttk.Frame(chat_frame)
entry_frame.pack(fill=X, pady=(0, 5))

user_entry = ttk.Entry(entry_frame, width=80)
user_entry.pack(side=LEFT, fill=X, expand=True, padx=(5, 0))

send_button = ttk.Button(entry_frame, text="Send")
send_button.pack(side=LEFT, padx=5)

side_panel = ttk.Frame(main_frame, width=250)
side_panel.pack(side=RIGHT, fill=Y)

all_label = ttk.Label(side_panel, text="Available Types", font=("Arial", 10, "bold"))
all_label.pack(anchor=W, padx=5)
all_types_box = ScrolledText(side_panel, height=10, width=30, state="disabled")
all_types_box.pack(padx=5, pady=2)

included_label = ttk.Label(side_panel, text="Included Types", font=("Arial", 10, "bold"))
included_label.pack(anchor=W, padx=5)
included_box = ScrolledText(side_panel, height=5, width=30, state="disabled")
included_box.pack(padx=5, pady=2)

excluded_label = ttk.Label(side_panel, text="Excluded Types", font=("Arial", 10, "bold"))
excluded_label.pack(anchor=W, padx=5)
excluded_box = ScrolledText(side_panel, height=5, width=30, state="disabled")
excluded_box.pack(padx=5, pady=2)

def update_side_panel():
    available = sorted(PLACE_TYPE_SET - set(user_state['includedTypes']) - set(user_state['excludedTypes']))
    def fill_box(box, lines):
        text_widget = box._text
        text_widget.configure(state="normal")
        text_widget.delete(1.0, 'end')
        text_widget.insert('end', '\n'.join(lines))
        text_widget.configure(state="disabled")
    fill_box(all_types_box, available)
    fill_box(included_box, user_state["includedTypes"])
    fill_box(excluded_box, user_state["excludedTypes"])

def match_place_type(text):
    if text in KEYWORD_TO_TYPE:
        return KEYWORD_TO_TYPE[text]
    matches = get_close_matches(text, KEYWORD_TO_TYPE.keys(), n=1, cutoff=0.6)
    if matches:
        return KEYWORD_TO_TYPE[matches[0]]
    return None

def update_preferences(message):
    doc = nlp(message.lower())
    added_types = []
    removed_types = []

    for ent in doc.ents:
        matched_type = match_place_type(ent.text)
        if matched_type:
            if any(neg in ent.sent.text for neg in ["no", "not", "don't", "do not", "avoid"]):
                if matched_type not in user_state["excludedTypes"]:
                    user_state["excludedTypes"].append(matched_type)
                    user_state["includedTypes"] = [t for t in user_state["includedTypes"] if t != matched_type]
                    removed_types.append(matched_type)
            else:
                if matched_type not in user_state["includedTypes"]:
                    user_state["includedTypes"].append(matched_type)
                    user_state["excludedTypes"] = [t for t in user_state["excludedTypes"] if t != matched_type]
                    added_types.append(matched_type)

    for chunk in doc.noun_chunks:
        matched_type = match_place_type(chunk.text.strip())
        if matched_type:
            if any(neg in chunk.root.head.text for neg in ["no", "not", "don't", "avoid"]):
                if matched_type not in user_state["excludedTypes"]:
                    user_state["excludedTypes"].append(matched_type)
                    user_state["includedTypes"] = [t for t in user_state["includedTypes"] if t != matched_type]
                    removed_types.append(matched_type)
            else:
                if matched_type not in user_state["includedTypes"]:
                    user_state["includedTypes"].append(matched_type)
                    user_state["excludedTypes"] = [t for t in user_state["excludedTypes"] if t != matched_type]
                    added_types.append(matched_type)

    update_side_panel()
    return added_types, removed_types

def search_restaurants():
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.primaryType,places.googleMapsUri"
    }
    body = {
        "includedTypes": user_state.get("includedTypes", ["restaurant"]),
        "excludedTypes": user_state.get("excludedTypes", ["store", "movie_theatre", "gas_station", "arena"]),
        "maxResultCount": user_state["max_results"],
        "locationRestriction": {
            "circle": {
                "center": user_state["location"],
                "radius": user_state["radius"]
            }
        }
    }
    response = requests.post(url, headers=headers, json=body)
    return response.json().get("places", [])

def get_location_coordinates(place_name):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.location"
    }
    body = {
        "textQuery": place_name,
        "maxResultCount": 1
    }
    response = requests.post(url, headers=headers, json=body)
    results = response.json().get("places", [])
    if results:
        return results[0]["location"]
    return None

def parse_radius(text):
    match = re.search(r'(\d+(\.\d+)?)\s*(mile|miles)', text)
    if match:
        return int(float(match.group(1)) * 1609)
    return None

def parse_location(text):
    loc_keywords = ["in", "at", "set location to", "i am in", "change location to"]
    for keyword in loc_keywords:
        if keyword in text.lower():
            loc_part = text.lower().split(keyword)[-1].strip().rstrip('.')
            if loc_part:
                return loc_part
    return None

def handle_user_input():
    message = user_entry.get()
    if not message.strip():
        return

    if message.strip().lower() in ['q', 'quit']:
        app.quit()
    elif message.strip().lower() in ['r', 'restart']:
        user_state["includedTypes"] = []
        user_state["excludedTypes"] = []
        update_side_panel()
        
        chat_history.text.configure(state="normal")
        chat_history.insert('end', "Restarting session...\n")
        chat_history.insert('end', "Welcome! Type 'r' to restart, 'q' to quit.\n")
        chat_history.text.configure(state="disabled")
        return

    chat_history.text.configure(state="normal")
    chat_history.insert('end', f"You: {message}\n")
    user_entry.delete(0, 'end')

    location_name = parse_location(message)
    if location_name:
        coords = get_location_coordinates(location_name)
        if coords:
            user_state["location"] = coords
            chat_history.insert('end', f"Bot: Updated location to {location_name}.\n")
        else:
            chat_history.insert('end', f"Bot: Could not find location '{location_name}'.\n")

    new_radius = parse_radius(message)
    if new_radius:
        user_state["radius"] = new_radius
        chat_history.insert('end', f"Bot: Updated search radius to {new_radius // 1609} miles.\n")

    added, removed = update_preferences(message)
    places = search_restaurants()

    bot_reply = ""
    if added:
        bot_reply += "Included: " + ", ".join(added) + "\n"
    if removed:
        bot_reply += "Excluded: " + ", ".join(removed) + "\n"

    if places:
        bot_reply += "\nTop recommendations:\n"
        for place in places:
            bot_reply += f"- {place['displayName']['text']} ({place.get('rating', 'N/A')}⭐)\n  {place.get('formattedAddress', '')}\n  {place.get('googleMapsUri', '')}\n\n"
    else:
        bot_reply += "\nNo matching places found."

    chat_history.insert('end', f"Bot: {bot_reply}\n\n")
    chat_history.text.configure(state="disabled")
    chat_history._text.yview('end')

send_button.config(command=handle_user_input)

def initialize():
    chat_history.text.configure(state="normal")
    chat_history.insert('end', "Welcome! Type 'r' to restart, 'q' to quit.\n")
    chat_history.text.configure(state="disabled")
    update_side_panel()

if __name__ == "__main__":
    initialize()
    app.mainloop()