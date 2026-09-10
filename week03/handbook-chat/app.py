from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
import streamlit as st
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
GENERATION_MODEL = "claude-haiku-4-5"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
INDEX_VERSION = "2026.1"

SYSTEM_MESSAGE = (
    "You are the company HR policy assistant. "
    "Answer only from the supplied context. "
    "If the answer is absent, say: I cannot find that answer in the available HR policy. "
    "End supported answers with the source and section used."
)


@st.cache_resource
def build_vector_store():
    policy_folder = Path("policies")
    if not policy_folder.exists():
        policy_folder = Path("../policies")

    policy_files = sorted(policy_folder.glob("*.md"))
    sections = []

    for policy_file in policy_files:
        parts = policy_file.read_text(encoding="utf-8").split("\n## ")
        for part in parts[1:]:
            heading, text = part.split("\n", 1)
            sections.append(
                {"source": policy_file.name, "section": heading, "text": text.strip()}
            )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    documents = []
    for section in sections:
        pieces = splitter.split_text(section["text"])
        for position, piece in enumerate(pieces):
            metadata = {
                "source": section["source"],
                "section": section["section"],
                "position": position,
                "version": INDEX_VERSION,
                "status": "current",
            }
            documents.append(Document(page_content=piece, metadata=metadata))

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    return InMemoryVectorStore.from_documents(documents, embedding=embeddings)


vector_store = build_vector_store()
llm = ChatAnthropic(model=GENERATION_MODEL, temperature=0)

st.title("Company HR policy assistant")
st.write("Ask a question and inspect the policy evidence used for the answer.")

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "evidence" not in st.session_state:
    st.session_state["evidence"] = ""
if "request_details" not in st.session_state:
    st.session_state["request_details"] = {}

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("Can I expense a $300 train ticket without approval?")

if question:
    st.session_state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    started = perf_counter()
    def is_current(document):
        return document.metadata["status"] == "current"

    results = vector_store.similarity_search_with_score(
        question, k=3, filter=is_current
    )

    context_parts = []
    sources = []
    for document, score in results:
        citation = document.metadata["source"] + " | " + document.metadata["section"]
        sources.append(citation)
        context_parts.append("Source: " + citation + "\n" + document.page_content)

    context = "\n\n".join(context_parts)
    user_message = "Context:\n" + context + "\n\nEmployee question:\n" + question
    response = llm.invoke([("system", SYSTEM_MESSAGE), ("human", user_message)])
    elapsed_ms = round((perf_counter() - started) * 1000, 1)

    st.session_state["messages"].append(
        {"role": "assistant", "content": response.content}
    )
    st.session_state["evidence"] = context
    st.session_state["request_details"] = {
        "index_version": INDEX_VERSION,
        "embedding_model": EMBEDDING_MODEL,
        "generation_model": GENERATION_MODEL,
        "retrieved_sources": sources,
        "retrieved_sections": [
            document.metadata["section"] for document, score in results
        ],
        "elapsed_ms": elapsed_ms,
    }

    with st.chat_message("assistant"):
        st.write(response.content)

if st.session_state["evidence"]:
    with st.expander("Retrieved evidence"):
        st.text(st.session_state["evidence"])

    with st.expander("Request details"):
        st.json(st.session_state["request_details"])
