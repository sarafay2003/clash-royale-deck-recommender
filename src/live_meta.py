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

                # Pull opponent tags out of this player's battles for
                # the next round.
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


def compute_deck_winrates(battles: list, min_games: int = 8, min_unique_players: int = 4) -> list:
    """
    Given a flat list of battles, compute win rate per exact deck.
    Requires both a minimum game count AND a minimum number of unique
    players using that deck - otherwise a single skilled player's
    win streak can masquerade as a "strong deck".
    """
    stats = defaultdict(lambda: {"wins": 0, "losses": 0, "players": set()})

    for battle in battles:
        for player in battle.get("team", []):
            trophy_change = player.get("trophyChange")
            if trophy_change is None:
                continue

            deck = _deck_key(player["cards"])
            stats[deck]["players"].add(player["tag"])
            if trophy_change > 0:
                stats[deck]["wins"] += 1
            else:
                stats[deck]["losses"] += 1

    results = []
    for deck, record in stats.items():
        total = record["wins"] + record["losses"]
        unique_players = len(record["players"])
        if total < min_games or unique_players < min_unique_players:
            continue
        win_rate = record["wins"] / total
        results.append({
            "deck": sorted(deck),
            "games": total,
            "wins": record["wins"],
            "losses": record["losses"],
            "unique_players": unique_players,
            "win_rate": round(win_rate * 100, 1),
        })

    results.sort(key=lambda r: r["win_rate"], reverse=True)
    return results

def print_meta_report(deck_stats: list, top_n: int = 10):
    print(f"\nTop {top_n} decks by live win rate (min games + min unique players applied):\n")
    for i, entry in enumerate(deck_stats[:top_n], start=1):
        deck_str = ", ".join(entry["deck"])
        print(f"{i}. {entry['win_rate']}% win rate "
              f"({entry['wins']}W-{entry['losses']}L, {entry['games']} games, "
              f"{entry['unique_players']} unique players)")
        print(f"   {deck_str}\n")


if __name__ == "__main__":
    print("Fetching live battle data via clan seed + opponent snowballing...")
    battles = collect_live_battles(max_players=300, max_rounds=4)

    deck_stats = compute_deck_winrates(battles, min_games=8)
    print_meta_report(deck_stats, top_n=10)