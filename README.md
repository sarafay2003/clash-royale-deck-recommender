# Clash Royale Deck Recommender

A personalized deck recommendation API for Clash Royale. Instead of showing a
generic "best deck" tier list, it looks at **your own battle history** and
**live, freshly-fetched meta data** from real recent matches, and recommends
which archetype you should actually be playing right now — with a plain-English
reason for each suggestion.

## The problem it solves

Players currently decide what deck to use one of two ways: copy whatever a
YouTuber calls "meta" (even if it doesn't suit their playstyle or card levels),
or stick with a deck out of habit even after it's gone stale post-balance-patch.
Both are guesswork.

This tool answers: **"Given how I personally play, and what's actually strong
in the game right now, what's my best deck?"**

## How it works

1. User provides only their public player tag (e.g. `#2Y8G9VVLC`) via the API.
2. **Live meta collection**: starting from a seed clan's members, the system
   snowballs outward — every opponent seen in a battle becomes a new player to
   query next — building a live sample of hundreds of recent matches, fetched
   fresh from the official Clash Royale API every time (no stored dataset).
3. **Archetype grouping**: instead of matching exact 8-card decks (which are
   too sparse to get reliable win-rate data from), decks are grouped by their
   win condition(s) - e.g. Hog Rider, Balloon, Golem. This solves the data
   sparsity problem and gives statistically meaningful sample sizes even from
   a few hundred players. A deck with two win conditions counts toward both
   archetypes.
4. **Filtering for reliability**: an archetype's win rate only counts if it's
   backed by enough total games *and* enough different players - otherwise one
   skilled player's win streak could masquerade as a "strong deck."
5. **Personal blending**: the user's own recent battles are pulled and scored
   per archetype the same way. Their personal win rate is blended with the
   live meta win rate using a weighting that favors personal data more as
   their sample size grows (shrinkage toward the meta average when personal
   data is sparse).
6. The API returns a ranked list of recommended archetypes, each with a
   plain-English reason (e.g. "your 58.8% win rate + 57.7% current meta
   strength", or "currently strong in the meta, you haven't played it much
   yet").

## ⏳ A note on response time

Because this pulls **live data on every request** rather than reading from a
pre-built dataset, the first call to `/recommend/{player_tag}` can take
**1-2 minutes** - it's actively fetching and aggregating battle data from
~150 real players in the background, not stuck or broken. A simple in-memory
cache means the live meta data is reused for subsequent requests until the
server restarts or a refresh is explicitly requested, so only the very first
call (or a forced refresh) pays this cost.

## Project status

Core pipeline is built and working end-to-end: live meta collection,
archetype-based aggregation, personal + meta blending, and a FastAPI service
exposing it over HTTP.

## Roadmap

- [x] Supercell API access + basic API client (player profile, battle log, clan members)
- [x] Live meta data collection via clan-seed + opponent snowballing
- [x] Archetype-level grouping (win-condition based) to solve exact-deck sparsity
- [x] Reliability filtering (minimum games + minimum unique players per archetype)
- [x] Personal battle history scoring per archetype
- [x] Blended personal + meta scoring with shrinkage
- [x] FastAPI service exposing recommendations by player tag
- [ ] Clean up unused/legacy exact-deck-matching code
- [ ] Simple frontend (basic form instead of raw JSON / API docs page)
- [ ] Smarter meta cache refresh (time-based instead of manual-only)

## Tech stack

- Python, `requests` - API client
- FastAPI, `uvicorn` - serving recommendations over HTTP
- Official Clash Royale API (developer.clashroyale.com)

## Setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # then add your Supercell API key (IP-restricted)
```

## Running the API

```bash
uvicorn src.main:app --reload
```

Then visit `http://127.0.0.1:8000/docs` for interactive API docs, or hit
`http://127.0.0.1:8000/recommend/{player_tag}` directly.

## Repository structure

```
clash-royale-deck-recommender/
├── src/
│   ├── config.py           # API key + base URL setup
│   ├── api_client.py        # Supercell API wrapper (player, battlelog, clan members)
│   ├── archetypes.py        # Win-condition based archetype classification
│   ├── live_meta.py         # Live meta collection (clan-seed + snowball) + aggregation
│   ├── personal.py          # Personal battle stats + personal/meta blending
│   └── main.py              # FastAPI service
├── notebooks/               # (reserved for future EDA)
├── data/                    # (unused - this project fetches live, nothing is stored)
├── tests/
├── requirements.txt
└── .env.example
```