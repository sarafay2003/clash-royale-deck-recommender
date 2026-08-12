# Architecture & Design Decisions

This document explains the reasoning behind the major technical choices in
this project - useful for anyone reviewing the code, and for future-me
remembering why things are built this way.

## Why live data instead of a stored dataset?

The original plan was to collect a dataset once and query it repeatedly.
That was rejected in favor of fetching fresh data on every request, because
"what's the best deck right now" is inherently about *current* state - a
dataset collected last week could already be stale after a balance patch.
The tradeoff is response time: live fetching takes 1-2 minutes on a cold
cache, versus instant reads from a stored file. That tradeoff was accepted
deliberately.

## Why archetype grouping instead of exact-deck matching?

Early versions matched exact 8-card decks. This failed in practice: there
are millions of possible 8-card combinations, so even a sample of 300 real
players produced almost no decks with enough repeat occurrences to trust a
win rate from. Grouping by win condition (Hog Rider, Balloon, Golem, etc.)
collapses dozens of similar decks into one bucket, producing statistically
meaningful sample sizes even from a modest number of players. This is
effectively a simple, rule-based clustering step.

A deck with two win conditions (e.g. Goblin Barrel + Wall Breakers) counts
toward *both* archetype buckets, not a separate combined label - this
reflects how players actually think about deck identity, and avoids
splintering data into overly specific combined categories.

## Why filter by both games AND unique players?

Early testing showed that some "100% win rate" decks were actually just one
highly skilled player winning consistently with their favorite deck - not
evidence the deck itself is strong. Requiring a minimum number of *different*
players, not just games, filters out this bias.

## Why clan-seeded snowball sampling instead of the rankings API?

The official `/locations/{id}/rankings/players` endpoint proved unreliable -
it returned empty results even for valid location IDs (both "global" and
country-specific brackets), likely due to Path of Legends ranking data not
being populated. Clan member lists (`/clans/{tag}/members`) proved reliable,
so that became the seed source instead. From there, every opponent
encountered in a battle log becomes a new player to query in the next round,
letting the sample grow organically beyond the original clan without
depending on the broken rankings endpoint.

## Why blend personal and meta scores with shrinkage instead of simple averaging?

A player's own win rate with an archetype they've only played 2-3 times is
statistically unreliable - a couple of lucky or unlucky games can swing it
wildly. The blending formula weights personal data more heavily as the
player's own sample size grows (capped at 70% influence), and falls back
almost entirely to the meta average when personal data is sparse. This is a
simple form of shrinkage estimation, a real technique used in recommender
systems to handle cold-start and small-sample problems.

## Why a single example deck per archetype (for now)?

Simpler to implement first and validates the concept. The most frequent
exact deck within an archetype is tracked and shown as a concrete, buildable
example - not a random draw. Showing multiple options is a natural next
step, tracked in the README roadmap.

## Known tradeoffs, stated plainly

- Live fetching means slower responses than a cached dataset would give.
- Sample sizes (hundreds of players) are modest compared to the full player
  base - good enough for directional signal, not a scientific-grade sample.
- The win-condition list in `archetypes.py` is manually curated and will
  need updates as new cards are released.