from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from models import Base, VoteOption
from database import engine, SessionLocal

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Initialize DB tables
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Optionally seed options
    async with SessionLocal() as session:
        options = ["Option A", "Option B", "Option C"]
        for title in options:
            result = await session.execute(select(VoteOption).where(VoteOption.title == title))
            if not result.scalar():
                session.add(VoteOption(title=title))
        await session.commit()

# Dependency
async def get_db():
    async with SessionLocal() as session:
        yield session

@app.get("/api/votes/")
async def get_votes(db: Session = Depends(get_db)):
    result = await db.execute(select(VoteOption))
    return [opt.__dict__ for opt in result.scalars()]

@app.post("/api/votes/cast/")
async def cast_vote(data: dict, db: Session = Depends(get_db)):
    name = data.get("name")
    vote_id = data.get("id")

    if not name or not vote_id:
        return {"detail": "Invalid data"}, 400

    result = await db.execute(select(VoteOption).where(VoteOption.id == vote_id))
    option = result.scalar_one_or_none()

    if option:
        option.votes += 1
        await db.commit()
        await db.refresh(option)
        return {
            "title": option.title,
            "votes": option.votes,
            "id": option.id
        }
    return {"detail": "Invalid vote ID"}, 400

