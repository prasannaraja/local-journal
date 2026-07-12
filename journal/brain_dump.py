import re

from journal.config import PROMPTS_DIR
from journal.llm import chat, chat_stream


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

    # Pass 1: extract a faithful detail map so the final pass misses fewer specifics.
    extraction_messages = [
        {
            "role": "system",
            "content": (
                "Extract a faithful detail map from the conversation. "
                "Do not summarize away specifics. "
                "Return plain text with these sections: "
                "Timeline, Emotions, Motivations, Decisions, Unresolved Questions, Exact User Phrases. "
                "Only include facts present in the conversation."
            ),
        },
        {
            "role": "user",
            "content": f"Conversation:\n\n{conversation_text}",
        },
    ]
    detail_map = chat(extraction_messages, options={"num_ctx": 8192})

    polish_messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"Here is the conversation:\n\n{conversation_text}\n\n"
                f"Here is a faithful detail map extracted from it:\n\n{detail_map}\n\n"
                "Please write the polished journal entry."
            ),
        },
    ]
    return chat_stream(polish_messages, options={"num_ctx": 8192})


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
