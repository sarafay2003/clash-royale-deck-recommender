"""
Archetype classification: groups decks by their win condition card(s)
instead of requiring an exact 8-card match. Much more data-dense than
exact matching, since dozens of decks share the same win condition.
"""

# Cards that typically define a deck's archetype/identity.
# Not exhaustive, but covers the vast majority of common win conditions.
WIN_CONDITIONS = {
    "Hog Rider", "Royal Giant", "Giant", "Golem", "Lava Hound",
    "Graveyard", "X-Bow", "Mortar", "Balloon", "Miner",
    "Royal Hogs", "Ram Rider", "Goblin Barrel", "Wall Breakers",
    "Electro Giant", "Goblin Giant", "Elixir Golem", "Battle Ram",
    "Goblin Drill", "Three Musketeers", "Skeleton Barrel",
}


def get_archetype(cards: list) -> str:
    """
    Given a deck's card list, return an archetype label based on which
    win condition(s) it contains. If multiple win conditions are found,
    join them (e.g. "Golem + Lava Hound"). If none are found, label it
    "Other" - some decks are pure spell-bait/control without a single
    clear win condition, or use one we haven't listed.
    """
    names = {c["name"] for c in cards}
    found = sorted(names & WIN_CONDITIONS)
    if not found:
        return "Other"
    return " + ".join(found)

