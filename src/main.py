"""
FastAPI service exposing the deck recommender as an HTTP endpoint.

Run with: uvicorn src.main:app --reload
Then visit http://127.0.0.1:8000/docs for interactive API docs.
"""
from fastapi import FastAPI, HTTPException

from src.live_meta import collect_live_battles, compute_archetype_winrates
from src.personal import compute_personal_archetype_stats, blend_scores
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


app = FastAPI(title="Clash Royale Deck Recommender")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/app")
def serve_frontend():
    return FileResponse("static/index.html")

# Cache the meta result in memory so we don't re-fetch 300 players on
# every single request - refreshed only when explicitly requested.
_meta_cache = {"stats": None}


def _get_meta_stats(force_refresh: bool = False):
    if _meta_cache["stats"] is None or force_refresh:
        battles = collect_live_battles(max_players=150, max_rounds=3)
        _meta_cache["stats"] = compute_archetype_winrates(
            battles, min_games=8, min_unique_players=3
        )
    return _meta_cache["stats"]


@app.get("/")
def root():
    return {"message": "Clash Royale Deck Recommender API - see /docs for usage"}


@app.get("/recommend/{player_tag}")
def recommend(player_tag: str, refresh_meta: bool = False):
    """
    Get personalized archetype recommendations for a player.
    - player_tag: the player's tag, with or without '#' (e.g. YUP02GRQG or #YUP02GRQG)
    - refresh_meta: set true to force a fresh meta pull instead of using the cache
    """
    tag = player_tag if player_tag.startswith("#") else f"#{player_tag}"

    try:
        personal_stats = compute_personal_archetype_stats(tag)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not fetch player data: {e}")

    if not personal_stats:
        raise HTTPException(
            status_code=404,
            detail="No recent ladder battles found for this player tag."
        )

    meta_stats = _get_meta_stats(force_refresh=refresh_meta)
    blended = blend_scores(personal_stats, meta_stats)

    return {
        "player_tag": tag,
        "recommendations": blended[:5],
    }