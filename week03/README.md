# Week 3 — Answer from your company's HR policy

Repository: https://github.com/utrains/llmops-course

## What this week is

In [Week 1](../week01/README.md) you sent a question to a **language model** and printed the answer. A language model is the program that writes answers in sentences (Ollama or Claude).

In [Week 2](../week02/README.md) you controlled that answer: a clear system prompt, JSON your code can read, and function calling.

The language model was trained on public text. It does not contain your company's **HR policy** (reimbursements, time off, parental leave). If an employee asks "How do I get reimbursed for a $300 train ticket?" and you send only that question, the model will guess.

This week you search *your* HR policy file, then (Lab 2) put the matching paragraphs in the prompt so the model answers from those paragraphs. That method is called **RAG** — Retrieval-Augmented Generation:

- **Retrieval** = search your file for the pieces that match the question
- **Generation** = the language model writes the answer
- **Augmented** = the answer is based on those pieces, not only on the model's training

You do not retrain the model.

Each step below is a word you will run in code:

| Step | Plain meaning | Where |
|------|----------------|--------|
| **Load** | Open `hr_policy.txt` and read it into Python as one string. | Lab 1 |
| **Split** | Cut that string into smaller pieces called **chunks**. | Lab 1 |
| **Embed** | Turn a piece of text into a list of numbers that stand for its meaning. | Lab 1 |
| **Store** | Save those lists of numbers so you can search them later. | Lab 1 |
| **Retrieve** | For a new question, find the chunks whose numbers are closest to the question. | Lab 1 |
| **Generate** | Send those chunks and the question to Claude, and get a sentence answer. | Lab 2 |

Lab 3 uses the same search-then-answer loop on messy documents so you can see when it is not enough. Fixes wait for Week 4.

Run the labs **in order**. All setup is in this file so the notebooks stay on the lesson.

## What is in this folder

| | File | What you do |
|---|------|-------------|
| Lab 1 | [`lab1_from_a_handbook_to_a_search.ipynb`](./lab1_from_a_handbook_to_a_search.ipynb) | Load the HR policy, split it, embed, score closeness, compare word search vs meaning search, store, search. |
| Lab 2 | [`lab2_end_to_end_chat_with_your_own_docs.ipynb`](./lab2_end_to_end_chat_with_your_own_docs.ipynb) | Same search, then Claude answers only from the retrieved chunks. |
| Lab 3 | [`lab3_watch_rag_fail_on_real_world_edge_cases.ipynb`](./lab3_watch_rag_fail_on_real_world_edge_cases.ipynb) | Same loop on seven messy documents. Five named failures. |
| App | [`handbook-chat/`](./handbook-chat/) | Optional Streamlit app after Lab 2. Same HR policy, same loop. |
| Policy file | [`hr_policy.txt`](./hr_policy.txt) | The HR policy the notebooks load. Keep it next to the notebooks. |

**Lab 1 uses OpenAI embeddings, not Ollama.** The model is `text-embedding-3-small`. Anthropic does not offer an embedding model. Claude writes the answers in Labs 2 and 3. OpenAI does not.

This week needs an internet connection. You will call hosted APIs.

## How to run this week (do these steps in order)

### Step 1. Finish Weeks 1 and 2

You need the virtual environment (`venv`) at the repository root, and the notebook kernel named `llmop-course-venv`. If that is missing, follow [Week 1 — Quickstart](../week01/README.md).

### Step 2. Activate the virtual environment

From the **repository root**:

- macOS / Linux: `source venv/bin/activate`
- Windows PowerShell: `venv\Scripts\Activate.ps1`

### Step 3. Install this week's packages

This week has its own file: [`requirements.txt`](./requirements.txt).

Still from the repository root:

```bash
uv pip install -r week03/requirements.txt
```

On Windows, if you hit a hardlink or metadata error:

```bash
uv pip install --link-mode=copy -r week03/requirements.txt
```

Check that the packages are there:

```bash
uv pip list
```

Look for `langchain-openai`, `langchain-anthropic`, `langchain-text-splitters`, `numpy`, and `pypdf`.

### Step 4. Create `.env` in the `week03` folder

The notebooks call `load_dotenv()` the same way as Week 2. They also open `hr_policy.txt` from this folder. Open notebooks from `week03` so both files are found.

```bash
cd week03
cp .env.example .env
```

Windows PowerShell:

```powershell
cd week03
copy .env.example .env
```

Open `.env` and paste the keys. **Never commit `.env`.**

| Key | Where to get it | Used in |
|-----|-----------------|---------|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) | Lab 1 from the embed step; Labs 2 and 3; the app |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | Labs 2 and 3; the app. You may already have this from Week 2. |

The text you send to OpenAI or Claude leaves your laptop. That is a real decision in a company.

**Cost.** A few embedding calls and a few short Claude replies. Fractions of a cent. OpenAI `text-embedding-3-small` is about $0.02 per 1 million tokens.

### Step 5. Run Lab 1, then Lab 2, then Lab 3

Activate the virtual environment first. Open each notebook **from this `week03` folder**. Run every cell from the top. If you restart the kernel, start again from the first cell.

#### Option A: JupyterLab

From the repository root:

```bash
jupyter lab
```

1. Open `week03/lab1_from_a_handbook_to_a_search.ipynb`.
2. `Kernel` > `Change Kernel` > `llmop-course-venv`.
3. Run all cells from the top. Read each output before you continue.
4. Then open Lab 2, then Lab 3. Same kernel. Same order.

Stop JupyterLab with `Ctrl+C` in that terminal.

#### Option B: VS Code / Cursor

1. Install the Microsoft `Python` and `Jupyter` extensions if they are missing.
2. Open the notebook under `week03`.
3. Select the interpreter from the repository-root `venv` (`venv\Scripts\python.exe` on Windows, `venv/bin/python` on macOS / Linux).
4. Confirm the kernel in the top-right corner is that same interpreter.
5. Run the cells in order.

#### What you should see

**Lab 1.** The printed HR policy. Chunk counts for sizes 200, 500, and 2000. An embedding that is 1536 numbers. Cosine of a list of numbers with itself is `1.0`. Keyword search misses a paraphrase that meaning search finds. The train-ticket question lands on the reimbursement chunk.

**Lab 2.** Retrieved chunks printed **before** the answer. Claude answers the reimbursement question from those chunks. A question the HR policy does not cover (pet bereavement) is refused. Skip the optional PDF cell unless you add `hr_policy.pdf` next to the notebook.

**Lab 3.** Does **not** use `hr_policy.txt`. Seven short messy documents. Print the retrieved rows and name the failure. Week 4 is where you fix these.

OpenAI embeddings are stable. Lab 1 cosine scores should match the notebook within a few thousandths.

### Step 6. Optional — run the Streamlit app (after Lab 2)

[`handbook-chat/`](./handbook-chat/) is Labs 1–2 as a small web app. It uses its **own** `.env` in that folder, not the labs `.env`.

1. Copy keys into that folder:

```bash
cd week03/handbook-chat
cp env.example .env
```

Windows PowerShell: `copy env.example .env`.

2. Paste `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` into that `.env`.
3. Start the app:

```bash
docker compose up --build
```

4. Open [http://localhost:8501](http://localhost:8501).

Without Docker, from the same folder, with the course virtual environment activated:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Full notes: [`handbook-chat/README.md`](./handbook-chat/README.md).

## Models this week

| Model | What it does | Why this one |
|-------|----------------|--------------|
| OpenAI `text-embedding-3-small` | Turns text into a list of 1536 numbers | Current cheap OpenAI embedder. |
| Claude `claude-haiku-4-5` | Writes the sentence answers in Labs 2 and 3 | Same model as Week 2. |

Use **one embedding model per index**. If you change the model, you must embed every chunk again.

Names to recognise (you do not run them this week): `text-embedding-3-large`, Voyage `voyage-4` / `voyage-4-lite`, Cohere `embed-v4.0`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `FileNotFoundError: hr_policy.txt` | The notebook is not running from `week03`. Open the notebook inside this folder. Do not move the file. Restart the kernel. |
| Missing key / `AuthenticationError` | Copy `week03/.env.example` to `week03/.env`, paste the key, restart the kernel. Labs 2 and 3 need both keys. |
| `ModuleNotFoundError: No module named 'langchain_openai'` (or `langchain_anthropic`, `numpy`, `pypdf`) | Wrong kernel, or packages not installed. Activate `venv`, run `uv pip install -r week03/requirements.txt`, select `llmop-course-venv`, restart the kernel. |
| `AuthenticationError` after the key is present | The key is wrong, revoked, or has no credit. Check the OpenAI or Anthropic console. |
| `NotFoundError` about `text-embedding-3-small` or `claude-haiku-4-5` | The model id moved. Check the provider docs and update the name in the notebook. |
| First API cell is slow | Normal. You are waiting on the network. |
| `NameError` (`POLICY`, `embeddings`, `retriever`, `medium`, …) | You skipped a cell or restarted the kernel. Run from the first cell again. |
| Lab 2 optional PDF cell prints "No hr_policy.pdf found" | Expected. Skip it unless you add that PDF next to the notebook. |
| Cosine of a list of numbers with itself is not `1.0` | Stop. Both lists must come from the same embedding model. Re-run Lab 1 from the embed step. |

Windows venv activation and `uv` hardlink errors are in [Week 1 troubleshooting](../week01/README.md).

## After this week you should be able to explain

- What goes wrong if chunks are too small? Too large?
- What is an embedding, in one sentence?
- Does Anthropic offer an embedding model?
- What is the difference between `embed_query` and `embed_documents`?
- When does keyword search beat meaning search? When does it lose?
- What does a vector store do that a Python cosine loop does not?
- Name the six steps: load, split, embed, store, retrieve, generate. Say which lab does which.
- Name two reasons a demo that worked on this HR policy will fail on real company documents.

Lab 3 is practice for the last two.
