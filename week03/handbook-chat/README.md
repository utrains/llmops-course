# HR policy chatbot

This folder is Labs 1 and 2 as a small Streamlit app. It loads `hr_policy.txt`,
cuts it into chunks, embeds the chunks, searches the closest three for a question,
then Claude answers only from those chunks.

You should finish Lab 2 before you run this app, so you have already seen the same
loop in the notebook.

## Files in this folder

| File | What it is |
|------|------------|
| `app.py` | The Streamlit app. Read the comments in that file. |
| `hr_policy.txt` | The same HR policy as the Week 3 notebooks. |
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
Read the **Retrieved chunks** box under the answer. Those are the paragraphs Claude was allowed to use.

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
| `FileNotFoundError: hr_policy.txt` | Run the command from this folder, not from the repository root. |
| Port 8501 already in use | Another Streamlit or Docker app is using that port. Stop it, or change the port in `docker-compose.yml`. |
