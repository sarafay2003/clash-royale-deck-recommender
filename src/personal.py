"""
Personal recommendation layer: combines a specific player's own
battle history with the live meta data to produce a personalized
deck/archetype recommendation.
"""
from collections import defaultdict

from src.api_client import get_battlelog
from src.archetypes import get_archetypes


def compute_personal_archetype_stats(player_tag: str) -> dict:
    """
    Pull a player's own recent battles and compute their personal
    win rate per archetype they've played. A deck with multiple win
    conditions contributes to each archetype it contains. Returns a
    dict keyed by archetype name.
    """
    battles = get_battlelog(player_tag)
    tag_clean = player_tag.strip("#").upper()

    stats = defaultdict(lambda: {"wins": 0, "losses": 0})

    for battle in battles:
        me = next(
            (p for p in battle.get("team", []) if p["tag"].strip("#").upper() == tag_clean),
            None,
        )
        if me is None:
            continue

        trophy_change = me.get("trophyChange")
        if trophy_change is None:
            continue  # not a ladder match

        for archetype in get_archetypes(me["cards"]):
            if trophy_change > 0:
                stats[archetype]["wins"] += 1
            else:
                stats[archetype]["losses"] += 1

    results = {}
    for archetype, record in stats.items():
        total = record["wins"] + record["losses"]
        results[archetype] = {
            "games": total,
            "wins": record["wins"],
            "losses": record["losses"],
            "win_rate": round(record["wins"] / total * 100, 1) if total else 0,
        }
    return results


def blend_scores(personal_stats: dict, meta_stats: list, min_personal_games: int = 3) -> list:
    """
    Combine personal archetype win rates with the live meta win rates.
    Uses a simple shrinkage approach: if a player has few games with an
    archetype, their personal win rate is unreliable, so we lean more
    on the meta average. If they have a solid sample, we trust their
    personal result more. Also carries through an example buildable
    deck for each archetype when available from the meta data.
    """
    meta_lookup = {entry["archetype"]: entry for entry in meta_stats}
    results = []

    all_archetypes = set(personal_stats.keys()) | set(meta_lookup.keys())

    for archetype in all_archetypes:
        personal = personal_stats.get(archetype, {"games": 0, "win_rate": 0})
        meta = meta_lookup.get(archetype)

        meta_win_rate = meta["win_rate"] if meta else None
        personal_games = personal["games"]
        personal_win_rate = personal["win_rate"]

        if personal_games >= min_personal_games and meta_win_rate is not None:
            weight = min(personal_games / 20, 0.7)
            blended = weight * personal_win_rate + (1 - weight) * meta_win_rate
            reason = f"your {personal_win_rate}% win rate + {meta_win_rate}% current meta strength"
        elif meta_win_rate is not None:
            blended = meta_win_rate
            reason = f"currently strong in the meta ({meta_win_rate}%), you haven't played it much yet"
        else:
            blended = personal_win_rate
            reason = f"your personal {personal_win_rate}% win rate (not enough current meta data)"

        results.append({
            "archetype": archetype,
            "score": round(blended, 1),
            "personal_games": personal_games,
            "reason": reason,
            "example_deck": meta["example_deck"] if meta else None,
            "example_deck_count": meta["example_deck_count"] if meta else None,
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def print_recommendations(blended: list, top_n: int = 5):
    print(f"\nTop {top_n} recommended archetypes for you:\n")
    for i, entry in enumerate(blended[:top_n], start=1):
        print(f"{i}. {entry['archetype']} — score {entry['score']}%")
        print(f"   ({entry['reason']})")
        if entry.get("example_deck"):
            print(f"   Example deck: {', '.join(entry['example_deck'])}")
        print()