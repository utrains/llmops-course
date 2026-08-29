# Handbook chatbot

Labs 1–6 in one Gradio app: chunk `handbook.txt`, embed, store, retrieve, answer.

## Run with Docker

1. Copy `env.example` to `.env` and paste `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`.
2. From this folder:

```bash
docker compose up --build
```

3. Open [http://localhost:7860](http://localhost:7860).

## Run without Docker

```bash
pip install -r requirements.txt
python app.py
```
