from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database import create_db_and_tables
from .routes import users, auth, bookings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_db_and_tables()
    yield


app = FastAPI(
    title="PYTHON ASSESSMENT",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(bookings.router)
