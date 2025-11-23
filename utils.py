# utils.py
BASE_URL = "https://api.themoviedb.org/3"

IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

def get_original_language(lang: str) -> str:
    """Return valid TMDB original language filter."""
    lang_map = {
        "en": "en",
        "hi": "hi"
    }
    return lang_map.get(lang, "en")   # default English


def add_poster_url(movie: dict) -> dict:
    """Attach full poster URL if available."""
    poster_path = movie.get("poster_path")
    movie["poster_url"] = f"{IMAGE_BASE_URL}{poster_path}" if poster_path else None
    return movie
