# Local LLM Journal

A personal journaling app powered by a local LLM. Write a brain dump, have an AI-guided conversation to clarify your thoughts, and get a polished journal entry — all running locally on your machine. No cloud, no API keys, your data stays yours.

## Features

**Brain Dump to Polished Entry**
1. Write your raw, unfiltered thoughts
2. An LLM asks gentle clarifying questions to help you reflect
3. When you're done chatting, it generates a polished journal entry
4. Review, edit, and save

**Semantic Search**
- Ask natural language questions about your past entries (e.g. "what have I learned about patience?")
- The app retrieves relevant entries and synthesizes an answer with references

**Browse & Manage**
- View all entries with mood tags and dates
- Expand any entry to read the full text
- Delete entries you no longer want

## Tech Stack

- **Backend:** Python + FastAPI
- **Frontend:** Vanilla HTML/CSS/JS (no build tools)
- **LLM:** Ollama (llama3.2:3b for chat, nomic-embed-text for embeddings)
- **Storage:** SQLite + ChromaDB
- **Environment:** Conda

## Quick Start

### Prerequisites

- [Ollama](https://ollama.com) installed and running
- [Miniforge](https://github.com/conda-forge/miniforge) or Conda

### Setup

```bash
# Clone the repo
git clone https://github.com/superS007/localllmjournal.git
cd localllmjournal

# Create the conda environment
conda env create -f environment.yml
conda activate llmjournal

# Pull the required models
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# Run the app
python -m journal.app
```

Open http://localhost:8000 in your browser.

## Run With Docker (Ollama Outside Container)

You can run this app in Docker while keeping Ollama on your host machine.

### Prerequisites

- Docker Desktop (or Docker Engine + Compose)
- Ollama running on host (`ollama serve`)
- Required models pulled on host:

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### Start with Compose

```bash
docker compose up --build -d
```

Open http://localhost:8000 in your browser.

### Stop

```bash
docker compose down
```

### Notes

- Container sets `OLLAMA_HOST=http://host.docker.internal:11434`.
- Journal data is persisted via `./data:/app/data`.
- If your Linux Docker setup cannot resolve `host.docker.internal`, replace it with your host IP and keep port `11434` reachable.

## How It Works

```
Brain Dump ──> LLM Dialogue ──> Polished Entry ──> SQLite + ChromaDB
                                                         │
Search Query ──> Embed ──> ChromaDB Lookup ──> LLM Synthesis ──> Answer
```

The app uses two Ollama models:
- **llama3.2:3b** — a small, fast chat model that runs well on laptops (including M1 MacBook Air with 8GB RAM)
- **nomic-embed-text** — generates embeddings for semantic search

All data is stored locally in the `data/` directory (SQLite database + ChromaDB vector store).

## Project Structure

```
localllmjournal/
├── environment.yml          # Conda environment
├── journal/
│   ├── app.py               # FastAPI routes + SSE streaming
│   ├── config.py            # Constants and paths
│   ├── db.py                # SQLite CRUD
│   ├── llm.py               # Ollama wrappers
│   ├── brain_dump.py        # Dialogue + polishing logic
│   ├── search.py            # Semantic search pipeline
│   ├── embeddings.py        # ChromaDB integration
│   └── static/              # Frontend (HTML/CSS/JS)
├── prompts/                 # System prompts for the LLM
└── data/                    # Runtime data (gitignored)
```

## License

MIT
