import json
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from journal.config import STATIC_DIR, DATA_DIR
from journal import db, embeddings, brain_dump, search
from journal.llm import health_check

app = FastAPI(title="Local LLM Journal")

# In-memory session store for active brain dump conversations
_sessions: dict[str, dict] = {}

# Active UI version directory.
_ui_version = os.getenv("JOURNAL_UI_VERSION", "v2.0")
_ui_dir = STATIC_DIR / _ui_version
if not _ui_dir.exists():
    fallback_dir = STATIC_DIR / "v1.0"
    _ui_dir = fallback_dir if fallback_dir.exists() else STATIC_DIR


@app.on_event("startup")
def startup():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db.init_db()


# --- Static files ---
app.mount("/static", StaticFiles(directory=str(_ui_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    return (_ui_dir / "index.html").read_text()


# --- Health ---
@app.get("/api/health")
async def api_health():
    ok = health_check()
    return {"status": "ok" if ok else "error", "ollama_ready": ok}


# --- Brain Dump ---
@app.post("/api/braindump/start")
async def braindump_start(request: Request):
    body = await request.json()
    raw_dump = body.get("raw_dump", "")
    session_id = body.get("session_id", "default")

    messages, stream = brain_dump.start_session(raw_dump)

    # Collect the streamed response to store in messages
    collected = []

    def event_stream():
        for chunk in stream:
            collected.append(chunk)
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        # After streaming completes, store assistant message
        full_response = "".join(collected)
        messages.append({"role": "assistant", "content": full_response})
        _sessions[session_id] = {"messages": messages, "raw_dump": raw_dump}
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/braindump/reply")
async def braindump_reply(request: Request):
    body = await request.json()
    user_reply = body.get("reply", "")
    session_id = body.get("session_id", "default")

    session = _sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    messages, stream = brain_dump.continue_session(session["messages"], user_reply)

    collected = []

    def event_stream():
        for chunk in stream:
            collected.append(chunk)
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        full_response = "".join(collected)
        messages.append({"role": "assistant", "content": full_response})
        turn_count = sum(1 for m in messages if m["role"] == "user") - 1  # exclude initial dump
        yield f"data: {json.dumps({'done': True, 'turn_count': turn_count})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/braindump/polish")
async def braindump_polish(request: Request):
    body = await request.json()
    session_id = body.get("session_id", "default")

    session = _sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    stream = brain_dump.polish_entry(session["messages"])

    def event_stream():
        for chunk in stream:
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# --- Entries ---
@app.post("/api/entries")
async def save_entry(request: Request):
    body = await request.json()
    session_id = body.get("session_id", "default")
    polished_text = body.get("polished_text", "")

    session = _sessions.get(session_id)
    raw_dump = session["raw_dump"] if session else ""
    conversation = session["messages"] if session else []

    parsed = brain_dump.parse_polished_entry(polished_text)

    # Allow user overrides
    title = body.get("title", parsed["title"])
    mood = body.get("mood", parsed["mood"])
    tags = body.get("tags", parsed["tags"])
    entry_body = body.get("body", parsed["body"])

    entry_id = db.save_entry(
        title=title,
        body=entry_body,
        raw_dump=raw_dump,
        mood=mood,
        tags=tags,
        conversation=conversation,
    )

    # Store embedding
    embeddings.store_entry(
        entry_id=entry_id,
        text=f"{title}\n\n{entry_body}",
        metadata={"title": title, "mood": mood, "tags": tags,
                  "created_at": db.get_entry(entry_id)["created_at"]},
    )

    # Clean up session
    _sessions.pop(session_id, None)

    return {"id": entry_id, "title": title}


@app.get("/api/entries")
async def list_entries():
    return db.get_entries()


@app.get("/api/entries/{entry_id}")
async def get_entry(entry_id: int):
    entry = db.get_entry(entry_id)
    if not entry:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return entry


@app.delete("/api/entries/{entry_id}")
async def delete_entry(entry_id: int):
    deleted = db.delete_entry(entry_id)
    if not deleted:
        return JSONResponse({"error": "Not found"}, status_code=404)
    embeddings.delete_entry(entry_id)
    return {"deleted": True}


# --- Search ---
@app.post("/api/search")
async def api_search(request: Request):
    body = await request.json()
    query = body.get("query", "")

    results, stream = search.semantic_search(query)

    def event_stream():
        # Send matching entry metadata first
        yield f"data: {json.dumps({'results': [{'id': r['id'], 'title': r['metadata'].get('title', ''), 'date': r['metadata'].get('created_at', '')} for r in results]})}\n\n"
        for chunk in stream:
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
