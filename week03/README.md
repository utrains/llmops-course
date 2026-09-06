# Week 3 (RAG Part 1: From a handbook to a grounded answer)

Repository: https://github.com/utrains/llmops-course

Week 1 got a model talking. Week 2 made the answer something your software can use.
Week 3 answers the next question: **can the model answer about *my* data?**

That technique is **RAG** (Retrieval-Augmented Generation). You do not retrain the model.
You look up the relevant passages, put them in the prompt, and the model answers from those passages.

```
load → split → embed → store → retrieve → generate
        Lab 1 (search)                    Lab 2
```

Lab 3 uses the same loop on a messy index so you can see when search + generate is not enough.
Fixes wait for Week 4.

All setup lives here so the notebooks stay on the lesson. Run the labs **in order**.

## What is in this week

| | File | What you do |
|---|------|-------------|
| Lab 1 | [`lab1_from_a_handbook_to_a_search.ipynb`](./lab1_from_a_handbook_to_a_search.ipynb) | Load `handbook.txt`, chunk it, embed, score with cosine, compare keyword vs meaning, store, `retriever.invoke`. |
| Lab 2 | [`lab2_end_to_end_chat_with_your_own_docs.ipynb`](./lab2_end_to_end_chat_with_your_own_docs.ipynb) | Same retrieve, then Claude answers **only** from those chunks. |
| Lab 3 | [`lab3_watch_rag_fail_on_real_world_edge_cases.ipynb`](./lab3_watch_rag_fail_on_real_world_edge_cases.ipynb) | Same loop on a messy index. Five named failures. |
| App | [`handbook-chat/`](./handbook-chat/) | Optional Streamlit app after Lab 2. Same handbook, same loop. |

`handbook.txt` sits in this folder, next to the notebooks. Do not move the notebooks.

**Lab 1 uses hosted OpenAI embeddings, not Ollama.** The model is `text-embedding-3-small`.
Anthropic does not ship an embedding model. Claude writes answers in Labs 2 and 3. OpenAI does not.

## Do this in order

1. Finish [Week 1](../week01/README.md) and [Week 2](../week02/README.md) (venv created, packages installed).
2. Activate the same virtual environment.
3. Install this week's packages from the repository root.
4. Put API keys in `.env` (Lab 1 needs OpenAI; Labs 2 and 3 need OpenAI **and** Anthropic).
5. Open the notebook from this `week03` folder. Select the course kernel. Run every cell from the top.
6. After Lab 2, optionally run [`handbook-chat/`](./handbook-chat/).

## Prerequisites

- Week 1 virtual environment (`venv` at the repository root)
- Week 1 kernel registered as `llmop-course-venv` (see [Week 1](../week01/README.md) if the kernel is missing)
- Internet access (this week calls hosted APIs)
- `OPENAI_API_KEY` before Lab 1 Step 4
- `ANTHROPIC_API_KEY` before Lab 2 (same key as Week 2 if you already created one)

Ollama is **not** used this week.

## Install the Week 3 packages

This week has its own file: [`requirements.txt`](./requirements.txt). It is the Week 3 subset of the repository-root list (no Ollama, no Week 4 packages).

From the **repository root**, with the virtual environment activated:

```bash
uv pip install -r week03/requirements.txt
```

On Windows, if you hit a hardlink or metadata error:

```bash
uv pip install --link-mode=copy -r week03/requirements.txt
```

Confirm the new packages:

```bash
uv pip list
```

Look for `langchain-openai`, `langchain-anthropic`, `langchain-text-splitters`, `numpy`, and `pypdf`.

If you do not have a venv yet, follow [Week 1 — Quickstart](../week01/README.md), then come back here.

## API keys

Copy `.env.example` in this `week03` folder to `.env` if you do not already have one.

```bash
cd week03
cp .env.example .env
```

On Windows PowerShell:

```powershell
cd week03
copy .env.example .env
```

Paste the keys:

| Key | Where to get it | Used in |
|-----|-----------------|---------|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) | Lab 1 from Step 4; Labs 2 and 3; the app |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | Labs 2 and 3; the app |

`.env` is git-ignored. **Never commit a key.**

The notebooks call `load_dotenv()` and open `handbook.txt` from this folder. Open the notebooks from `week03` so both files are found.

The text you embed or send to Claude leaves your laptop. That is a real decision in a company.

**Cost.** A few embedding calls plus a few short Claude replies. Fractions of a cent.
OpenAI `text-embedding-3-small` is about $0.02 / 1M tokens.

## Models this week

| Model | Role | Why |
|-------|------|-----|
| OpenAI `text-embedding-3-small` | Embeddings (1536 numbers per text) | Current cheap OpenAI embedder. |
| Claude `claude-haiku-4-5` | Chat answers in Labs 2 and 3 | Same model as Week 2. Fast enough for short grounded answers. |

Use **one embedding model per index**. If you change the model, you must embed every chunk again.

Other embedding names to recognise (you do not run them): `text-embedding-3-large`, Voyage `voyage-4` / `voyage-4-lite`, Cohere `embed-v4.0`.

## Run the notebooks

Activate the virtual environment first. Open each notebook **from this `week03` folder** so `handbook.txt` is found. Run Lab 1, then Lab 2, then Lab 3. Run cells **in order**. If you restart the kernel, start again from the first cell.

### Option 1: JupyterLab

From the repository root:

```bash
jupyter lab
```

1. Open `week03/lab1_from_a_handbook_to_a_search.ipynb`.
2. `Kernel` > `Change Kernel` > `llmop-course-venv`.
3. Run all cells from the top. Read each output before you continue.
4. Then open Lab 2, then Lab 3, same kernel, same order.

Stop JupyterLab with `Ctrl+C` in that terminal.

### Option 2: VS Code / Cursor

1. Install the Microsoft `Python` and `Jupyter` extensions if they are missing.
2. Open the notebook under `week03`.
3. Select the interpreter from the repository-root `venv` (`venv\Scripts\python.exe` on Windows, `venv/bin/python` on macOS / Linux).
4. Confirm the kernel in the top-right corner is that same interpreter.
5. Run the cells in order.

### What you should see

**Lab 1** — print the handbook; compare chunk sizes 200 / 500 / 2000; embed a sentence (1536 numbers); cosine of a vector with itself is `1.0`; keyword search misses a paraphrase that cosine finds; the train-ticket question lands on the reimbursement chunk; `retriever.invoke` returns the same idea without your `for` loop.

**Lab 2** — retrieve first and **read the chunks**; Claude answers the reimbursement question from those chunks; a question the handbook does not cover should be refused. Skip the optional `handbook.pdf` cell unless you drop a PDF next to the notebook.

**Lab 3** — does **not** use `handbook.txt`. It indexes a small hostile corpus. Print the hits, name the failure. Week 4 is where you fix these.

OpenAI embeddings are stable. Lab 1 cosine scores should match the notebook within a few thousandths.

## Optional: handbook chatbot (after Lab 2)

[`handbook-chat/`](./handbook-chat/) is Labs 1–2 as a Streamlit app. It uses its **own** `.env` in that folder, not the labs `.env`.

```bash
cd week03/handbook-chat
cp env.example .env
```

PowerShell: `copy env.example .env`.

Paste `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`, then:

```bash
docker compose up --build
```

Open [http://localhost:8501](http://localhost:8501). To run without Docker: `pip install -r requirements.txt` then `streamlit run app.py`. Full notes: [`handbook-chat/README.md`](./handbook-chat/README.md).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `FileNotFoundError: handbook.txt` | The notebook is not running from `week03`. Open `week03/lab1_...ipynb` or `week03/lab2_...ipynb`. Do not move the file. Restart the kernel. |
| `EnvironmentError` / missing `OPENAI_API_KEY` | Copy `week03/.env.example` to `week03/.env`, paste the key, restart the kernel. |
| `EnvironmentError` about `ANTHROPIC_API_KEY` | Labs 2 and 3 need both keys in the same `.env`. Restart the kernel after you paste. |
| `ModuleNotFoundError: No module named 'langchain_openai'` (or `langchain_anthropic`, `numpy`, `pypdf`) | Wrong kernel, or packages not installed. Activate `venv`, run `uv pip install -r week03/requirements.txt`, select `llmop-course-venv`, restart the kernel. |
| `AuthenticationError` | The key is present but wrong, revoked, or has no credit. Check the OpenAI or Anthropic console. |
| `NotFoundError` about `text-embedding-3-small` or `claude-haiku-4-5` | The model id moved. Check the provider docs and update the constant in the notebook. |
| First API cell is slow | Normal. You are waiting on the network, not a local model load. |
| `NameError` (`HANDBOOK`, `embeddings`, `retriever`, `medium`, …) | You skipped a cell or restarted the kernel. Run from the first cell again. |
| Lab 2 optional PDF cell prints "No handbook.pdf found" | Expected. Skip it unless you add `handbook.pdf` next to the notebook. |
| Cosine of a vector with itself is not `1.0` | Stop. Both vectors must come from the same embedding model. Re-run Step 5 and Step 6 from the top. |

Windows venv activation and `uv` hardlink errors are covered in [Week 1 troubleshooting](../week01/README.md).

## Quick check

You should be able to answer these after this week:

- What goes wrong if chunks are too small? Too large?
- What is an embedding, in one sentence?
- Does Anthropic ship an embedding model?
- What is the difference between `embed_query` and `embed_documents`?
- When does keyword search beat embedding search? When does it lose?
- What does a vector store do that a Python cosine loop does not?
- Draw the RAG loop: load → split → embed → store → retrieve → generate.
- Name two reasons a RAG demo that worked on the handbook will fail on real documents.

Lab 3 is practice for the last two.
