# Week 3: Build and evaluate an HR policy RAG system

Week 1 introduced model calls. Week 2 introduced controlled prompts, structured output, and tools. Week 3 adds company knowledge through retrieval-augmented generation.

The business scenario remains the same across all three labs: employees need reliable answers from approved HR policies. The labs expose each moving part so changes can be measured rather than hidden behind a framework.

## Engineering ownership

AI engineers commonly design chunking, embeddings, retrieval, prompts, and answer behavior. Data engineers commonly own source connections, parsing, cleaning, and document refresh pipelines. LLMOps engineers must understand those decisions well enough to reproduce, deploy, evaluate, monitor, troubleshoot, and safely release the complete system.

The design decision used in these labs is structure-aware recursive chunking with controlled size, limited overlap, and source metadata. Learners implement and test that decision as an operational pipeline.

## Lab progression

| Lab | Business mission | Moving pieces exposed |
| --- | --- | --- |
| [Lab 1](./lab1_from_a_handbook_to_a_search.ipynb) | Find the correct policy evidence for an employee question. | source inspection, section parsing, recursive splitting, chunk size, overlap, metadata, embeddings, similarity, top k |
| [Lab 2](./lab2_end_to_end_chat_with_your_own_docs.ipynb) | Produce a grounded HR answer with citations and an insufficient-evidence response. | retrieval, context construction, system instructions, generation model, citations, missing evidence |
| [Lab 3](./lab3_watch_rag_fail_on_real_world_edge_cases.ipynb) | Detect retrieval failures before a pipeline change reaches production. | exact identifiers, conflicting versions, lifecycle metadata, missing answers, test cases, retrieval accuracy |
| [Containerized app](./handbook-chat/) | Run the same request path through a chat interface. | Streamlit, cached index, API configuration, Docker |

Each exercise follows the same learning pattern:

1. Business mission
2. Why the moving piece matters
3. One focused code change
4. Output inspection
5. Production conclusion

## Request path

```text
HR documents
    -> parse and inspect
    -> split into traceable chunks
    -> create embeddings
    -> store vectors and metadata
    -> retrieve evidence
    -> build grounded context
    -> generate and cite an answer
    -> evaluate the result
```

## Setup

From the repository root:

```powershell
uv pip install -r week03/requirements.txt
cd week03
copy .env.example .env
```

Add these keys to `week03/.env`:

```text
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
```

Open the notebooks from the `week03` directory and run them in order. API inputs leave the local machine, so company documents require an approved provider, data-handling policy, and access model.

## Models

| Model | Responsibility |
| --- | --- |
| OpenAI `text-embedding-3-small` | Embeds both indexed chunks and employee questions into the same vector space. |
| Anthropic `claude-haiku-4-5` | Generates the grounded response in Lab 2 and the application. |

Use one embedding model and configuration per index. Changing the embedding model requires rebuilding the index and rerunning the retrieval evaluation.

## Run the containerized application

After completing the notebooks:

```powershell
cd week03/handbook-chat
copy env.example .env
docker compose up --build
```

Open http://localhost:8501. The container is the deployment artifact for this milestone. The in-memory vector store is intentionally visible and replaceable so the same evaluation can later be applied to a production vector database.

## Completion evidence

At the end of Week 3, the repository should demonstrate:

- reproducible document indexing;
- visible chunk text and metadata;
- the same embedding model for documents and questions;
- retrieved evidence shown before generation;
- grounded answers with citations;
- a clear response when evidence is insufficient;
- retrieval tests that run before and after a pipeline change;
- a containerized chat application.
