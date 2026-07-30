"""
Thin wrapper around the official Clash Royale API.
Docs: https://developer.clashroyale.com/#/documentation
"""
import requests
import json

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
    # print("Status:", resp.status_code)
    # print("Response:", resp.text)
    resp.raise_for_status()
    return resp.json()


def get_battlelog(tag: str) -> list:
    """Fetch a player's recent battles (typically last ~25)."""
    url = f"{BASE_URL}/players/{_tag_encoded(tag)}/battlelog"
    resp = requests.get(url, headers=_headers())
    resp.raise_for_status()
    return resp.json()

def get_top_ladder_players(limit: int = 30) -> list:
    url = f"{BASE_URL}/locations/57000178/rankings/players"
    resp = requests.get(url, headers=_headers(), params={"limit": limit})
    print("Status:", resp.status_code)
    print("Response:", resp.text[:500])
    resp.raise_for_status()
    return resp.json().get("items", [])

def get_clan_members(clan_tag: str) -> list:
    """
    Fetch member list of a clan. Returns list of dicts with at least
    'tag' and 'name'. Clan tags need the same # -> %23 encoding as
    player tags.
    """
    url = f"{BASE_URL}/clans/{_tag_encoded(clan_tag)}/members"
    resp = requests.get(url, headers=_headers())
    resp.raise_for_status()
    return resp.json().get("items", [])


# def get_locations() -> list:
#     """List all valid location IDs (needed for rankings endpoints)."""
#     url = f"{BASE_URL}/locations"
#     resp = requests.get(url, headers=_headers())
#     resp.raise_for_status()
#     return resp.json().get("items", [])


# if __name__ == "__main__":
#     sample_tag = "#YUP02GRQG" # replace with a real tag to test
#     print(get_player(sample_tag))
#     print("\n--- BATTLE LOG ---\n")
#     print(get_battlelog(sample_tag))


def print_player_summary(player: dict):
    print(f"Player: {player['name']} ({player['tag']})")
    print(f"Trophies: {player['trophies']} (best: {player['bestTrophies']})")
    print(f"Wins/Losses: {player['wins']}/{player['losses']}")
    print(f"Clan: {player.get('clan', {}).get('name', 'None')}")
    print("Current deck:")
    for card in player['currentDeck']:
        print(f"  - {card['name']} (level {card['level']}, elixir {card['elixirCost']})")


def print_battlelog_summary(battles: list, my_tag: str):
    my_tag = my_tag.strip("#").upper()
    print(f"\nShowing {len(battles)} recent battles:\n")
    for b in battles:
        me = next(p for p in b['team'] if p['tag'].strip("#").upper() == my_tag)
        opp = b['opponent'][0]
        result = "WIN" if me['trophyChange'] > 0 else "LOSS"
        my_cards = ", ".join(c['name'] for c in me['cards'])
        print(f"[{b['battleTime']}] {result} ({me['trophyChange']:+d} trophies) "
              f"vs {opp['name']} | Crowns: {me['crowns']}-{opp['crowns']}")
        print(f"  My deck: {my_cards}")
        print()


if __name__ == "__main__":
    sample_tag = "#YUP02GRQG"

    player = get_player(sample_tag)
    print_player_summary(player)

    battles = get_battlelog(sample_tag)
    print_battlelog_summary(battles, sample_tag)


# if __name__ == "__main__":
#     locations = get_locations()
#     for loc in locations:
#         print(loc["id"], loc["name"])

# if __name__ == "__main__":
#     members = get_clan_members("#QLCYCPPC")
#     for m in members:
#         print(m["tag"], m["name"])