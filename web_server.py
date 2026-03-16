#!/usr/bin/env python3
"""FastAPI web server for ASS - serves the debate UI and streams events via SSE."""

import json
import threading
import uuid
from queue import Empty, Queue
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse

from config import DebateConfig
from debate_engine import DebateEngine

app = FastAPI(title="ASS - Argumentative System Service")

# Store active debates
active_debates: dict = {}


def _serialize_event(event: dict) -> dict:
    """Make an event JSON-serializable by converting non-serializable objects."""
    serialized = {}
    for key, value in event.items():
        if key == "votes":
            serialized[key] = [
                {"voter": v.voter, "rankings": v.rankings,
                 "reasoning": v.reasoning, "iteration": v.iteration}
                for v in value
            ] if value else None
        else:
            serialized[key] = value
    return serialized


def _run_debate_thread(debate_id: str, question: str, config: DebateConfig):
    """Run a debate in a background thread, pushing events to the queue."""
    queue = active_debates[debate_id]["queue"]
    try:
        engine = DebateEngine(config)
        for event in engine.run_debate(question):
            serialized = _serialize_event(event)
            queue.put(serialized)
        queue.put(None)  # Signal completion
    except Exception as e:
        queue.put({"type": "error", "message": str(e)})
        queue.put(None)


@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse("static/index.html")


@app.get("/api/debate/start")
async def start_debate(
    question: str = Query(..., min_length=1),
    classic_mode: bool = Query(False),
    max_iterations: int = Query(10, ge=1, le=50),
    consensus_threshold: float = Query(0.75, ge=0.0, le=1.0),
):
    """Start a new debate and return a debate ID for SSE streaming."""
    config = DebateConfig.from_env()
    config.classic_mode = classic_mode
    config.voting_enabled = not classic_mode
    config.max_iterations = max_iterations
    config.consensus_threshold = consensus_threshold
    config.save_enabled = False  # Don't save web debates by default

    debate_id = str(uuid.uuid4())
    active_debates[debate_id] = {"queue": Queue(), "question": question}

    thread = threading.Thread(
        target=_run_debate_thread, args=(debate_id, question, config), daemon=True
    )
    thread.start()

    return {"debate_id": debate_id}


@app.get("/api/debate/{debate_id}/stream")
async def stream_debate(debate_id: str):
    """Stream debate events via Server-Sent Events."""
    if debate_id not in active_debates:
        return HTMLResponse("Debate not found", status_code=404)

    def event_generator():
        queue = active_debates[debate_id]["queue"]
        while True:
            try:
                event = queue.get(timeout=120)  # 2 min timeout per event
                if event is None:
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    break
                yield f"data: {json.dumps(event)}\n\n"
            except Empty:
                # Send keepalive
                yield f": keepalive\n\n"

        # Cleanup
        if debate_id in active_debates:
            del active_debates[debate_id]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
