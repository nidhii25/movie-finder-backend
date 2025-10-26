from pydantic import BaseModel

class recomm_ques(BaseModel):
    genre: str
    min_ratings: float
    fav_movie: str

