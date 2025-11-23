import httpx
from fastapi import APIRouter, HTTPException
import os
from dotenv import load_dotenv
import asyncio
from utils import get_original_language, add_poster_url, BASE_URL
from datetime import datetime
load_dotenv()

router = APIRouter()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")


async def tmdb_get(url, params=None, retries=3, backoff=2):
    """Centralized TMDB request with retry and exponential backoff"""
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

    raise HTTPException(status_code=500, detail=f"TMDB request failed after {retries} attempts")


# 🔹 Popular movies
@router.get("/movies")
async def get_movies(count: int = 10, page: int = 1, lang: str = "en"):
    original_lang = get_original_language(lang)

    url = f"{BASE_URL}/discover/movie"
    data = await tmdb_get(url, params={
        "sort_by": "popularity.desc",
        "page": page,
        "with_original_language": original_lang
    })

    movies = data.get("results", [])[:count]
    return {"movies": [add_poster_url(m) for m in movies]}


# 🔹 Movie details
@router.get("/movie/{movie_id}")
async def get_movie_details(movie_id: int):
    url = f"{BASE_URL}/movie/{movie_id}"
    movie = await tmdb_get(url)
    return add_poster_url(movie)


# 🔹 Trending movies
@router.get("/movies/trending")
async def get_trending_movies(count: int = 15, page: int = 1, lang: str = "en"):
    original_lang = get_original_language(lang)

    url = f"{BASE_URL}/discover/movie"
    data = await tmdb_get(url, params={
        "sort_by": "popularity.desc",
        "vote_count.gte": 50,      # trending-like filter
        "page": page,
        "with_original_language": original_lang
    })

    movies = data.get("results", [])[:count]
    return {"trending_movies": [add_poster_url(m) for m in movies]}


# 🔹 Top rated movies
@router.get("/movies/top_rated")
async def get_top_rated_movies(count: int = 15, page: int = 1, lang: str = "en"):
    original_lang = get_original_language(lang)

    url = f"{BASE_URL}/discover/movie"
    data = await tmdb_get(url, params={
        "sort_by": "vote_average.desc",
        "vote_count.gte": 100,     # ensures meaningful ratings
        "page": page,
        "with_original_language": original_lang
    })
    movies = data.get("results", [])[:count]
    return {"top_rated_movies": [add_poster_url(m) for m in movies]}


# 🔹 Upcoming movies
@router.get("/movies/upcoming")
async def get_upcoming_movies(count: int = 15, page: int = 1, lang: str = "en"):
    original_lang = get_original_language(lang)
    today = datetime.today().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/discover/movie"
    data = await tmdb_get(url, params={
        "sort_by": "release_date.asc",
        "release_date.gte": today,
        "page": page,
        "with_original_language": original_lang
    })
    movies = data.get("results", [])[:count]
    return {"upcoming_movies": [add_poster_url(m) for m in movies]}


# 🔹 Search movies
@router.get("/search")
async def search_movies(query: str, count: int = 10, page: int = 1, lang: str = "en"):
    original_lang = get_original_language(lang)

    movies = []

    # 🔹 Search by title
    title_url = f"{BASE_URL}/search/movie"
    title_data = await tmdb_get(title_url, params={
        "query": query,
        "page": page,
        "with_original_language": original_lang
    })
    movies += title_data.get("results", [])[:count]

    # 🔹 Search by keyword
    kw_url = f"{BASE_URL}/search/keyword"
    kw_data = await tmdb_get(kw_url, params={"query": query})
    if kw_data.get("results"):
        keyword_id = kw_data["results"][0]["id"]
        discover_url = f"{BASE_URL}/discover/movie"
        discover_data = await tmdb_get(discover_url, params={
            "with_keywords": keyword_id,
            "page": page,
            "with_original_language": original_lang
        })
        movies += discover_data.get("results", [])[:count]

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found for this search query")

    movies = {m['id']: m for m in movies}.values()

    return [add_poster_url(m) for m in movies]
