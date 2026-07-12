import ollama
from journal.config import CHAT_MODEL, EMBED_MODEL


def health_check() -> bool:
    """Check if Ollama is running and models are available."""
    try:
        models = ollama.list()
        names = [m.model for m in models.models]
        has_chat = any(CHAT_MODEL in n for n in names)
        has_embed = any(EMBED_MODEL in n for n in names)
        return has_chat and has_embed
    except Exception:
        return False


def chat(messages: list[dict], model: str = CHAT_MODEL, options: dict | None = None) -> str:
    """Send messages and return the full response text."""
    kwargs = {"model": model, "messages": messages}
    if options:
        kwargs["options"] = options
    response = ollama.chat(**kwargs)
    return response.message.content


def chat_stream(messages: list[dict], model: str = CHAT_MODEL, options: dict | None = None):
    """Stream chat response, yielding content chunks."""
    kwargs = {"model": model, "messages": messages, "stream": True}
    if options:
        kwargs["options"] = options
    for chunk in ollama.chat(**kwargs):
        text = chunk.message.content
        if text:
            yield text


def embed(text: str) -> list[float]:
    """Generate embedding for a text string."""
    response = ollama.embed(model=EMBED_MODEL, input=text)
    return response.embeddings[0]
