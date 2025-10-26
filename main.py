from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import movies, genres,recommendation

app= FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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