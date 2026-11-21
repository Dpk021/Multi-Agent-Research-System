# ResearcherAgent — Multi-Agent Research System

Hand over a topic. Get back a research report that has already been reviewed.

ResearcherAgent is a small multi-agent pipeline built with **LangChain** and **OpenAI (gpt-4o-mini)**. Four specialised agents run in sequence — one searches the web, one reads the best source in full, one writes a structured report, and one critiques and scores it — wrapped in a **Streamlit** UI that shows each agent's progress and output.

---

## How it works

```
Topic
  │
  ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Scout   │ ─▶ │  Delver  │ ─▶ │  Scribe  │ ─▶ │  Arbiter │
│  search  │    │  reader  │    │  writer  │    │  critic  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
 web_search      scrape_url      LLM chain       LLM chain
 (Tavily)        (trafilatura /  (report)        (score +
                 readability /                   feedback)
                 BeautifulSoup)
```

| Agent | Role | Powered by |
|---|---|---|
| **Scout** (search) | Finds recent, reliable sources and returns titles, URLs and snippets | LangChain `create_agent` + `web_search` tool (Tavily, top 5 results) |
| **Delver** (reader) | Picks the most relevant URL from Scout's findings and scrapes it for deep content | LangChain `create_agent` + `scrape_url` tool |
| **Scribe** (writer) | Writes a structured report: Introduction → Key Findings → Conclusion → Sources | Prompt → `gpt-4o-mini` → `StrOutputParser` |
| **Arbiter** (critic) | Reviews the report and returns a `Score: X/10`, strengths, areas to improve and a one-line verdict | Prompt → `gpt-4o-mini` → `StrOutputParser` |

The `scrape_url` tool tries three extraction strategies in order — **trafilatura** → **readability** → raw **BeautifulSoup** — and returns up to 5,000 characters of clean text, so most article and blog pages extract reliably.

---

## Project structure

```
Multi-Agent-Research-System/
├── app.py                    # Streamlit UI (relay view, tabbed results, report download)
├── main.py                   # CLI entry point — runs the pipeline on a hard-coded topic
├── src/
│   ├── agents/
│   │   └── agents.py         # LLM init, Scout/Delver agent builders, Scribe/Arbiter chains
│   ├── pipelines/
│   │   └── pipeline.py       # run_research_pipeline(topic) — sequential 4-step orchestration
│   └── tools/
│       └── tools.py          # web_search (Tavily) and scrape_url (multi-strategy scraper)
├── .env                      # API keys (not committed)
├── .gitignore
├── LICENSE
└── README.md
```

---

## Getting started

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/Dpk021/Multi-Agent-Research-System.git
cd Multi-Agent-Research-System

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install langchain langchain-openai langchain-core \
            tavily-python streamlit python-dotenv \
            requests beautifulsoup4 readability-lxml trafilatura rich
```

### 3. Add your API keys

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

- OpenAI key: https://platform.openai.com/api-keys
- Tavily key (free tier available): https://app.tavily.com

### 4. Run it

**Streamlit UI (recommended)**

```bash
streamlit run app.py
```

Enter a topic (or click one of the example chips) and press **Run research**. The relay bar shows which agent is working and how long each one took; results appear in tabs — the report first, then Arbiter's review, then Scout's raw findings and Delver's notes. The report can be downloaded as Markdown.

**Command line**

```bash
python main.py
```

Edit the `topic` string in `main.py` to research something else. Each step's output is printed to the terminal.

---

## Using the pipeline in your own code

```python
from src.pipelines.pipeline import run_research_pipeline

state = run_research_pipeline("The impact of AI on the job market in 2027")

print(state["report"])      # the written report
print(state["feedback"])    # the critic's score and review
# also available: state["search_results"], state["scraped_content"]
```

---

## Configuration

A few knobs worth knowing about:

| Where | Setting | Default | What it does |
|---|---|---|---|
| `src/agents/agents.py` | `model` | `gpt-4o-mini` | LLM used by all four agents |
| `src/agents/agents.py` | `temperature` | `0` | Deterministic outputs |
| `src/tools/tools.py` | `max_results` | `5` | Number of Tavily results Scout fetches |
| `src/tools/tools.py` | `[:5000]` | 5,000 chars | Cap on scraped page content |
| `app.py` | `READER_CONTEXT_CHARS` | `800` | How much of Scout's output Delver sees when picking a URL |
| `app.py` | `AGENTS` / `EXAMPLES` | — | Agent names, tab labels and example topics shown in the UI |

---

## Error handling

- If any agent fails mid-run, the UI keeps everything the earlier agents produced, names the agent that stopped, and shows the exception so you can retry.
- `scrape_url` returns a readable message (timeout, HTTP error, extraction failure) instead of raising, so the reader agent can recover or report the problem.

---

## Roadmap / ideas

- Let Delver read the top *N* sources instead of a single URL
- Feed Arbiter's feedback back to Scribe for a revision loop
- Persist run history and let users compare reports
- Swap in other LLM providers via LangChain's model abstraction

---

## License

See [LICENSE](LICENSE).
