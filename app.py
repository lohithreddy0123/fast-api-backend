from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:5173"] for stricter config
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory data store
votes = {
    "Option A": 0,
    "Option B": 0,
    "Option C": 0,
}

connections = []

@app.get("/api/votes/")
def get_votes():
    return [{"title": k, "votes": v, "id": i + 1} for i, (k, v) in enumerate(votes.items())]

@app.post("/api/votes/cast/")
async def cast_vote(data: dict):
    name = data.get("name")
    vote_id = data.get("id")

    if not name or not vote_id:
        return JSONResponse(status_code=400, content={"detail": "Invalid data"})

    keys = list(votes.keys())
    if 0 < vote_id <= len(keys):
        selected = keys[vote_id - 1]
        votes[selected] += 1

        updated = {
            "title": selected,
            "votes": votes[selected],
            "id": vote_id
        }

        # Notify all clients via WebSocket
        for conn in connections:
            try:
                await conn.send_json({
                    "type": "update",
                    "payload": get_votes()
                })
            except:
                pass

        return updated

    return JSONResponse(status_code=400, content={"detail": "Invalid vote ID"})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.remove(websocket)
