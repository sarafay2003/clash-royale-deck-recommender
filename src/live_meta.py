"""
Live meta aggregator.

Instead of relying on a saved dataset, this fetches fresh data from the
Clash Royale API every time it's called: pulls a sample of top ladder
players, grabs their most recent battles (the API only ever returns each
player's last ~25 anyway, so this is always recent by nature), and
computes win rates per deck from that fresh sample.

Nothing here is saved to disk - it's meant to be called on-demand.
"""
import time
from collections import defaultdict
from src.api_client import get_clan_members, get_battlelog


from src.api_client import get_top_ladder_players, get_battlelog


def _deck_key(cards: list) -> frozenset:
    """
    Turn a list of card dicts into a hashable, order-independent key
    so the same 8 cards always produce the same key regardless of the
    order they were played in.
    """
    return frozenset(c["name"] for c in cards)



def collect_live_battles(seed_clan_tag: str = "#QLCYCPPC", delay_seconds: float = 0.5) -> list:
    """
    Fetch battle logs from a clan's members, live. Clan-members is a
    reliable seed source since the player-rankings endpoint has proven
    unreliable (empty results even on valid requests).
    """
    members = get_clan_members(seed_clan_tag)
    all_battles = []

    for i, member in enumerate(members):
        tag = member["tag"]
        try:
            battles = get_battlelog(tag)
            all_battles.extend(battles)
        except Exception as e:
            print(f"  Skipped {tag}: {e}")

        time.sleep(delay_seconds)

        if (i + 1) % 10 == 0:
            print(f"  Fetched {i + 1}/{len(members)} members...")

    return all_battles

def compute_deck_winrates(battles: list, min_games: int = 3) -> list:
    """
    Given a flat list of battles, compute win rate per exact deck
    (8-card combination). Only counts battles with a trophyChange field
    (regular ladder matches) - skips tournaments/challenges/events which
    don't have a win/loss trophy signal. Only includes decks seen at
    least `min_games` times.
    """
    stats = defaultdict(lambda: {"wins": 0, "losses": 0})

    for battle in battles:
        for player in battle.get("team", []):
            trophy_change = player.get("trophyChange")
            if trophy_change is None:
                continue  # not a ladder match - skip

            deck = _deck_key(player["cards"])
            if trophy_change > 0:
                stats[deck]["wins"] += 1
            else:
                stats[deck]["losses"] += 1

    results = []
    for deck, record in stats.items():
        total = record["wins"] + record["losses"]
        if total < min_games:
            continue
        win_rate = record["wins"] / total
        results.append({
            "deck": sorted(deck),
            "games": total,
            "wins": record["wins"],
            "losses": record["losses"],
            "win_rate": round(win_rate * 100, 1),
        })

    results.sort(key=lambda r: r["win_rate"], reverse=True)
    return results


def print_meta_report(deck_stats: list, top_n: int = 10):
    print(f"\nTop {top_n} decks by live win rate (min games filter applied):\n")
    for i, entry in enumerate(deck_stats[:top_n], start=1):
        deck_str = ", ".join(entry["deck"])
        print(f"{i}. {entry['win_rate']}% win rate "
              f"({entry['wins']}W-{entry['losses']}L, {entry['games']} games)")
        print(f"   {deck_str}\n")


if __name__ == "__main__":
    print("Fetching live battle data from clan members...")
    battles = collect_live_battles()
    print(f"\nCollected {len(battles)} battle entries.")

    deck_stats = compute_deck_winrates(battles, min_games=2)
    print_meta_report(deck_stats, top_n=10)