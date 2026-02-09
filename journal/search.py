from journal.embeddings import search_entries
from journal.llm import chat_stream


def semantic_search(query: str):
    """Search entries and synthesize an answer. Returns (results, stream_generator)."""
    results = search_entries(query, n_results=5)

    if not results:
        def empty_stream():
            yield "No journal entries found yet. Start writing some entries first!"
        return [], empty_stream()

    context = ""
    for r in results:
        meta = r["metadata"]
        context += f"--- Entry: \"{meta.get('title', 'Untitled')}\" ({meta.get('created_at', 'unknown date')}) ---\n"
        context += r["document"] + "\n\n"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant that answers questions about the user's journal entries. "
                "You have access to their past entries as context. "
                "Reference specific entries by title and date when relevant. "
                "Be thoughtful, concise, and insightful. Use markdown formatting."
            ),
        },
        {
            "role": "user",
            "content": f"Here are my relevant journal entries:\n\n{context}\n\nMy question: {query}",
        },
    ]

    return results, chat_stream(messages)
