# ShipFaster - Agent Automation Engine

ShipFaster is an enterprise-grade developer automation platform that streamlines common coding, testing, documentation, and content delivery workflows. This repository houses the **Agent & Automation (Dev 1)** subsystem, which provides five advanced automation modules orchestrated via a central Python engine and exposed as LLM-callable tools through a **Model Context Protocol (MCP)** server.

---

## 🚀 Key Features & Modules

### 1. Scaffolder
- **Purpose**: Generates template-based project skeletons (currently supports FastAPI).
- **AI Customization**: Generates a rich, highly descriptive `README.md` personalized to your project name and description using an LLM.
- **Output**: Returns a packaged `.zip` archive file.

### 2. Test Generator (Self-Healing Tests)
- **Purpose**: Statically parses python code using **AST (Abstract Syntax Tree)** to discover logical pathways (if/else conditions, try-except blocks, loops).
- **Execution Sandbox**: Calls the LLM to write corresponding `pytest` cases, compiles and runs them inside a subprocess sandbox, captures errors, and automatically prompts the LLM once to correct any failing tests.

### 3. Docs Generator
- **Purpose**: Parses Flask, Django, or FastAPI router files.
- **Output**: Automatically generates an OpenAPI 3.0 specification in YAML format and a comprehensive markdown API Reference Guide.

### 4. Changelog Generator (Automated Release Notes)
- **Purpose**: Groups git commits by Conventional Commit guidelines (`feat`, `fix`, `chore`, `breaking`).
- **SemVer Logic**: Suggests version bumps (Major, Minor, or Patch) based on breaking change detection and writes beautiful markdown release summaries.

### 5. Notebook-to-Blog
- **Purpose**: Converts Jupyter Notebooks (`.ipynb`) into engaging blog narrative documents.
- **Asset Handling**: Extracts base64 plots, saves them locally as static image assets, replaces placeholder references, and restructures code and prose.

---

## 📁 Repository Structure

```text
pydatahackethon/
│
├── engine/
│   ├── core/                  # Mock core client stubs (Dev 3 boundaries)
│   │   ├── models.py          # ModuleResult Pydantic schema (with dataclass fallback)
│   │   ├── llm_client.py      # Dual Gemini / Anthropic API wrapper with mock fallback
│   │   ├── storage.py         # Local simulator for S3 uploads (.temp_artifacts/)
│   │   └── sandbox.py         # Isolated subprocess execution environment for tests
│   │
│   ├── modules/               # Core automation modules
│   │   ├── scaffolder/
│   │   ├── test_generator/
│   │   ├── docs_generator/
│   │   ├── changelog_generator/
│   │   └── notebook_to_blog/
│   │
│   ├── prompts/               # Central repository for prompt templates
│   │   └── ...
│   │
│   ├── mcp/                   # FastMCP server wrapping modules as agent tools
│   │   ├── tools.py           
│   │   └── server.py          
│   │
│   └── tests/                 # Integration test suite
│       └── run_tests.py       
│
├── .temp_artifacts/           # Auto-generated artifact folder (git ignored)
└── README.md
```

---

## 🛠️ Installation & Setup

1. **Navigate to the project root**:
   ```bash
   cd pydatahackethon
   ```

2. **Verify Python Virtual Environment is active**:
   Ensure you are using your project's `.venv` (e.g. `d:\pydata2.0\.venv`).

3. **Install Dependencies**:
   ```bash
   pip install pydantic httpx fastmcp pytest
   ```

4. **Configure Environment API Keys**:
   Set one (or both) of the following environment variables in your environment or local `.env` file:
   ```bash
   # For Google Gemini API (Default/Recommended)
   GEMINI_API_KEY="your-gemini-api-key"

   # For Anthropic Claude API
   ANTHROPIC_API_KEY="your-anthropic-api-key"
   ```

---

## ⚡ How to Run

### 1. Run Verification Test Suite
Executes a simulated run across all 5 modules using the active virtual environment:
```powershell
$env:PYTHONPATH="."
python engine/tests/run_tests.py
```

### 2. Run MCP Server (Stdio Transport)
Launches the server in stdio mode, waiting to accept tool calls from AI clients (such as Claude Desktop or Cursor):
```powershell
$env:PYTHONPATH="."
python -m engine.mcp.server
```

### 3. Run MCP Server (Browser Inspector Mode)
*Requires Node.js/npm installed on the host system:*
```powershell
$env:PYTHONPATH="."
fastmcp dev inspector engine/mcp/server.py
```
This opens the MCP Inspector interface in your browser where you can execute and test tools manually.
