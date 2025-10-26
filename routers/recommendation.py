import httpx
from fastapi import APIRouter, HTTPException
from models import recomm_ques
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

GENRE_MAP = {
    "Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35, "Crime": 80,
    "Documentary": 99, "Drama": 18, "Family": 10751, "Fantasy": 14, "Horror": 27,
    "Romance": 10749, "Science Fiction": 878, "Thriller": 53
}

router = APIRouter()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"


async def tmdb_get(url, params=None, retries=3, backoff=2):
    """Centralized TMDB request with retry + exponential backoff"""
    params = params or {}
    params["api_key"] = TMDB_API_KEY

    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url, params=params)
                r.raise_for_status()
                return r.json()
        except httpx.RequestError:
            wait = backoff ** attempt
            await asyncio.sleep(wait)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Movie not found")
            wait = backoff ** attempt
            await asyncio.sleep(wait)

    raise HTTPException(status_code=502, detail=f"TMDB request failed after {retries} attempts")


def add_poster_url(movie):
    if movie.get("poster_path"):
        movie["poster_url"] = IMAGE_BASE_URL + movie["poster_path"]
    else:
        movie["poster_url"] = None
    return movie


@router.post("/recommendations")
async def get_choice(ques: recomm_ques):
    genre_id = GENRE_MAP.get(ques.genre)
    if not genre_id:
        raise HTTPException(status_code=400, detail="Invalid genre provided")

    # Step 1: Search favorite movie
    fav_data = await tmdb_get(f"{BASE_URL}/search/movie", params={"query": ques.fav_movie})
    fav_results = fav_data.get("results")
    if not fav_results:
        raise HTTPException(status_code=404, detail="Favorite movie not found")
    fav_id = fav_results[0]["id"]

    # Step 2: Get keywords
    kw_data = await tmdb_get(f"{BASE_URL}/movie/{fav_id}/keywords")
    kw_ids = [str(kw["id"]) for kw in kw_data.get("keywords", [])]
    kw_query = ",".join(kw_ids) if kw_ids else ""

    all_movies = []

    # Discover with genre, rating, and keywords
    discover_params = {
        "with_genres": genre_id,
        "vote_average.gte": ques.min_ratings,
        "sort_by": "popularity.desc"
    }
    if kw_query:
        discover_params["with_keywords"] = kw_query
    all_movies += (await tmdb_get(f"{BASE_URL}/discover/movie", params=discover_params)).get("results", [])

    # TMDB recommendations
    all_movies += (await tmdb_get(f"{BASE_URL}/movie/{fav_id}/recommendations")).get("results", [])

    # Popular in genre fallback
    genre_params = {"with_genres": genre_id, "sort_by": "popularity.desc"}
    all_movies += (await tmdb_get(f"{BASE_URL}/discover/movie", params=genre_params)).get("results", [])

    # Exclude favorite and remove duplicates
    unique_movies = {m["id"]: m for m in all_movies if m["id"] != fav_id}.values()
    movies = list(unique_movies)[:10]

    if not movies:
        raise HTTPException(status_code=404, detail="No recommended movies found")

    return {"recommended_movies": [add_poster_url(m) for m in movies]}
