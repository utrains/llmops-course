from dotenv import load_dotenv
import streamlit as st
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Same as Week 2 and Lab 2. Reads OPENAI_API_KEY and ANTHROPIC_API_KEY
# from the .env file in this folder. OpenAIEmbeddings and ChatAnthropic
# pick up those keys on their own.
load_dotenv()

# Standing rule for Claude (Week 2: role, constraint, escape hatch).
SYSTEM = (
    "You are an HR assistant. "
    "Answer only from the HR policy context. "
    "If the answer is not in the context, say you cannot find it. "
    "End a supported answer with the source and chunk citation supplied in the context."
)


# Streamlit re-runs this whole file on every question. @st.cache_resource
# keeps the index in memory so we do not embed the HR policy again each time.
@st.cache_resource
def build_retriever():
    with open("hr_policy.txt", encoding="utf-8") as f:
        policy = f.read()

    # Lab 1: split, embed, store.
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunk_texts = splitter.split_text(policy)

    docs = []
    for i, text in enumerate(chunk_texts):
        docs.append(
            Document(
                page_content=text,
                metadata={"source": "hr_policy.txt", "chunk": i},
            )
        )

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    store = InMemoryVectorStore.from_documents(docs, embedding=embeddings)
    # Return up to three closest chunks for inspection and generation.
    return store.as_retriever(search_kwargs={"k": 3})


retriever = build_retriever()
llm = ChatAnthropic(model="claude-haiku-4-5", temperature=0)

st.title("Ask the HR policy")
st.write("Ask questions using the approved HR policy as evidence.")

# session_state keeps values when Streamlit re-runs the file.
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
        citation = "Source: " + hit.metadata["source"] + ", chunk " + str(hit.metadata["chunk"])
        parts.append(citation + "\n" + hit.page_content)
    context = "\n\n".join(parts)

    reply = llm.invoke(
        [
            ("system", SYSTEM),
            ("human", "Context:\n" + context + "\n\nQuestion: " + question),
        ]
    )

    st.session_state["messages"].append({"role": "assistant", "content": reply.content})
    st.session_state["context"] = context

    with st.chat_message("assistant"):
        st.write(reply.content)

# Show the evidence used for the last answer.
if st.session_state["context"]:
    st.text_area("Retrieved evidence", st.session_state["context"], height=200, disabled=True)
