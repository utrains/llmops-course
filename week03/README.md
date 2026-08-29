# Week 3 (RAG Part 1: Embeddings, Retrieval, Grounded Answers)

Repository: https://github.com/utrains/llmops-course

Week 1 got a model talking. Week 2 made the answer something your software can actually use.
Week 3 answers the next question: **can I make it answer about *my* data?**

That technique is called **RAG** (Retrieval-Augmented Generation). You do not retrain the model.
You look up the relevant passages, then you put those passages in the prompt so the model has
something true to read before it answers.

This week you build that pipeline one piece at a time. Labs 1–6 use hosted OpenAI embeddings
and LangChain. Lab 6 also calls Claude to generate. Lab 7 still uses the older Ollama path
until it is moved next.

## What is in this week

| Lab | Notebook | What you learn |
|-----|----------|----------------|
| Lab 1 | [`lab1_embeddings_are_just_numbers.ipynb`](./lab1_embeddings_are_just_numbers.ipynb) | What an embedding is, and how to produce one with OpenAI + LangChain. |
| Lab 2 | [`lab2_cosine_similarity_the_one_math_idea_you_need.ipynb`](./lab2_cosine_similarity_the_one_math_idea_you_need.ipynb) | Same embeddings as Lab 1. Cosine similarity is how "close" two vectors are. |
| Lab 3 | [`lab3_keyword_search_vs_embedding_search_on_the_same_query.ipynb`](./lab3_keyword_search_vs_embedding_search_on_the_same_query.ipynb) | Same question, two scores: keyword (words) vs cosine (meaning). |
| Lab 4 | [`lab4_chunking_the_choice_that_decides_whether_rag_works.ipynb`](./lab4_chunking_the_choice_that_decides_whether_rag_works.ipynb) | Split `handbook.txt`, then embed. Too-small / usable / whole-file chunks, scored with cosine. |
| Lab 5 | [`lab5_store_the_vectors_then_search.ipynb`](./lab5_store_the_vectors_then_search.ipynb) | Put Lab 4's chunks in `InMemoryVectorStore`. Search with `retriever.invoke`. |
| Lab 6 | [`lab6_end_to_end_chat_with_your_own_pdf_in_80_lines.ipynb`](./lab6_end_to_end_chat_with_your_own_pdf_in_80_lines.ipynb) | Labs 1–5 plus generate: retrieve handbook chunks, Claude answers only from them. |
| Lab 7 | [`lab7_watch_rag_fail_on_real_world_edge_cases_active.ipynb`](./lab7_watch_rag_fail_on_real_world_edge_cases_active.ipynb) | Five ways this loop fails in production, and why Week 4 exists. |
| App | [`handbook-chat/`](./handbook-chat/) | Gradio chatbot: chunk, embed, retrieve, answer from `handbook.txt`. |

Run the labs **in order**. Each one reuses the object the previous lab taught you to build.

**Lab 1 uses hosted OpenAI embeddings, not Ollama.** The model is
`text-embedding-3-small`. The library is LangChain (`OpenAIEmbeddings`). Anthropic does not
ship an embedding model; that fact is in the lab on purpose. Cosine similarity is Lab 2.
LangGraph (a retrieve-then-generate graph) is named in Lab 6, not built. Lab 7 is still on
the older Ollama path until it is moved next.

## Handbook chatbot (after Lab 6)

[`handbook-chat/`](./handbook-chat/) is Labs 1–6 as a small Gradio app. Same handbook:
chunk, embed, store, retrieve, then Claude answers from those chunks.

```bash
cd week03/handbook-chat
cp env.example .env
# paste OPENAI_API_KEY and ANTHROPIC_API_KEY, then:
docker compose up --build
```

On Windows PowerShell, use `copy env.example .env` instead of `cp`.

Open [http://localhost:7860](http://localhost:7860). Full notes are in [`handbook-chat/README.md`](./handbook-chat/README.md).

## Lab 1 keys (required)

Lab 1 calls the OpenAI embeddings API. You need `OPENAI_API_KEY` before you run it.

1. Copy `.env.example` at the repository root to `.env` if you have not already.
2. Paste `OPENAI_API_KEY` from [platform.openai.com](https://platform.openai.com).

```bash
cp .env.example .env
```

`.env` is git-ignored. **Never commit a key.** Running Lab 1 costs a fraction of a cent: a few
embedding calls at about $0.02 / 1M tokens.

The same data-leaving-your-laptop warning from Week 2 applies. The moment you call a hosted
embedding API, the text of the prompt leaves your machine. That is a real decision in a company.

## Lab 6 keys (required)

Lab 6 embeds with OpenAI and generates with Claude. You need **both** keys in the same `.env`:

- `OPENAI_API_KEY` — same as Labs 1–5
- `ANTHROPIC_API_KEY` — same as Week 2, from [console.anthropic.com](https://console.anthropic.com)

## Where this sits in LLMOps

A language model does not know your employee handbook, your runbooks, or last Tuesday's incident.
If you ask it anyway, it will often answer with something that *sounds* right. That is how a
company ships a confident lie.

RAG is the standard fix in US industry right now:

1. **Index** your documents ahead of time (split, embed, store).
2. **Retrieve** the passages that match a new question.
3. **Generate** an answer that is only allowed to use those passages.

The skill that shows up in job postings is not "I called OpenAI." It is "I can swap the embedding
model, the splitter, and the vector store without rewriting the rest of the app." That is why Lab 1
uses LangChain's current partner package (`langchain-openai`).

Week 4 is where this becomes production: hybrid search, reranking, metadata filters, and evals.
This week you need to *see* the pieces, and then see them break.

## Prerequisites

Week 1 and Week 2 completed: virtual environment created. For **Lab 1** you also need
`OPENAI_API_KEY` in `.env` (see above). Labs 2–6 still use the local Ollama models from Weeks 1–2 until they
are migrated.

## Install the Week 3 dependencies

Week 3 adds LangChain, LangGraph, the OpenAI and Anthropic partner packages, NumPy, and `pypdf`.

From the repository root, with your virtual environment activated:

```bash
uv pip install -r requirements.txt
```

On Windows, if you hit a hardlink or metadata error, use copy mode:

```bash
uv pip install --link-mode=copy -r requirements.txt
```

Confirm it worked:

```bash
uv pip list
```

Look for `langchain-openai` and `numpy` in the list.

## Why Lab 1 uses this model

| Model | Role in Lab 1 | Why |
|-------|---------------|-----|
| OpenAI `text-embedding-3-small` | Embeddings | Cheapest current OpenAI embedder. 1536-d. ~$0.02 / 1M tokens. |

Claude does not produce embeddings. The notebook still teaches that, and lists the other embedding ids you should be able to name: `text-embedding-3-large`, Azure OpenAI, Voyage `voyage-4` / `voyage-4-lite` / `voyage-4-large`, Cohere `embed-v4.0`, Google Gemini embeddings, Bedrock Titan.

## Run the notebooks

Same two options as Weeks 1 and 2. Activate the virtual environment first. Run Lab 1, then 2, then
3, and so on.

### Option 1: JupyterLab

From the repository root:

```bash
jupyter lab
```

Open `week03/lab1_embeddings_are_just_numbers.ipynb`, then `Kernel > Change Kernel > llmop-course-venv`,
and run the cells in order.

### Option 2: VS Code / Cursor

Open the notebook, confirm the interpreter in the top-right corner is the `venv` from the
repository root, and run the cells in order.

## A note on the answers you will get

OpenAI embeddings are stable: the same sentence produces the same (or extremely close) vector
every time. Your cosine scores in Lab 2 will look like the notebook's, give or take a few
thousandths.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'langchain_openai'` | Week 3 Lab 1 added it. Re-run `uv pip install -r requirements.txt`, then restart the kernel. |
| `EnvironmentError: Missing OPENAI_API_KEY` | Copy `.env.example` to `.env` at the repo root, paste the key, restart the kernel. |
| `AuthenticationError` | The key is present but wrong, revoked, or has no credit. Check the OpenAI console. |
| `NotFoundError` about `text-embedding-3-small` | The model id moved on. Check the current ids on the OpenAI docs and update the constant in the notebook. |
| First OpenAI cell is slow | Normal. You are waiting on a network round-trip, not a local model load. |

## Quick check

You should be able to answer these after this week:

- What is an embedding, in one sentence a hiring manager would accept?
- Does Anthropic ship an embedding model? What do US Claude teams use instead?
- Name three embedding model ids besides `text-embedding-3-small`, and when you would pick each.
- What is the difference between `embed_query` and `embed_documents`?
- When does keyword search beat embedding search? When does it lose?
- Why does production RAG usually use **hybrid** retrieval?
- What goes wrong if chunks are too small? Too large?
- What does a vector store do that a Python cosine loop does not? Name one store besides `InMemoryVectorStore`.
- Draw the RAG loop: load → split → embed → store → retrieve → generate.
- Name two reasons a RAG demo that "worked on the handbook" will fail on real documents.

Those last two questions are the interview. Lab 7 is practice for them.
