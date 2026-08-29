import os
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv(Path(__file__).resolve().parent / ".env")

if not os.getenv("OPENAI_API_KEY") or not os.getenv("ANTHROPIC_API_KEY"):
    raise EnvironmentError("Set OPENAI_API_KEY and ANTHROPIC_API_KEY in .env")

# Lab 4: split the handbook into chunks.
handbook = Path(__file__).resolve().parent.joinpath("handbook.txt").read_text(encoding="utf-8")
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunk_texts = splitter.split_text(handbook)

docs = []
for i, text in enumerate(chunk_texts):
    docs.append(Document(page_content=text, metadata={"chunk": i}))

# Lab 1 + Lab 5: embed each chunk and store the vectors.
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
store = InMemoryVectorStore.from_documents(docs, embedding=embeddings)
retriever = store.as_retriever(search_kwargs={"k": 3})

# Week 2: role, constraint, escape hatch.
SYSTEM = (
    "You are an HR assistant. "
    "Answer only from the handbook context. "
    "If the answer is not in the context, say you cannot find it."
)

llm = ChatAnthropic(model="claude-haiku-4-5", temperature=0)


def answer(question, history):
    history = list(history or [])
    question = (question or "").strip()
    if not question:
        return history, ""

    # Lab 5: embed the question, then cosine search for the closest chunks.
    hits = retriever.invoke(question)

    parts = []
    for hit in hits:
        parts.append(hit.page_content)
    context = "\n\n".join(parts)

    # Lab 6: send the retrieved context + the question to the chat model.
    reply = llm.invoke(
        [
            ("system", SYSTEM),
            ("user", "Context:\n" + context + "\n\nQuestion: " + question),
        ]
    )

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": reply.content})
    return history, context


with gr.Blocks(title="Handbook chatbot") as demo:
    gr.Markdown("# Ask the company handbook")
    chatbot = gr.Chatbot(label="Chat", height=400)
    context_box = gr.Textbox(label="Retrieved context", lines=8, interactive=False)
    msg = gr.Textbox(label="Question", placeholder="How do I get reimbursed for a $300 train ticket?")
    send = gr.Button("Send", variant="primary")
    send.click(answer, [msg, chatbot], [chatbot, context_box]).then(lambda: "", None, msg)
    msg.submit(answer, [msg, chatbot], [chatbot, context_box]).then(lambda: "", None, msg)

if __name__ == "__main__":
    demo.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
    )
