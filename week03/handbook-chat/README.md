# Handbook chatbot

Labs 1–2 in one Streamlit app: chunk `handbook.txt`, embed, store, retrieve, answer.

## Run with Docker

1. Copy `env.example` to `.env` and paste `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`.
2. From this folder:

```bash
docker compose up --build
```

On Windows PowerShell, use `copy env.example .env` instead of `cp`.

3. Open [http://localhost:8501](http://localhost:8501).

## Run without Docker

From this folder, with the course virtual environment activated:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the URL Streamlit prints (usually [http://localhost:8501](http://localhost:8501)).
