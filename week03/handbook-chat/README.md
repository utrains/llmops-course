# HR policy chatbot

This folder runs the Week 3 retrieval and generation pipeline through Streamlit.
It loads the approved policy folder, preserves policy sections, splits oversized
sections, stores metadata, retrieves the closest evidence, and asks Claude to
answer only from that evidence.

The request path is the same one made visible in Labs 1 and 2.

## Files in this folder

| File | What it is |
|------|------------|
| `app.py` | The Streamlit app. Read the comments in that file. |
| `../policies/` | The same HR policy collection used by the notebooks. |
| `requirements.txt` | Python packages for this app. |
| `env.example` | Copy this to `.env` and paste your keys. |
| `Dockerfile` / `docker-compose.yml` | Run the app in Docker. |

## Keys

This app uses its **own** `.env` in this folder, not the `.env` next to the notebooks.

1. Copy `env.example` to `.env`.
2. Paste `OPENAI_API_KEY` (embeddings) and `ANTHROPIC_API_KEY` (Claude).

```bash
cp env.example .env
```

Windows PowerShell:

```powershell
copy env.example .env
```

Never commit `.env`.

## Run with Docker

From this folder (`week03/handbook-chat`):

```bash
docker compose up --build
```

Wait until the terminal says the app is running. Open [http://localhost:8501](http://localhost:8501).

Ask: `How do I get reimbursed for a $300 train ticket?`  
Open **Retrieved evidence** and **Request details** under the answer. They show
the policy context and operational information used for the request.

Stop the app with `Ctrl+C` in that terminal.

## Run without Docker

From this folder, with the course virtual environment activated:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the URL Streamlit prints (usually [http://localhost:8501](http://localhost:8501)).

## If something fails

| Symptom | Fix |
|---------|-----|
| Authentication error | `.env` is missing, or a key is wrong. Paste both keys, restart the app. |
| No policy evidence appears | Confirm that the five Markdown files exist in `week03/policies`. |
| Port 8501 already in use | Another Streamlit or Docker app is using that port. Stop it, or change the port in `docker-compose.yml`. |
