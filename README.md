# Local-LLM-Advisor

[![CI](https://github.com/doorukb/Local-LLM-Advisor/actions/workflows/ci.yml/badge.svg)](https://github.com/doorukb/Local-LLM-Advisor/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A simple, zero-installation terminal script that analyzes your hardware and recommends the best local AI models you can reliably run. You run it, make a few selections, get a detailed report, close the window. No servers, no accounts beyond a free Gemini API key, no trace left behind.

---

## What It Does

Local-LLM-Advisor reads your system hardware automatically, asks you a small set of fixed questions about your preferred inference engine and use case, fetches the current model libraries from Ollama and Hugging Face at runtime, and sends all of that to Gemini 3.1 Flash-Lite. The model reasons over your actual hardware against the current model landscape and returns a structured report telling you exactly what you can run, how fast, and how to run it.

No hardcoded model lists. No stale recommendations. No free-text input surface for the LLM to drift on.

<img width="952" height="559" alt="image" src="https://github.com/user-attachments/assets/ce55ed88-2aba-4f62-9d0a-b07404656252" />

---

## How It Works

**Step 1 - Hardware detection**

On launch, the script reads your system automatically:

- CPU model, core count, thread count
- Total RAM and available RAM
- GPU model and VRAM (via `nvidia-smi` for NVIDIA, `rocm-smi` for AMD, Metal detection on macOS)
- Operating system and architecture

You never type any of this. It is collected programmatically and is not editable.

**Step 2 - Fixed input selections**

A GUI window opens with a small set of dropdown menus and radio buttons:

- **Inference engine**: Ollama / llama.cpp / LM Studio
- **Primary use case**: General chat / Coding assistant / Document Q&A / Creative writing / Summarization
- **Context length preference**: Short (2K-4K) / Medium (8K-16K) / Long (32K+)
- **Performance priority**: Speed (tokens/sec) / Quality (best output at hardware limits) / Balanced

These are the only inputs a user provides. None of them are free-text fields. None of them enter the LLM prompt uncontrolled.

**Step 3 - Live model data fetch**

Before calling Gemini, the script fetches:

- The current Ollama library via the Ollama API (`ollama.com/library`)
- A targeted Hugging Face GGUF model search filtered to the most relevant architecture families

This data is injected into the prompt as context. The LLM reasons over what is actually available right now, not what was in its training data at cutoff. This keeps recommendations current as new models are released without any changes to the codebase.

**Step 4 - Gemini 3.1 Flash-Lite inference**

A fully hardcoded, structured prompt is assembled from the detected hardware, the user's selections, and the fetched model data. The prompt is sent to Gemini 3.1 Flash-Lite using the user's own API key. The prompt instructs the model to return a formatted report and nothing else. There is no conversational loop, no follow-up turns, no free-text channel.

**Step 5 - Report display**

The report appears in a scrollable text box in the same window. It can be saved to a `.txt` file. When the user closes the window, the program exits completely. No background processes, no cached data, no logs written anywhere by default.

---

## Report Contents

The report structure branches on the engine the user selected.

**All engines receive:**

- Ranked list of recommended models with quantization level (e.g., Q4_K_M, Q5_K_S)
- Estimated tokens per second on their hardware for each recommendation
- VRAM / RAM usage estimate per model
- A plain-language explanation of why each model was or was not recommended given the hardware

**Engine-specific sections:**

- **Ollama**: `ollama pull` command for each recommendation, relevant Modelfile parameters to tune for the selected use case, context window flag configuration
- **llama.cpp**: Full `./llama-cli` or `./llama-server` command with relevant flags (`-ngl`, `-c`, `-t`, `--mlock`, etc.), explanation of what each flag does at the user's hardware level, guidance on tuning `n-gpu-layers` specifically for their VRAM
- **LM Studio**: Model search terms to use in LM Studio's discovery panel, recommended loader settings, context and GPU offload configuration guidance

---

## Requirements

- A free Gemini 3.1 Flash-Lite API key from [Google AI Studio](https://aistudio.google.com) (takes under 90 seconds, requires a Google account)
- Internet connection at runtime (for the Gemini call and the live model fetch)
- Python 3.9 or later (only required if using the manual install path)

---

## Setup and Usage

### Quick method (recommended)

**Linux / macOS**

```
curl -fsSL https://raw.githubusercontent.com/doorukb/Local-LLM-Advisor/main/launch.sh | bash
```

**Windows (PowerShell)**

```
irm https://raw.githubusercontent.com/doorukb/Local-LLM-Advisor/main/launch.ps1 | iex
```

That is the entire setup. The script checks for Python, creates an isolated virtual environment, installs dependencies into it, and launches the advisor. On first run you will be prompted to enter your Gemini API key once. You can enter any valid Google Gemini API Key (Google AI Studio key) and the script will automatically route the requests to the free Gemini 3.1 Flash-Lite model, and it will cost absolutely nothing.

The window opens, you make your selections, you get your report, you close the window. The virtual environment is self-contained in a temporary directory and does not affect your global Python installation.

To test a branch before it is merged to `main`, set `LLM_ADVISOR_BRANCH` (for example `config-and-reset`) before running the curl or irm command.

### Manual install (fallback)

For users who prefer not to pipe a remote script to a shell:

```
git clone https://github.com/doorukb/Local-LLM-Advisor
cd Local-LLM-Advisor
pip install -r requirements.txt
python advisor.py
```

### First run and API key

On first run, the script prompts for your Gemini API key and saves it for later runs. The key is sent only to the Gemini API directly from your machine.

**Where the key is stored:**

- **Manual install or local clone** (`./launch.ps1` / `./launch.sh` from a git checkout): `config.json` in the project directory
- **Remote bootstrap** (`curl | bash` or `irm | iex`): a persistent user profile path so the key survives cleanup of the temporary clone
  - Windows: `%APPDATA%\Local-LLM-Advisor\config.json`
  - Linux / macOS: `~/.config/local-llm-advisor/config.json`

To remove the stored key and leave no trace:

**Manual or local clone:**

```
python advisor.py --reset
```

**Remote bootstrap - Linux / macOS:**

```bash
curl -fsSL https://raw.githubusercontent.com/doorukb/Local-LLM-Advisor/main/launch.sh | bash -s -- --reset
```

**Remote bootstrap - Windows (PowerShell):**

```powershell
$launch = Join-Path $env:TEMP "llm-advisor-launch.ps1"
irm https://raw.githubusercontent.com/doorukb/Local-LLM-Advisor/main/launch.ps1 -OutFile $launch
& $launch --reset
```

`--reset` deletes the stored API key and, when launched via the bootstrap scripts, removes the temporary virtual environment. It exits without opening the GUI.

---

## Security and Privacy

Your API key is stored on your machine only - in the project `config.json` for a local clone, or in the user profile paths listed above for remote bootstrap. It is sent directly from your machine to the Gemini API over HTTPS. It is never sent to any intermediate server, never logged, and never included in any telemetry. The project has no telemetry.

Your hardware data is collected locally, assembled into a prompt on your machine, and sent to Gemini as part of the API request. It is not stored anywhere after the window closes.

This project is open source. You can read every line of code that runs. There are no obfuscated network calls.

---

## API Key

This tool is designed specifically for **Gemini 3.1 Flash-Lite** via the Google Generative AI Python SDK. Other Gemini models or other providers are not supported in this version.

On the free tier, Gemini 3.1 Flash-Lite is typically limited to roughly 30 requests per minute, 1,500 requests per day, and 1 million tokens per minute. Limits are set per Google Cloud project (not per API key) and can vary by region and account status - check your active limits in [Google AI Studio](https://aistudio.google.com). Each advisor run uses one request, so personal use stays well within the free tier.

Get a key at: https://aistudio.google.com

---

## License

MIT License. See `LICENSE` for details.
