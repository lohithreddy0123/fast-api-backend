from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from models import Base, VoteOption
from database import engine, SessionLocal
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for all origins (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# Create tables and seed options on startup
@app.on_event("startup")
async def initialize_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        default_options = ["Option A", "Option B", "Option C"]
        for title in default_options:
            existing = await session.execute(select(VoteOption).where(VoteOption.title == title))
            if not existing.scalar():
                session.add(VoteOption(title=title))
        await session.commit()

# Dependency to get DB session
async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

# Get all vote options
@app.get("/api/votes/")
async def get_votes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VoteOption))
    return [
        {
            "id": opt.id,
            "title": opt.title,
            "votes": opt.votes
        }
        for opt in result.scalars()
    ]

# Cast a vote
@app.post("/api/votes/cast/")
async def cast_vote(data: dict, db: AsyncSession = Depends(get_db)):
    name = data.get("name")
    vote_id = data.get("id")

    if not name or not vote_id:
        raise HTTPException(status_code=400, detail="Name and vote ID are required.")

    result = await db.execute(select(VoteOption).where(VoteOption.id == vote_id))
    option = result.scalar_one_or_none()

    if not option:
        raise HTTPException(status_code=400, detail="Invalid vote ID.")

    option.votes += 1
    await db.commit()
    await db.refresh(option)

    return {
        "id": option.id,
        "title": option.title,
        "votes": option.votes
    }
