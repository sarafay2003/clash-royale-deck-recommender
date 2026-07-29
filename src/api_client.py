"""
Thin wrapper around the official Clash Royale API.
Docs: https://developer.clashroyale.com/#/documentation
"""
import requests
from src.config import CLASH_ROYALE_API_KEY, BASE_URL


def _headers():
    return {"Authorization": f"Bearer {CLASH_ROYALE_API_KEY}"}


def _tag_encoded(tag: str) -> str:
    """Player/clan tags start with '#' which must be URL-encoded as %23."""
    tag = tag.strip()
    if not tag.startswith("#"):
        tag = "#" + tag
    return tag.replace("#", "%23")


def get_player(tag: str) -> dict:
    url = f"{BASE_URL}/players/{_tag_encoded(tag)}"
    resp = requests.get(url, headers=_headers())
    print("Status:", resp.status_code)
    print("Response:", resp.text)
    resp.raise_for_status()
    return resp.json()


def get_battlelog(tag: str) -> list:
    """Fetch a player's recent battles (typically last ~25)."""
    url = f"{BASE_URL}/players/{_tag_encoded(tag)}/battlelog"
    resp = requests.get(url, headers=_headers())
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    sample_tag = "#YUP02GRQG"  # replace with a real tag to test
    print(get_player(sample_tag))