# Architecture & Design Decisions

This document explains the reasoning behind the major technical choices in
this project, the exact flow of execution, and why each library was chosen -
useful for anyone reviewing the code, and for future-me remembering why
things are built this way.

## Execution flow: what actually happens on a request

When a user submits a player tag through the frontend, here's the exact
sequence of events, end to end:

1. **Frontend** (`static/index.html`) sends a `GET` request to
   `/recommend/{player_tag}`, with an `AbortController` attached so the
   request can be cancelled mid-flight if the user chooses.

2. **`main.py`** receives the request. It first calls `get_player(tag)` from
   `api_client.py` to fetch the player's profile (used to get their display
   name for the frontend).

3. **`main.py`** calls `compute_personal_archetype_stats(tag)`
   (`personal.py`), which:
   - Fetches the player's own recent battle log via `get_battlelog(tag)`
   - For each battle, identifies which of the two players in `team` is the
     user (by matching tag)
   - Classifies their deck into archetype(s) using `get_archetypes()`
     (`archetypes.py`)
   - Tallies wins/losses per archetype, returning a per-archetype win rate

4. **`main.py`** calls `_get_meta_stats()`, which checks an in-memory cache:
   - **If empty or a refresh was requested**: calls `collect_live_battles()`
     (`live_meta.py`), which:
     a. Fetches clan member tags via `get_clan_members()` as a starting seed
     b. Fetches each member's battle log
     c. Extracts every opponent tag seen in those battles
     d. Repeats for those newly discovered tags (the "snowball"), up to a
        configured number of rounds or a maximum player count
     e. Returns the full flat list of collected battles
   - Then calls `compute_archetype_winrates()` on that battle list, which:
     a. Groups every player-battle by archetype (a deck can belong to
        multiple archetypes if it has multiple win conditions)
     b. Tracks win/loss counts, unique player counts, and the most
        frequently seen exact 8-card deck per archetype
     c. Filters out archetypes with too few games or too few unique players
     d. Returns a sorted list of archetype stats, richest signal first

5. **`main.py`** calls `blend_scores(personal_stats, meta_stats)`
   (`personal.py`), which combines the two data sources per archetype using
   a shrinkage-weighted formula (see "Why blend with shrinkage" below), and
   returns a ranked list with a human-readable reason string per entry.

6. **`main.py`** returns the top 5 blended recommendations, plus the
   player's name and tag, as JSON.

7. **Frontend** renders each recommendation as a card: archetype name,
   score, reason, and the example deck's card art (fetched from the
   `iconUrls` already present in the Clash Royale API's card data - no
   separate image-fetching step is needed).

## Why each library was chosen

- **`requests`** - the standard, well-documented library for making HTTP
  calls to the Clash Royale API. No async needed here since calls are made
  sequentially with a deliberate delay between them (see rate-limiting
  note below), so the added complexity of `aiohttp` or similar wasn't
  justified.

- **`python-dotenv`** - loads the API key from a local `.env` file into
  environment variables, keeping the real key out of source control while
  still making it easy to access via `os.getenv()`.

- **`fastapi`** - chosen over Flask for three concrete reasons: automatic
  interactive API docs at `/docs` (useful for testing without building a
  frontend first), built-in request/response validation via type hints,
  and native `async def` support if the project later needs concurrent
  request fetching.

- **`uvicorn`** - the ASGI server FastAPI is built to run on; required to
  actually serve a FastAPI app.

- **No database** - deliberately omitted. Since the whole point of this
  project is live, always-current data rather than a stored dataset, there
  was nothing that needed persistent storage. The only "storage" is an
  in-memory dictionary (`_meta_cache`) that intentionally resets on server
  restart.

- **No pandas/numpy in the actual running system** - these are listed in
  `requirements.txt` from the original project plan (when a stored dataset
  and offline EDA were still the design), but the final live-aggregation
  approach only needed plain Python data structures (`dict`, `defaultdict`,
  `set`) for counting and grouping - genuinely faster to write and reason
  about for this scale of data, and one less dependency to explain. Worth
  removing from `requirements.txt` if not used elsewhere.

- **Vanilla HTML/CSS/JS frontend, no framework** - a single-page tool with
  one form and one result view doesn't need React/Vue's complexity. Plain
  JavaScript's `fetch` API and DOM manipulation are sufficient and keep the
  project understandable without a build step.

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

## Why blend personal and meta scores with shrinkage?

A player's own win rate with an archetype they've only played 2-3 times is
statistically unreliable - a couple of lucky or unlucky games can swing it
wildly. The blending formula weights personal data more heavily as the
player's own sample size grows (capped at 70% influence), and falls back
almost entirely to the meta average when personal data is sparse. This is a
simple form of shrinkage estimation, a real technique used in recommender
systems to handle cold-start and small-sample problems.

## Why a delay between API requests?

`collect_live_battles()` sleeps briefly (`delay_seconds`) between each
player's battle-log request. This avoids hitting the Clash Royale API's
rate limits during the snowball phase, which can involve dozens to hundreds
of sequential requests in one run.

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
- Requests are sequential, not concurrent - simpler code, but slower than it
  could be. A `ThreadPoolExecutor`-based rewrite would speed this up at the
  cost of added complexity.
