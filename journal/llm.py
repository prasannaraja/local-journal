import ollama
from journal.config import CHAT_MODEL, EMBED_MODEL, OLLAMA_HOST


_client = ollama.Client(host=OLLAMA_HOST)


def health_check() -> bool:
    """Check if Ollama is running and models are available."""
    try:
        models = _client.list()
        names = [m.model for m in models.models]
        has_chat = any(CHAT_MODEL in n for n in names)
        has_embed = any(EMBED_MODEL in n for n in names)
        return has_chat and has_embed
    except Exception:
        return False


def chat(messages: list[dict], model: str = CHAT_MODEL) -> str:
    """Send messages and return the full response text."""
    response = _client.chat(model=model, messages=messages)
    return response.message.content


def chat_stream(messages: list[dict], model: str = CHAT_MODEL):
    """Stream chat response, yielding content chunks."""
    for chunk in _client.chat(model=model, messages=messages, stream=True):
        text = chunk.message.content
        if text:
            yield text


def embed(text: str) -> list[float]:
    """Generate embedding for a text string."""
    response = _client.embed(model=EMBED_MODEL, input=text)
    return response.embeddings[0]
