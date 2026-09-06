import os

import streamlit as st
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

if not os.getenv("OPENAI_API_KEY") or not os.getenv("ANTHROPIC_API_KEY"):
    raise EnvironmentError("Set OPENAI_API_KEY and ANTHROPIC_API_KEY in .env")

# Week 2: role, constraint, escape hatch.
SYSTEM = (
    "You are an HR assistant. "
    "Answer only from the handbook context. "
    "If the answer is not in the context, say you cannot find it."
)


# Streamlit re-runs this file on every question. Cache the index so we
# do not embed the handbook again each time.
@st.cache_resource
def build_retriever():
    with open("handbook.txt", encoding="utf-8") as f:
        handbook = f.read()

    # Lab 1: split, embed, store.
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunk_texts = splitter.split_text(handbook)

    docs = []
    for i, text in enumerate(chunk_texts):
        docs.append(Document(page_content=text, metadata={"chunk": i}))

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    store = InMemoryVectorStore.from_documents(docs, embedding=embeddings)
    return store.as_retriever(search_kwargs={"k": 3})


retriever = build_retriever()
llm = ChatAnthropic(model="claude-haiku-4-5", temperature=0)

st.title("Ask the company handbook")
st.write("The app retrieves handbook chunks, then Claude answers only from those chunks.")

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "context" not in st.session_state:
    st.session_state["context"] = ""

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("How do I get reimbursed for a $300 train ticket?")
if question:
    st.session_state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    # Lab 1: closest chunks. Lab 2: answer only from those chunks.
    hits = retriever.invoke(question)
    parts = []
    for hit in hits:
        parts.append(hit.page_content)
    context = "\n\n".join(parts)

    reply = llm.invoke(
        [
            ("system", SYSTEM),
            ("user", "Context:\n" + context + "\n\nQuestion: " + question),
        ]
    )

    st.session_state["messages"].append({"role": "assistant", "content": reply.content})
    st.session_state["context"] = context

    with st.chat_message("assistant"):
        st.write(reply.content)

if st.session_state["context"]:
    st.text_area("Retrieved context", st.session_state["context"], height=160, disabled=True)
