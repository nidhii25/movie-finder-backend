import httpx
from fastapi import APIRouter, Query, HTTPException
import os
from dotenv import load_dotenv
import asyncio
from utils import add_poster_url, BASE_URL, get_original_language

load_dotenv()
router = APIRouter()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")


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
                raise HTTPException(status_code=404, detail="Resource not found")
            wait = backoff ** attempt
            await asyncio.sleep(wait)

    raise HTTPException(status_code=500, detail=f"TMDB request failed after {retries} attempts")


# 🔹 Get all genres
@router.get("/genres")
async def get_genres():
    url = f"{BASE_URL}/genre/movie/list"
    data = await tmdb_get(url)
    return {"genres": data.get("genres", [])}


# 🔹 Get movies by genre
@router.get("/genres/{genre_id}/movies")
async def get_by_genre(genre_id: int, count: int = 15, page: int = 1, lang: str = "en"):
    original_lang = get_original_language(lang)

    url = f"{BASE_URL}/discover/movie"
    data = await tmdb_get(url, params={
        "with_genres": genre_id,
        "page": page,
        "with_original_language": original_lang
    })
    movies = data.get("results", [])[:count]
    return {"movies": [add_poster_url(m) for m in movies]}


# 🔹 Get movies by genre with sorting
@router.get("/genres/{genre_id}/movies/sort")
async def get_by_genre_sorted(
    genre_id: int,
    sort_by: str = Query(
        ...,
        description="Sort by: popularity.asc, popularity.desc, vote_average.asc, vote_average.desc, release_date.asc, release_date.desc"
    ),
    count: int = Query(15, ge=1, le=50),
    page: int = Query(1, ge=1),
    lang: str = "en"
):
    original_lang = get_original_language(lang)

    valid_sorts = [
        "popularity.asc", "popularity.desc",
        "vote_average.asc", "vote_average.desc",
        "release_date.asc", "release_date.desc"
    ]
    if sort_by not in valid_sorts:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by value. Must be one of: {valid_sorts}")

    url = f"{BASE_URL}/discover/movie"
    data = await tmdb_get(url, params={
        "with_genres": genre_id,
        "sort_by": sort_by,
        "page": page,
        "with_original_language": original_lang
    })

    movies = data.get("results", [])[:count]

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found for the specified genre")

    return [add_poster_url(m) for m in movies]
