# Week 5 — Agents that take actions (LLMOps)

Repository: https://github.com/utrains/llmops-course

## What this week is

In [Week 1](../week01/README.md) you got a language model to answer.

In [Week 2](../week02/README.md) you controlled the answer (prompts, JSON, function calling).

In [Weeks 3 and 4](../week03/README.md) you made the model answer about *your* documents (RAG).

**Week 5** answers the next course question: **Can I let the model take actions?**

An **AI agent** is a language model plus **tools** (functions your code runs), plus a loop: the model decides when to call a tool, your code runs it, the model reads the result, and then answers.

This week's industrial path builds toward a **Simple AWS Agent** in later labs. **Lab 1 starts simpler:** you write your own Python functions for a company order desk, turn them into tools, and learn what an agent is before AWS appears.

The theory path, in this order:

- Agent vs chatbot
- Think → Act → Observe → Respond
- Tools and tool calling
- Agent loop: User → LLM → Tool → Result → LLM
- Memory (short-term)
- MCP (Model Context Protocol)
- Orchestration with LangGraph

## What is in this folder

| Lab | Notebook | What you learn |
|-----|----------|----------------|
| 1 | [`lab1_tools_and_the_agent_loop.ipynb`](./lab1_tools_and_the_agent_loop.ipynb) | Custom tools and tool calling |
| 2 | [`lab2_the_agent_loop.ipynb`](./lab2_the_agent_loop.ipynb) | What an agent is (run tool, send result back, repeat) |
| 3 | [`lab3_when_agents_fail.ipynb`](./lab3_when_agents_fail.ipynb) | When agents fail |
| 4 | [`lab4_short_term_memory_for_the_order_desk.ipynb`](./lab4_short_term_memory_for_the_order_desk.ipynb) | Short-term conversation memory |
| 5 | [`lab4_mcp_for_aws_tools.ipynb`](./lab4_mcp_for_aws_tools.ipynb) | MCP (server, client, tools) |
| 6 | [`lab5_langgraph_orchestration.ipynb`](./lab5_langgraph_orchestration.ipynb) | LangGraph orchestration |
| 7 | [`lab6_agent_memory_mcp_langgraph.ipynb`](./lab6_agent_memory_mcp_langgraph.ipynb) | Optional synthesis: combine the layers |

Shared files:

| File | Role |
|------|------|
| [`aws_data.py`](./aws_data.py) | Mock EC2 / S3 / cost inventory |
| [`aws_tools.py`](./aws_tools.py) | LangChain tools wrapping `aws_data` |
| [`mcp_aws_server.py`](./mcp_aws_server.py) | Simple MCP server for Lab 4+ |

Run the labs **in order**. Each lab builds on the previous one.

## How to run this week

### Step 1. Finish Weeks 1–4

You need the course virtual environment and notebook kernel from Week 1.

### Step 2. Activate the virtual environment

From the **repository root**:

- macOS / Linux: `source venv/bin/activate`
- Windows PowerShell: `venv\Scripts\Activate.ps1`

### Step 3. Install this week's packages

```bash
uv pip install -r week05/requirements.txt
```

Windows hardlink error:

```bash
uv pip install --link-mode=copy -r week05/requirements.txt
```

### Step 4. Create `.env` in the `week05` folder

```bash
cd week05
cp .env.example .env
```

Windows PowerShell:

```powershell
cd week05
copy .env.example .env
```

Paste `ANTHROPIC_API_KEY`. **Never commit `.env`.**

| Key | Used for |
|-----|----------|
| `ANTHROPIC_API_KEY` | Claude `claude-haiku-4-5` in all labs |

Open notebooks **from the `week05` folder** so `import aws_data` and `load_dotenv()` find local files.

### Step 5. Run Lab 1 → Lab 6

Activate the venv. Kernel = course venv. Run every cell from the top.

**Lab 4 note.** The MCP server file is [`mcp_aws_server.py`](./mcp_aws_server.py). The notebook shows how the client talks to it. Follow the Lab 4 cells in order.

## Cost

A few short Claude calls per lab. Fractions of a cent with Haiku.

## What you should be able to explain after Week 5

- An agent is a model that can call tools in a loop, not only chat.
- The agent loop is User → LLM → Tool → Result → LLM.
- Chatbots without tools guess; agents with tools can look up facts.
- Short-term memory is conversation history your application stores and resends.
- MCP standardizes how an agent discovers and calls tools on a server.
- LangGraph makes multi-step routing (nodes, edges, state) explicit.
