from fastapi import FastAPI
from database import init_db
from routes import router

app = FastAPI(
    title="Writers LLM Backend",
    description="A FastAPI backend for book authors' text autocomplete functionality",
    version="1.0.0"
)

@app.on_event("startup")
async def startup():
    init_db()

app.include_router(router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to Writers LLM Backend",
        "version": "1.0.0"
    } 