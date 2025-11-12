# ChatWithYourData_Bot

Interactive Panel dashboard that builds a local document vector DB from a PDF, performs retrieval using embeddings, and provides a conversational UI backed by OpenAI.

This project exposes a `src/chat_with_data.py` script (the main app). The script:
- Loads a PDF (or uploaded file),
- Splits text into chunks with `RecursiveCharacterTextSplitter`,
- Creates embeddings via `OpenAIEmbeddings`,
- Builds an in-memory DocArray vector store (`DocArrayInMemorySearch`),
- Performs retrieval and calls OpenAI ChatCompletion API to answer queries,
- Exposes a Panel UI for conversation, DB inspection, and file upload.

----------------

## File layout (expected)

ChatWithYourData_Bot/
├── src/
│ └── chat_with_data.py # main Panel app script
├── docs/
│ └── learning-and-teaching-prompt-templates.pdf # example PDF
├── .env # (not committed) OPENAI_API_KEY=sk-...
├── requirements.txt
├── .gitignore
└── README.md

--------------

## Quick start (recommended)

1. Clone / copy this repo and `cd` into it:

git clone <your-repo-url>
cd ChatWithYourData_Bot

2. Create and activate a virtual environment:

macOS / Linux:

python -m venv .venv
source .venv/bin/activate


Windows (PowerShell):

python -m venv .venv
.\.venv\Scripts\Activate.ps1


3. Install dependencies:

python -m pip install -U pip
python -m pip install -r requirements.txt


4. Add your OpenAI API key in a .env file at the project root (do NOT commit .env):

OPENAI_API_KEY=sk-...

If .env is missing, the script will prompt you for the API key at runtime.

5. Put at least one PDF into docs/ (example used in the code: docs/learning-and-teaching-prompt-templates.pdf). Or use the UI file-upload widget after launching the app.

---------

A — Use Panel CLI (recommended while developing)
panel serve src/chat_with_data.py --show


This starts a local server (default http://localhost:5006) and opens your browser.

B — Run as a script (if script includes the __main__ snippet)
python src/chat_with_data.py


This will attempt to start the Panel server programmatically and open a browser tab.

---------

How it works (short)

load_db(file, chain_type, k) loads the PDF → splits → creates embeddings → builds DocArray index.

The QA callable retrieves top-k docs and calls OpenAI ChatCompletion to produce a concise answer.

Panel + Param build the UI (Conversation, Database info, Chat History, Configure).

----

Tips & troubleshooting

File not found: If you see ValueError: File path ... is not a valid file or url, ensure the PDF exists under the docs/ folder or update the default path in src/chat_with_data.py. The script resolves paths relative to the repo root (if implemented) — if not, use an absolute path.

Missing modules: If you see ModuleNotFoundError, make sure you installed dependencies into the same Python environment you run (use python -m pip install -r requirements.txt and python -c "import sys; print(sys.executable)" to check).

OpenAI auth error: Ensure .env contains OPENAI_API_KEY or be ready to paste it when prompted.

Large PDFs / production: DocArray in-memory is for quick local testing. For production, consider a persistent vector store (Chroma/Pinecone/Weaviate) and add rate-limiting, retries, and cost controls.