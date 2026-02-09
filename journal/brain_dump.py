import re

from journal.config import PROMPTS_DIR
from journal.llm import chat_stream


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()


def start_session(raw_dump: str) -> tuple[list[dict], ...]:
    """Start a brain dump dialogue. Returns (messages, stream_generator)."""
    system = _load_prompt("braindump_system.txt")
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Here's my brain dump:\n\n{raw_dump}"},
    ]
    return messages, chat_stream(messages)


def continue_session(messages: list[dict], user_reply: str):
    """Add user reply, return updated messages and stream generator."""
    messages.append({"role": "user", "content": user_reply})
    return messages, chat_stream(messages)


def polish_entry(messages: list[dict]):
    """Generate a polished journal entry from the conversation. Returns stream generator."""
    system = _load_prompt("polish_system.txt")

    conversation_text = ""
    for msg in messages:
        if msg["role"] == "user":
            conversation_text += f"User: {msg['content']}\n\n"
        elif msg["role"] == "assistant":
            conversation_text += f"Companion: {msg['content']}\n\n"

    polish_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Here is the conversation:\n\n{conversation_text}\n\nPlease write the polished journal entry."},
    ]
    return chat_stream(polish_messages)


def parse_polished_entry(text: str) -> dict:
    """Parse the polished entry text to extract body, title, mood, tags."""
    title_match = re.search(r"TITLE:\s*(.+)", text)
    mood_match = re.search(r"MOOD:\s*(.+)", text)
    tags_match = re.search(r"TAGS:\s*(.+)", text)

    title = title_match.group(1).strip() if title_match else "Untitled"
    mood = mood_match.group(1).strip().lower() if mood_match else ""
    tags = tags_match.group(1).strip() if tags_match else ""

    # Remove metadata lines from body
    body = text
    for pattern in [r"\n*TITLE:.*", r"\n*MOOD:.*", r"\n*TAGS:.*"]:
        body = re.sub(pattern, "", body)
    body = body.strip()

    return {"title": title, "mood": mood, "tags": tags, "body": body}
