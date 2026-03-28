import json
import os
import requests
from google.adk.tools import ToolContext


WARDROBE_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wardrobe.json")

# Base URL for wardrobe images hosted on GCS.
# Set to "" to use local relative paths (for local dev with adk web).
# Set to GCS bucket URL for Cloud Run deployment.
IMAGE_BASE_URL = os.environ.get(
    "IMAGE_BASE_URL",
    "https://storage.googleapis.com/wardrobe-planner-images"
)


def get_weather(city: str, tool_context: ToolContext) -> str:
    """
    Fetches real-time weather for a given city using Open-Meteo API (no API key required).
    Stores the result in session state for other agents to use.

    Args:
        city: Name of the city to get weather for.

    Returns:
        A human-readable weather summary string.
    """
    try:
        # Step 1: Geocode city name to lat/lon
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_resp = requests.get(geo_url, params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=10)
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return f"Could not find location for '{city}'. Please check the city name."

        location = geo_data["results"][0]
        lat, lon = location["latitude"], location["longitude"]
        city_name = location.get("name", city)
        country = location.get("country", "")

        # Step 2: Get current weather
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_resp = requests.get(
            weather_url,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": ["temperature_2m", "weathercode", "windspeed_10m"],
                "timezone": "auto",
            },
            timeout=10,
        )
        weather_data = weather_resp.json()
        current = weather_data["current"]

        temp_c = current["temperature_2m"]
        wind_kph = current["windspeed_10m"]
        wcode = current["weathercode"]

        # Map WMO weather codes to readable conditions
        condition = _wmo_to_condition(wcode)

        # Classify weather bucket for outfit logic
        if temp_c >= 28:
            weather_bucket = "warm"
        elif temp_c >= 15:
            weather_bucket = "mild"
        else:
            weather_bucket = "cold"

        weather_summary = {
            "city": f"{city_name}, {country}",
            "temperature_c": temp_c,
            "condition": condition,
            "weather_bucket": weather_bucket,
            "wind_kph": wind_kph,
        }

        # Store in session state so sub-agents can read it
        tool_context.state["weather"] = weather_summary

        return (
            f"Weather in {city_name}, {country}: {temp_c}°C, {condition}. "
            f"Wind: {wind_kph} km/h. Classification: {weather_bucket.upper()}."
        )

    except requests.RequestException as e:
        fallback = {"city": city, "temperature_c": 25, "condition": "clear", "weather_bucket": "warm", "wind_kph": 10}
        tool_context.state["weather"] = fallback
        return f"Could not fetch live weather (network error). Defaulting to warm/clear conditions for outfit selection."


def load_wardrobe(tool_context: ToolContext) -> str:
    """
    Loads the wardrobe catalog from wardrobe.json and stores it in session state.

    Returns:
        A confirmation message with item counts.
    """
    with open(WARDROBE_JSON_PATH, "r", encoding="utf-8") as f:
        wardrobe = json.load(f)

    # Prepend base URL to all image_path fields if IMAGE_BASE_URL is set
    if IMAGE_BASE_URL:
        for item in wardrobe.get("clothing", []) + wardrobe.get("accessories", []):
            item["image_path"] = f"{IMAGE_BASE_URL}/{item['image_path']}"

    tool_context.state["wardrobe"] = wardrobe

    clothing_count = len(wardrobe.get("clothing", []))
    accessory_count = len(wardrobe.get("accessories", []))

    return f"Wardrobe loaded: {clothing_count} clothing items and {accessory_count} accessories available."


def get_wardrobe_context(tool_context: ToolContext) -> str:
    """
    Retrieves wardrobe items, weather, and previous outfit history from session state.
    Used by outfit selector and styling agents to make decisions.

    Returns:
        A formatted JSON string containing all context needed for selection.
    """
    wardrobe = tool_context.state.get("wardrobe", {})
    weather = tool_context.state.get("weather", {})
    previous_outfits = tool_context.state.get("previous_outfits", [])
    tried_in_loop = tool_context.state.get("tried_in_loop", [])
    user_preferences = tool_context.state.get("user_preferences", {})

    context = {
        "weather": weather,
        "user_preferences": user_preferences,
        "previous_outfits": previous_outfits,
        "avoid_these_outfits_in_current_attempt": tried_in_loop,
        "available_clothing": wardrobe.get("clothing", []),
        "available_accessories": wardrobe.get("accessories", []),
    }

    return json.dumps(context, indent=2)


def check_and_save_outfit(outfit_ids: list[str], tool_context: ToolContext) -> dict:
    """
    Validates that the selected outfit has not been suggested before.
    If it is fresh, saves it to session state and signals the LoopAgent to stop.
    If it is a duplicate, records the attempt so the agent can try a different combination.

    Args:
        outfit_ids: List of clothing item IDs in the proposed outfit (e.g. ["top2", "bottom1"]).

    Returns:
        A dict with status ("accepted" or "duplicate") and a message.
    """
    previous_outfits = tool_context.state.get("previous_outfits", [])
    tried_in_loop = tool_context.state.get("tried_in_loop", [])

    proposed_set = frozenset(outfit_ids)

    # Check against all previously shown outfits
    for prev in previous_outfits:
        if frozenset(prev) == proposed_set:
            # Record this attempt so the loop agent knows to avoid it next iteration
            tool_context.state["tried_in_loop"] = tried_in_loop + [outfit_ids]
            return {
                "status": "duplicate",
                "message": (
                    f"This outfit ({', '.join(outfit_ids)}) was already suggested. "
                    "Please select a completely different combination of items."
                ),
            }

    # Check against attempts made in the current loop (shouldn't repeat within same loop)
    for tried in tried_in_loop:
        if frozenset(tried) == proposed_set:
            tool_context.state["tried_in_loop"] = tried_in_loop + [outfit_ids]
            return {
                "status": "duplicate",
                "message": (
                    f"You already tried {', '.join(outfit_ids)} in this round. "
                    "Pick a different combination."
                ),
            }

    # Fresh outfit — save it
    tool_context.state["previous_outfits"] = previous_outfits + [outfit_ids]
    tool_context.state["current_outfit_ids"] = outfit_ids
    tool_context.state["tried_in_loop"] = []  # Reset for next request

    # Signal LoopAgent to stop iterating
    tool_context.actions.escalate = True

    return {
        "status": "accepted",
        "outfit_ids": outfit_ids,
        "message": "Fresh outfit confirmed! Proceeding to styling.",
    }


def _wmo_to_condition(code: int) -> str:
    """Maps WMO weather code to a readable condition string."""
    if code == 0:
        return "clear sky"
    elif code in (1, 2, 3):
        return "partly cloudy"
    elif code in (45, 48):
        return "foggy"
    elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        return "rainy"
    elif code in (71, 73, 75, 77, 85, 86):
        return "snowy"
    elif code in (95, 96, 99):
        return "thunderstorm"
    else:
        return "cloudy"
