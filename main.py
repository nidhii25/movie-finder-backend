from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import movies, genres,recommendation

app= FastAPI()

origins = [
    "http://localhost:5173",  # React frontend local dev
    "https://movie-finder-n.vercel.app/"  # Production frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to the Movie Recommendation API"}

app.include_router(movies.router)
app.include_router(genres.router)
app.include_router(recommendation.router)