# Clash Royale Deck Recommender

A personalized deck recommendation API for Clash Royale. Instead of showing a
generic "best deck" tier list, it looks at **your own battle history** and
**live, freshly-fetched meta data** from real recent matches, and recommends
which archetype you should actually be playing right now — with a plain-English
reason for each suggestion and an actual buildable example deck with card art.

![Screenshot](docs/screenshot.png)

## The problem it solves

Players currently decide what deck to use one of two ways: copy whatever a
YouTuber calls "meta" (even if it doesn't suit their playstyle or card levels),
or stick with a deck out of habit even after it's gone stale post-balance-patch.
Both are guesswork.

This tool answers: **"Given how I personally play, and what's actually strong
in the game right now, what's my best deck?"**

## How it works

1. User provides their public player tag through the web interface.
2. **Live meta collection**: starting from a seed clan's members, the system
   snowballs outward — every opponent seen in a battle becomes a new player to
   query next — building a live sample of hundreds of recent matches, fetched
   fresh from the official Clash Royale API every time (no stored dataset).
3. **Archetype grouping**: decks are grouped by win condition (e.g. Hog Rider,
   Balloon, Golem) rather than matched exactly, since exact 8-card matches are
   too sparse to get reliable win-rate data from at this sample size.
4. **Reliability filtering**: an archetype's win rate only counts if it's
   backed by enough total games *and* enough different players.
5. **Personal blending**: the user's own recent battles are scored the same
   way and blended with the live meta win rate, weighted toward personal data
   as their sample size grows.
6. The API returns ranked archetypes, each with a plain-English reason, an
   actual example deck (with card art) that real players used, and a warning
   when that example deck's sample size is thin.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical reasoning behind
each design decision.

## ⏳ A note on response time

Because this pulls **live data on every request** rather than reading from a
pre-built dataset, the first call to `/recommend/{player_tag}` can take
**1-2 minutes** - it's actively fetching and aggregating battle data from
~150 real players in the background. A simple in-memory cache means the live
meta data is reused for subsequent requests until the server restarts or a
refresh is explicitly requested.

## Known limitations

- **Modest sample size**: live meta data comes from ~150-300 players per
  fetch, snowballed from one seed clan. This is enough for archetype-level
  signal but not a fully representative sample of the entire player base.
- **Archetype list isn't exhaustive**: win conditions are matched against a
  manually curated list (`src/archetypes.py`). Uncommon or new cards may fall
  into the generic "Other" bucket instead of their own archetype.
- **Single example deck per archetype**: currently shows the single most
  common exact deck within an archetype, not multiple build options.
- **First request is slow by design**: live data means no instant answer on
  a cold cache - this is a deliberate tradeoff, not a bug.
- **Cache doesn't expire automatically**: the meta cache only refreshes on
  server restart or when `refresh_meta=true` is explicitly passed.

## Project status

Core pipeline is built and working end-to-end: live meta collection,
archetype-based aggregation, personal + meta blending, and a full web
interface with card art and usage guidance.

## Roadmap

- [x] Supercell API access + basic API client (player profile, battle log, clan members)
- [x] Live meta data collection via clan-seed + opponent snowballing
- [x] Archetype-level grouping (win-condition based) to solve exact-deck sparsity
- [x] Reliability filtering (minimum games + minimum unique players per archetype)
- [x] Personal battle history scoring per archetype
- [x] Blended personal + meta scoring with shrinkage
- [x] FastAPI service exposing recommendations by player tag
- [x] Frontend with card images, player identity, loading feedback, cancel button
- [x] Low-sample-size warning on example decks
- [ ] Multiple example decks per archetype instead of one
- [ ] Time-based meta cache refresh instead of manual-only
- [ ] Clean up unused/legacy code as the project evolves

## Tech stack

- Python, `requests` - API client
- FastAPI, `uvicorn` - serving recommendations over HTTP
- Vanilla HTML/CSS/JS - frontend
- Official Clash Royale API (developer.clashroyale.com)

## Setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # then add your Supercell API key (IP-restricted)
```

## Running

```bash
uvicorn src.main:app --reload
```

Then visit `http://127.0.0.1:8000/app` for the web interface, or
`http://127.0.0.1:8000/docs` for interactive API docs.

## Repository structure

```
clash-royale-deck-recommender/
├── src/
│   ├── config.py           # API key + base URL setup
│   ├── api_client.py       # Supercell API wrapper (player, battlelog, clan members)
│   ├── archetypes.py       # Win-condition based archetype classification
│   ├── live_meta.py        # Live meta collection (clan-seed + snowball) + aggregation
│   ├── personal.py         # Personal battle stats + personal/meta blending
│   └── main.py              # FastAPI service
├── static/
│   └── index.html          # Frontend
├── docs/
│   └── screenshot.png
├── notebooks/               # (reserved for future EDA)
├── tests/
├── requirements.txt
└── .env.example
```