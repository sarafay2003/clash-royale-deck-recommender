"""
Live meta aggregator.

Instead of relying on a saved dataset, this fetches fresh data from the
Clash Royale API every time it's called: pulls a sample of players
starting from a clan seed, snowballs outward through opponents, and
computes win rates per archetype from that fresh sample. Also tracks
the most common full 8-card decks within each archetype so
recommendations can show an actual buildable deck.

Nothing here is saved to disk - it's meant to be called on-demand.
"""
import time
from collections import defaultdict

from src.api_client import get_clan_members, get_battlelog
from src.archetypes import get_archetypes
from src.personal import compute_personal_archetype_stats, blend_scores, print_recommendations


def collect_live_battles(
    seed_clan_tag: str = "#QLCYCPPC",
    max_players: int = 300,
    max_rounds: int = 4,
    delay_seconds: float = 0.3,
) -> list:
    """
    Fetch battle logs starting from a clan's members, then snowball
    outward: every opponent tag seen in a battle becomes a new player
    to query in the next round. Stops when either max_players is
    reached or max_rounds completes, whichever comes first.
    """
    seen_tags = set()
    to_query = [m["tag"] for m in get_clan_members(seed_clan_tag)]
    all_battles = []
    round_num = 0

    for round_num in range(1, max_rounds + 1):
        if not to_query or len(seen_tags) >= max_players:
            break

        print(f"\nRound {round_num}: querying {len(to_query)} players "
              f"({len(seen_tags)} seen so far)...")

        next_round_tags = set()

        for tag in to_query:
            if tag in seen_tags or len(seen_tags) >= max_players:
                continue
            seen_tags.add(tag)

            try:
                battles = get_battlelog(tag)
                all_battles.extend(battles)

                for battle in battles:
                    for opp in battle.get("opponent", []):
                        opp_tag = opp.get("tag")
                        if opp_tag and opp_tag not in seen_tags:
                            next_round_tags.add(opp_tag)

            except Exception as e:
                print(f"  Skipped {tag}: {e}")

            time.sleep(delay_seconds)

            if len(seen_tags) % 25 == 0:
                print(f"  ...{len(seen_tags)} players queried so far")

        to_query = list(next_round_tags)

    print(f"\nDone. Queried {len(seen_tags)} unique players across "
          f"{round_num} round(s), collected {len(all_battles)} battles.")
    return all_battles


def compute_archetype_winrates(battles: list, min_games: int = 10, min_unique_players: int = 4) -> list:
    """
    Groups battles by archetype (win condition) instead of exact deck -
    much more data-dense, so real coverage is possible even with a few
    hundred players. Also tracks the most common full 8-card decks
    within each archetype, including each card's icon URL from the API,
    so recommendations can show an actual buildable deck with images.
    """
    stats = defaultdict(lambda: {
        "wins": 0, "losses": 0, "players": set(),
        "deck_counts": defaultdict(int),
    })
    card_icons = {}  # card name -> icon URL, built up as we see cards

    for battle in battles:
        for player in battle.get("team", []):
            trophy_change = player.get("trophyChange")
            if trophy_change is None:
                continue

            for c in player["cards"]:
                icon = c.get("iconUrls", {}).get("medium")
                if icon:
                    card_icons[c["name"]] = icon

            full_deck = tuple(sorted(c["name"] for c in player["cards"]))

            for archetype in get_archetypes(player["cards"]):
                stats[archetype]["players"].add(player["tag"])
                stats[archetype]["deck_counts"][full_deck] += 1
                if trophy_change > 0:
                    stats[archetype]["wins"] += 1
                else:
                    stats[archetype]["losses"] += 1

    results = []
    for archetype, record in stats.items():
        total = record["wins"] + record["losses"]
        unique_players = len(record["players"])
        if total < min_games or unique_players < min_unique_players:
            continue
        win_rate = record["wins"] / total

        top_deck, top_deck_count = max(
            record["deck_counts"].items(), key=lambda kv: kv[1]
        )
        example_deck = [
            {"name": name, "icon": card_icons.get(name)} for name in top_deck
        ]

        results.append({
            "archetype": archetype,
            "games": total,
            "wins": record["wins"],
            "losses": record["losses"],
            "unique_players": unique_players,
            "win_rate": round(win_rate * 100, 1),
            "example_deck": example_deck,
            "example_deck_count": top_deck_count,
        })

    results.sort(key=lambda r: r["win_rate"], reverse=True)
    return results

def print_archetype_report(archetype_stats: list, top_n: int = 15):
    print(f"\nTop {top_n} archetypes by live win rate:\n")
    for i, entry in enumerate(archetype_stats[:top_n], start=1):
        print(f"{i}. {entry['archetype']} — {entry['win_rate']}% win rate "
              f"({entry['wins']}W-{entry['losses']}L, {entry['games']} games, "
              f"{entry['unique_players']} unique players)")
        print(f"   Example deck: {', '.join(entry['example_deck'])} "
              f"(seen {entry['example_deck_count']}x)")


if __name__ == "__main__":
    my_tag = "#YUP02GRQG"

    print("Fetching live meta data...")
    battles = collect_live_battles(max_players=60, max_rounds=2, delay_seconds=0.1)
    meta_stats = compute_archetype_winrates(battles, min_games=5, min_unique_players=2)
    print_archetype_report(meta_stats, top_n=15)

    print(f"\nFetching your personal battle history ({my_tag})...")
    personal_stats = compute_personal_archetype_stats(my_tag)

    blended = blend_scores(personal_stats, meta_stats)
    print_recommendations(blended, top_n=5)