# Lab 1 (Quickstart)

Repository: https://github.com/utrains/llmops-course

This repository contains Lab 1: a short notebook that demonstrates the "no-memory surprise" when calling a local LLM and how to carry conversation history in your code. All environment and installation/setup instructions are centralized in this README so the notebook stays focused on the lesson.

## Prerequisites

- Linux, macOS, or Windows
- 8 GB RAM (recommended)
- Git
- `uv` CLI (used here to create virtual environments) or any preferred venv tool
- Ollama (local LLM runtime) — install instructions below

## Quickstart (clone, venv, install)

1. Clone the repo and change directory:

```bash
git clone https://github.com/utrains/llmops-course.git
cd llmops-course
```

2. Create a virtual environment using `uv` (example using Python 3.14):

```bash
uv venv venv --python 3.14
```

3. Activate the virtual environment:

- macOS / Linux:
```bash
source venv/bin/activate
```
- Windows (PowerShell):
```powershell
venv\\Scripts\\Activate.ps1
```
- Windows (Git Bash):
```Bash
source venv\\Scripts\\Activate
```

If you encounter any issue while activating the virtual environment, please to the troubleshooting section down below.

4. Install Python dependencies from `requirements.txt`:

```bash
uv pip install -r requirements.txt
```

To verify the requirements installed correctly, run the following command to list the installed packages and look for `ollama` in the list:

```bash
uv pip list
```

## Install & configure Ollama

Follow the platform-specific commands below or visit https://ollama.com for details.

- macOS (Homebrew):
```bash
brew install ollama
brew services start ollama
```

- Linux:
```bash
curl -fsSL https://ollama.com/install.sh | sh
# follow any prompts the installer shows
```

- Windows (PowerShell, run as Administrator):
```powershell
powershell -c "irm https://ollama.com/install.ps1 | iex"
```

Restart the command line and verify Ollama is running:

```bash
ollama --version
```

(Optional) Pull the model used in the lab (`llama3.2:1b`):

```bash
ollama pull llama3.2:1b
ollama list
```

## Test Ollama from the CLI first

Before touching Python, prove the model works from the terminal. This confirms Ollama is installed, the service is running, and the model is loaded.

```bash
ollama run llama3.2:1b "Say hello in one line."
```

Note that The very first time you run a model, Ollama has to load about 1.3 GB of weights from disk into RAM. That can take **30 seconds to 2 minutes** depending on your machine. Subsequent runs are near-instant because the model stays in memory. Give the cell time. If nothing has printed after 3 minutes, see the troubleshooting note further down.

## Run the notebook

Open the notebook for this lab:

- File: `week01/week01_labs.ipynb`

After installing dependencies, register the virtual environment as a notebook kernel (one time):

```bash
python -m ipykernel install --user --name venv --display-name "llmop-course-venv"
```

Then choose one of these two options: JupyterLab or VS Code.

### Option 1: Run in JupyterLab

1. From the repository root with the virtual environment activated, launch JupyterLab:

```bash
jupyter lab
```

2. Open `week01/week01_labs.ipynb`.

3. In the kernel picker, select `llmop-course-venv`.

4. Run cells in order.

### Option 2: Run in VS Code

Before running the first notebook cell in VS Code:

1. Launch VS Code from the repository root:

```bash
code .
```

2. Install the recommended VS Code extensions if they are not already installed.
   - Install the `Python` extension from Microsoft.
   - Install the `Jupyter` extension from Microsoft.

- Open the [notebook file](./week01/week01_labs.ipynb).

4. Select the Python interpreter for the virtual environment you created earlier.
	- In VS Code, open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`).
	- Run `Python: Select Interpreter`.
	- Choose the interpreter from the root folder: `venv/bin/python` 

5. Confirm the notebook kernel is using that same interpreter, then run the first cell.


Notes:

- All environment and Ollama setup instructions live in this `README.md`.
- In the notebook, run cells in order. If the kernel restarts or you changed environments, re-run the setup steps above before running the model-calling cells.


## Troubleshooting

| Symptom | Fix |
|---------|-----|
| A cell says "In [*]" for more than 3 minutes and nothing prints. | Restart the kernel. In VS Code: click the "Restart" icon at the top of the notebook. In JupyterLab: Kernel > Restart Kernel. |
| `ollama.chat(...)` raises `ConnectionRefused`. | The Ollama background service is not running. On Mac open Ollama.app. On Linux run `sudo systemctl start ollama`. On Windows open the Ollama app or reboot. |
| Import error: `No module named 'ollama'`. | You are running the notebook with the wrong Python. Change kernel to your `venv` (top-right corner). If ollama is missing from `venv`, run `uv pip install ollama`. |
| Kernel repeatedly dies mid-run. | Your machine is low on RAM. Close other apps. Make sure no other model is running (`ollama ps` to check, `ollama stop llama3.2:1b` to free memory). |
| Everything looks fine but the model gives nonsense. | Small models (like `llama3.2:1b`) hallucinate more than big ones. That is expected. See the probabilistic note under Step 8. |

If none of the above fixes it, restart Ollama itself:

```
# Mac
brew services restart ollama    # if you installed via brew
# or just Quit and reopen Ollama.app

# Linux
sudo systemctl restart ollama

# Windows PowerShell (as Admin)
Get-Service Ollama | Restart-Service
```

**Error while activating Virtual Environment on Windows**
* Error Message: `.\venv\Scripts\activate : File venv\Scripts\activate.ps1 cannot be loaded because running scripts is disabled on this system. For more information, see about_Execution_Policies at https:/go.microsoft.com/fwlink/?LinkID=135170.`
* Solution : By default script execution is disabled in powershell, you have to enable it using the following command `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`. This command enables the execution policy for the current user. By default, the execution policy for Windows is set to Restricted. You can check the current execution policy by running `Get-ExecutionPolicy`.


