# Lab 2 (Prompts, Structured Outputs, Function Calling)

Repository: https://github.com/utrains/llmops-course

Week 1 got a model talking to you. Week 2 is about **controlling what it says**, so the answer is
something your software can actually use: engineered prompts, JSON with a shape you chose, the
function-calling loop, and a first look at measuring whether a prompt works.

The notebook for this week is [`week02_labs.ipynb`](./week02_labs.ipynb). All setup lives here in the
README so the notebook stays focused on the lesson.

## What is in this week

| Lab | Topic | Deck section |
|-----|-------|--------------|
| Lab 1 | Message roles, and why the model forgets | 2 |
| Lab 2 | System prompts: a vague one vs the 5 parts | 3 |
| Lab 3 | Prompt techniques: few-shot, chain-of-thought, self-critique | 4 |
| Lab 4 | Getting JSON your code can rely on | 5 |
| Lab 5 | Function calling, step by step by hand | 6 |
| Lab 6 | Checking whether a prompt actually works | 7 |

**Everything runs locally on `llama3.2:1b` from Week 1.** No cloud account, no API key, no cost.

Every cell does one thing: build a prompt, send it, print the answer. Run them in order and read each
output before moving on. The output *is* the lesson.

## Prerequisites

Week 1 completed: virtual environment created, Ollama installed, `llama3.2:1b` pulled.

Check that Week 1 still works before you start:

```bash
ollama list
ollama run llama3.2:1b "Say hello in one line."
```

If `llama3.2:1b` is listed and answers, you are ready.

## Install the Week 2 dependencies

Week 2 adds `pydantic`, which Lab 4 uses to describe the shape of the data you want back. From the
repository root, with your virtual environment activated:

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

Look for `ollama` and `pydantic` in the list.

## Optional: an Anthropic API key

**Labs 1, 2, 3 and 6 need nothing but Ollama.** Labs 4 and 5 each end with an optional section that
calls Claude instead, so you can see a strong model do the same job. Skip them and the week still
works end to end.

If you do want to run them:

1. Sign up at [console.anthropic.com](https://console.anthropic.com) and create an API key.
2. Copy `.env.example` at the repository root to `.env`.
3. Paste your key into `ANTHROPIC_API_KEY`.

```bash
cp .env.example .env
```

`.env` is git-ignored. **Never commit a key.** In production this same secret lives in AWS Secrets
Manager, Doppler or HashiCorp Vault, which is a Week 6 topic.

### Which model, and why Haiku

Choosing a model is a Week 1 decision, and here you get to make it for real. The current line-up, as
of August 2026:

| Model | What it is for | Context | Input | Output |
|---|---|---|---|---|
| `claude-haiku-4-5` | Fastest, near-frontier intelligence. Speed-critical and high-volume work. | 200k | $1 / MTok | $5 / MTok |
| `claude-sonnet-5` | The best balance of speed and intelligence. | 1M | $2 / MTok | $10 / MTok |
| `claude-opus-5` | Complex agentic coding and enterprise work. Anthropic's suggested default when you are unsure. | 1M | $5 / MTok | $25 / MTok |
| `claude-fable-5` | Most capable. Long-running agents and the hardest reasoning. | 1M | $10 / MTok | $50 / MTok |

MTok means per million tokens. Prices and model ids change, so check
[the pricing page](https://platform.claude.com/docs/en/about-claude/pricing) before you quote them to
anyone.

**These labs use `claude-haiku-4-5`, and the reason is itself the lesson.**

Look at what we are actually asking the model to do: pull three fields out of a three-line resume,
and call one function with one argument. Neither is hard. Running that on Opus would cost five times
the input and five times the output for capability the task cannot use.

So the habit worth forming is this: **pick the cheapest model that clears the bar, not the best one
you can afford.** Notice too that every output price is five times its own input price. A chatty model
on a high-volume endpoint is where budgets actually die, which is worth remembering next time you are
tempted to ask a model to think out loud.

The obvious follow-up question is how you know where the bar is. You measure it. That is Lab 6, and
it is why an eval set is worth building *before* anyone starts arguing about which model to use.

One column to keep half an eye on: Haiku has a 200k context against 1M for the others. Irrelevant
here, where our prompts are a few hundred tokens. It stops being irrelevant in Weeks 3 and 4, when
RAG starts pushing retrieved documents into every single request.

Running both optional sections in this notebook costs a fraction of a cent.

**One thing to be aware of before you run them.** Everything else in this notebook stays on your
machine. Nothing you type leaves it. The moment you call a hosted API, the contents of your prompt,
in these labs a resume, leave your building. That is a real decision with legal and contractual
consequences in a company, and it is worth making it consciously the first time rather than by
accident.

## Run the notebook

Same two options as Week 1. Make sure the virtual environment is activated.

### Option 1: JupyterLab

```bash
jupyter lab
```

Open `week02/week02_labs.ipynb`, then `Kernel > Change Kernel > llmop-course-venv`, and run the
cells in order.

### Option 2: VS Code

Open [the notebook](./week02_labs.ipynb), confirm the interpreter in the top-right corner is the
`venv` from the repository root, and run the cells in order.

## A note on the answers you will get

`llama3.2:1b` is a small model. It is fast and free, which is why we use it, but it is not always
right, and several labs only make sense *because* you can watch a weak model go wrong.

So when your output does not exactly match what the notebook describes, that is normal and expected.
Read what you actually got and ask yourself why. That habit is most of the job.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'ollama'` | Your notebook kernel is not the project `venv`. In JupyterLab use `Kernel > Change Kernel > llmop-course-venv`; in VS Code pick the interpreter from the repository root. |
| `ModuleNotFoundError: No module named 'pydantic'` | Week 2 added it. Re-run `uv pip install -r requirements.txt`, then restart the kernel. |
| `ConnectionError` / `connection refused` on the first cell | Ollama is not running. Start the Ollama app, or run `ollama serve`. |
| `model 'llama3.2:1b' not found` | Run `ollama pull llama3.2:1b`. |
| A cell takes 30+ seconds | Normal on a laptop CPU, especially the first call after Ollama has been idle. It is loading the model. |
| A `NameError` about `EXTRACT`, `result`, `draft_text` or similar | You skipped a cell, or restarted the kernel part way through. Cells build on each other, so run them in order from the top. |
| Lab 2: the model does not say the exact escape-hatch sentence | Expected on a 1B model. It often says "I cannot find that **information** in our policies". Close enough. Lab 4 is where you stop asking politely and constrain the output. |
| Lab 3: the chain-of-thought answer is still wrong | Also expected. Run it a few times. You are looking at the *rate* of correct answers, not a single result. |
| Lab 4 step 1: the JSON parses fine, no code fences | You got lucky this run. Run the cell a few more times and you will see the fences, the "Sure!" preamble, or both. |
| Lab 5: the last cell errors or gives a strange reply | The 1B model is weak at the `tool` role. The message list printed in the cell above it is the part that matters. Week 5 does this properly. |
| Labs 4 and 5, optional cells: `ModuleNotFoundError: No module named 'anthropic'` | Re-run `uv pip install -r requirements.txt`, then restart the kernel. |
| Labs 4 and 5, optional cells: `AuthenticationError` or a missing-key error | No `.env`, or the key was not pasted in. Copy `.env.example` to `.env` at the repository root and restart the kernel so `load_dotenv()` picks it up. |
| Labs 4 and 5, optional cells: `NotFoundError` about the model | The model id moved on. Check the current ids at https://platform.claude.com/docs and update `claude-haiku-4-5`. |
| Lab 5: `tool_use` is not the last content block | Claude sometimes writes a sentence before calling the tool. Print `first.content` to see all the blocks and pick the one whose `type` is `tool_use`. |
| Lab 6: Prompt A answers with a sentence instead of one word | That *is* the finding. A prompt that is hard to score is a prompt that is hard to improve. Note it in your score table. |

## Quick check

You should be able to answer these after this week:

- What are the four message roles, and when do you use each?
- Why does the model not remember your last question, and what does re-sending the history cost you?
- What are the five parts of a good system prompt? Which one stops invented answers?
- When do few-shot examples *hurt*?
- When is chain-of-thought not worth it?
- What is the difference between JSON mode and a schema-enforced output?
- Show me a Pydantic schema you would use to extract structured data from a resume.
- In the function-calling loop, who runs the function, the model or your code?
- How would you check whether a prompt change made things better or worse?
