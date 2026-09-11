# Week 3: Build and evaluate an HR policy RAG system

Week 1 introduced model calls. Week 2 introduced controlled prompts, structured output, and tools. Week 3 adds company knowledge through retrieval-augmented generation.

The proposition is an HR policy assistant that gives employees immediate, grounded answers from approved company policies instead of sending every question to an HR mailbox. If the current email process can take up to 24 hours, the assistant can provide a first response in seconds, twenty-four hours a day, while citing the policy evidence used. That gives HR more time for complex and sensitive cases, reduces repeated questions, shortens response queues, improves consistency, and creates a measurable record of which questions remain unresolved. The labs expose each moving part so the stakeholder can see how those benefits are delivered and measured rather than hidden behind a framework.

## Engineering ownership

AI engineers commonly design chunking, embeddings, retrieval, prompts, and answer behavior. Data engineers commonly own source connections, parsing, cleaning, and document refresh pipelines. LLMOps engineers must understand those decisions well enough to reproduce, deploy, evaluate, monitor, troubleshoot, and safely release the complete system.

The design decision used in these labs is structure-aware recursive chunking with controlled size, limited overlap, and source metadata. Learners implement and test that decision as an operational pipeline.

## What makes this LLMOps work

The notebooks do not stop at retrieving text. They also make the pipeline reviewable:

- the source, section, version, status, chunk settings, and embedding model are visible;
- retrieval evidence is inspected before generation;
- archived records can be excluded with metadata filters;
- known questions run as repeatable retrieval tests;
- latency and retrieved sources are recorded for troubleshooting;
- a release decision is made from evaluation results before the application is containerized.

The lab uses a local Chroma vector store so each moving part stays visible. The same index contract can later be implemented with pgvector, Pinecone, Qdrant, Weaviate, Milvus, OpenSearch, Azure AI Search, or another production vector store.

## Lab progression

| Lab | Business mission | Moving pieces exposed |
| --- | --- | --- |
| [Lab 1](./lab1_from_a_handbook_to_a_search.ipynb) | Turn a handbook PDF into a searchable, traceable index. | PDF loading, page inspection, recursive splitting, chunk size, overlap, metadata, embeddings, Chroma, similarity search |
| [Lab 2](./lab2_end_to_end_chat_with_your_own_docs.ipynb) | Produce a grounded HR answer with citations and an insufficient-evidence response. | retrieval, context construction, system instructions, generation model, citations, missing evidence |
| [Lab 3](./lab3_watch_rag_fail_on_real_world_edge_cases.ipynb) | Evaluate retrieval and make an evidence-based release decision. | exact identifiers, conflicting versions, lifecycle filters, missing answers, tests, latency, release gate |
| [Containerized app](./handbook-chat/) | Run the same request path through a chat interface. | Streamlit, cached index, API configuration, Docker |

Each exercise follows the same learning pattern:

1. Business mission
2. Why the moving piece matters
3. One focused code change
4. Output inspection
5. Production conclusion

The notebooks are designed to be run from top to bottom. Each code cell has one focused job, and the output is part of the lesson. If the kernel is restarted, run the earlier cells again before continuing.

## Request path

```text
Approved HR documents
    -> parse and inspect
    -> split into traceable chunks
    -> create embeddings
    -> store vectors and metadata
    -> retrieve evidence
    -> build grounded context
    -> generate and cite an answer
    -> evaluate and make a release decision
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

Never commit a real key. The `.env` file is git-ignored.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `ModuleNotFoundError` for LangChain, Chroma, or `pypdf` | Run the Week 3 install command and confirm that the notebook uses the project virtual environment. |
| Missing API key or authentication error | Confirm that `week03/.env` exists, contains the correct key, and that the kernel was restarted after creating it. |
| PDF text is empty or incomplete | The source may be scanned or use a complex layout. Production systems use OCR or a managed document parser for those files. |
| Chroma returns no useful matches | Check that the index cell ran, the question uses the same embedding model, and the retrieved chunks are printed before generation. |
| The answer says there is not enough evidence | That is an intended result when the retrieved policy does not support the question. |
| Docker cannot start the application | Confirm Docker Desktop is running and that the application `.env` file exists. |

## Models

| Model | Responsibility |
| --- | --- |
| OpenAI `text-embedding-3-small` | Embeds both indexed chunks and employee questions into the same vector space. |
| Anthropic `claude-haiku-4-5` | Generates the grounded response in Lab 2 and the application. |

These are the implementation choices for the lab, not the only valid choices. Embedding providers commonly seen in RAG roles include OpenAI, Cohere, Voyage AI, Google, and open-weight BGE or E5 models. Generation commonly uses OpenAI, Anthropic, Google Gemini, or hosted open-weight models through Bedrock, Azure AI Foundry, or Vertex AI. Vector search roles commonly mention pgvector, Pinecone, Qdrant, Weaviate, Milvus, and Azure AI Search. Students should be able to explain why a team might choose a different provider, then record and evaluate that change.

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
