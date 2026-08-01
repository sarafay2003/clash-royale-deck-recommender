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


def get_archetypes(cards: list) -> list:
    """
    Given a deck's card list, return ALL individual win conditions
    found (as a list), rather than one combined label. A deck with two
    win conditions contributes to both archetype buckets - e.g. a
    Goblin Barrel + Wall Breakers deck counts toward both "Goblin
    Barrel" stats and "Wall Breakers" stats.
    """
    names = {c["name"] for c in cards}
    found = sorted(names & WIN_CONDITIONS)
    return found if found else ["Other"]