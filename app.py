import html
import inspect
import re
import time

import streamlit as st

from src.agents.agents import (
    build_search_agent,
    build_reader_agent,
    writer_chain,
    critic_chain,
)

# ── Settings you may want to change ──────────────────────────────────────────
APP_NAME = "ResearcherAgent"

# How much of Scout's output Delver sees when choosing a page to read.
READER_CONTEXT_CHARS = 800

# The four agents, in running order. Rename them here and the whole UI follows.
AGENTS = [
    {
        "key": "search",
        "name": "Scout",
        "does": "Finds recent, reliable sources",
        "working": "Searching the web",
        "tab": "Scout's findings",
    },
    {
        "key": "reader",
        "name": "Delver",
        "does": "Reads the best source in full",
        "working": "Reading the top source",
        "tab": "Delver's notes",
    },
    {
        "key": "writer",
        "name": "Scribe",
        "does": "Writes the report",
        "working": "Writing the draft",
        "tab": "Report",
    },
    {
        "key": "critic",
        "name": "Arbiter",
        "does": "Reviews and scores the draft",
        "working": "Reviewing the draft",
        "tab": "Arbiter's review",
    },
]
AGENT = {a["key"]: a for a in AGENTS}

EXAMPLES = [
    "Future of LLMs in the tech industry",
    "Latest AI agents in 2026",
    "Roadmap for AGI development in the next 5 years",
]


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🔎",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ── Styles ───────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&display=swap');

:root {
    --pine:    #0f1a17;   /* page */
    --moss:    #16241f;   /* raised surfaces */
    --fern:    #2a3d35;   /* lines */
    --chalk:   #e9efe6;   /* text */
    --lichen:  #93a79d;   /* quiet text */
    --mark:    #f2b84b;   /* highlighter: progress and actions */
    --mark-ink:#1c1503;   /* text on highlighter */
    --rust:    #e5735c;   /* errors */
    --ui:   'Instrument Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
    --read: 'Newsreader', Georgia, 'Times New Roman', serif;
}

/* ── Base ── */
.stApp { background: var(--pine); color: var(--chalk); }
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp button {
    font-family: var(--ui);
}
#MainMenu, footer, header { visibility: hidden; }
.block-container, [data-testid="stMainBlockContainer"] {
    max-width: 920px;
    padding: 3.5rem 1.5rem 4rem;
}

/* ── Masthead ── */
.wordmark {
    font-family: var(--ui);
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--mark);
    margin-bottom: 1.4rem;
}
.stApp h1.lede {
    font-family: var(--read);
    font-weight: 500;
    font-size: clamp(2rem, 4.6vw, 3.1rem);
    line-height: 1.08;
    letter-spacing: -0.015em;
    color: var(--chalk);
    max-width: 17em;
    margin: 0 0 1rem;
    padding: 0;
}
.sublede {
    font-size: 1.02rem;
    line-height: 1.6;
    color: var(--lichen);
    max-width: 34em;
    margin: 0 0 2.2rem;
}
.sublede b { color: var(--chalk); font-weight: 500; }

/* ── Topic form ── */
[data-testid="stForm"] { border: 0; padding: 0; }
[data-testid="stTextInput"] label p {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--chalk);
}
[data-testid="stTextInputRootElement"],
[data-testid="stTextInput"] [data-baseweb="input"],
[data-testid="stTextInput"] [data-baseweb="base-input"] {
    background: var(--moss);
    border-color: var(--fern);
    border-radius: 10px;
    height: 3rem;
}
[data-testid="stTextInput"] input {
    background: transparent;
    color: var(--chalk);
    font-size: 1.02rem;
    height: 100%;
    padding: 0 0.95rem;
    caret-color: var(--mark);
}
[data-testid="stTextInput"] input::placeholder { color: #6f8279; opacity: 1; }
[data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
    border-color: var(--mark);
    box-shadow: 0 0 0 3px rgba(242, 184, 75, 0.22);
}

[data-testid="stFormSubmitButton"] button {
    width: 100%;
    height: 3rem;
    min-height: 3rem;
    background: var(--mark);
    color: var(--mark-ink);
    border: 0;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.98rem;
    transition: background 0.15s ease;
}
[data-testid="stFormSubmitButton"] button p { color: var(--mark-ink); font-weight: 600; }
[data-testid="stFormSubmitButton"] button:hover { background: #ffd071; color: var(--mark-ink); }
[data-testid="stFormSubmitButton"] button:active { background: #e0a637; color: var(--mark-ink); }
[data-testid="stFormSubmitButton"] button:focus-visible {
    outline: 3px solid var(--chalk);
    outline-offset: 2px;
}

/* ── Example topics (real buttons that fill the box) ── */
.examples-label { font-size: 0.86rem; color: var(--lichen); margin: 0.2rem 0 0.1rem; }
.st-key-examples [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 0.5rem; }
.st-key-examples [data-testid="stColumn"] { flex: 0 1 auto; width: auto; min-width: 0; max-width: 100%; }
.st-key-examples button {
    background: transparent;
    border: 1px solid var(--fern);
    border-radius: 999px;
    padding: 0.3rem 0.9rem;
    min-height: 0;
    height: auto;
    white-space: normal;
    text-align: left;
    color: var(--chalk);
}
.st-key-examples button p { font-size: 0.86rem; color: var(--chalk); }
.st-key-examples button:hover { border-color: var(--mark); background: rgba(242, 184, 75, 0.08); color: var(--chalk); }
.st-key-examples button:focus-visible { outline: 2px solid var(--mark); outline-offset: 2px; }

/* ── The relay: four agents on one line ── */
.relay {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    margin: 2.6rem 0 1.6rem;
    font-family: var(--ui);
}
.stop { position: relative; padding: 1.9rem 1.2rem 0 0; }
.stop::before {                       /* the line to the next agent */
    content: "";
    position: absolute;
    top: 7px; left: 0; right: 0;
    height: 2px;
    background: var(--fern);
}
.stop:last-child::before { display: none; }
.stop-dot {
    position: absolute;
    top: 0; left: 0;
    width: 16px; height: 16px;
    box-sizing: border-box;
    border-radius: 50%;
    background: var(--pine);
    border: 2px solid #4a6257;
}
.stop-name {
    font-family: var(--read);
    font-size: 1.5rem;
    font-weight: 500;
    line-height: 1.15;
    color: var(--lichen);
}
.stop-does  { font-size: 0.86rem; line-height: 1.4; color: var(--lichen); margin-top: 0.25rem; }
.stop-state { font-size: 0.86rem; font-weight: 500; color: #6f8279; margin-top: 0.55rem; }

.stop.is-done::before   { background: var(--mark); }
.stop.is-done .stop-dot { background: var(--mark); border-color: var(--mark); }
.stop.is-done .stop-name { color: var(--chalk); }
.stop.is-done .stop-state { color: var(--lichen); }

.stop.is-active .stop-dot {
    border-color: var(--mark);
    animation: relay-pulse 1.6s ease-out infinite;
}
.stop.is-active .stop-name  { color: var(--chalk); }
.stop.is-active .stop-state { color: var(--mark); }

.stop.is-failed .stop-dot   { background: var(--rust); border-color: var(--rust); }
.stop.is-failed .stop-name  { color: var(--chalk); }
.stop.is-failed .stop-state { color: var(--rust); }

@keyframes relay-pulse {
    0%   { box-shadow: 0 0 0 0 rgba(242, 184, 75, 0.55); }
    100% { box-shadow: 0 0 0 12px rgba(242, 184, 75, 0); }
}
@media (prefers-reduced-motion: reduce) {
    .stop.is-active .stop-dot { animation: none; background: rgba(242, 184, 75, 0.35); }
}
@media (max-width: 640px) {
    .relay { grid-template-columns: 1fr; }
    .stop { padding: 0 0 1.5rem 2rem; }
    .stop::before { top: 8px; bottom: -8px; left: 7px; right: auto; width: 2px; height: auto; }
}

/* ── Results ── */
.stApp h2.results-topic {
    font-family: var(--read);
    font-size: 1.7rem;
    font-weight: 500;
    line-height: 1.2;
    color: var(--chalk);
    margin: 1rem 0 0.2rem;
    padding: 2rem 0 0;
    border-top: 1px solid var(--fern);
}
.empty-note { color: #6f8279; font-size: 0.92rem; margin-top: 0.5rem; }

[data-baseweb="tab-list"] { gap: 1.6rem; border-bottom: 1px solid var(--fern); }
[data-baseweb="tab"] { background: transparent; padding: 0.7rem 0; }
[data-baseweb="tab"] p { font-size: 0.95rem; font-weight: 500; color: var(--lichen); }
[data-baseweb="tab"][aria-selected="true"] p { color: var(--chalk); }
[data-baseweb="tab-highlight"] { background: var(--mark); }
[data-baseweb="tab-border"] { background: transparent; }

.byline { font-size: 0.86rem; color: var(--lichen); margin: 0.8rem 0 0.4rem; }

/* Long-form text is set in the reading face, at a comfortable measure */
.stApp .st-key-report, .stApp .st-key-review, .stApp .st-key-findings, .stApp .st-key-notes {
    background: var(--moss);
    border: 1px solid var(--fern);
    border-radius: 14px;
    padding: 1.8rem 2rem 2rem;
}
.stApp .st-key-report p, .stApp .st-key-report li,
.stApp .st-key-review p, .stApp .st-key-review li {
    font-family: var(--read);
    font-size: 1.12rem;
    line-height: 1.7;
    color: var(--chalk);
    max-width: 68ch;
}
.stApp .st-key-findings p, .stApp .st-key-findings li,
.stApp .st-key-notes p, .stApp .st-key-notes li {
    font-size: 0.95rem;
    line-height: 1.65;
    color: #cfd9d0;
    max-width: 76ch;
}
.stApp .st-key-report h1, .stApp .st-key-report h2, .stApp .st-key-report h3, .stApp .st-key-report h4,
.stApp .st-key-review h1, .stApp .st-key-review h2, .stApp .st-key-review h3, .stApp .st-key-review h4 {
    font-family: var(--read);
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--chalk);
}
.stApp .st-key-report h1 { font-size: 1.9rem; }
.stApp .st-key-report h2, .stApp .st-key-review h2 { font-size: 1.45rem; }
.stApp .st-key-report h3, .stApp .st-key-review h3 { font-size: 1.2rem; }
.stApp .st-key-report a, .stApp .st-key-review a, .stApp .st-key-findings a, .stApp .st-key-notes a {
    color: var(--mark);
    text-underline-offset: 3px;
}
.stApp .st-key-report strong, .stApp .st-key-review strong { color: #ffffff; font-weight: 600; }
.stApp .st-key-report code, .stApp .st-key-review code { background: var(--pine); color: var(--mark); }

[data-testid="stDownloadButton"] button {
    background: transparent;
    border: 1px solid var(--mark);
    border-radius: 10px;
    color: var(--mark);
    font-weight: 600;
    margin-top: 0.6rem;
}
[data-testid="stDownloadButton"] button p { color: var(--mark); font-weight: 600; }
[data-testid="stDownloadButton"] button:hover { background: rgba(242, 184, 75, 0.1); color: var(--mark); }
[data-testid="stDownloadButton"] button:focus-visible { outline: 2px solid var(--chalk); outline-offset: 2px; }

.colophon { color: #6f8279; font-size: 0.82rem; margin-top: 4rem; }
</style>
""",
    unsafe_allow_html=True,
)


# ── Helpers ──────────────────────────────────────────────────────────────────
def stretch(widget) -> dict:
    """Full-width keyword for a button, whichever one this Streamlit version uses."""
    if "width" in inspect.signature(widget).parameters:
        return {"width": "stretch"}
    return {"use_container_width": True}


def as_text(content) -> str:
    """Model output is usually a string, but some models return content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("text"):
                parts.append(block["text"])
        return "\n".join(parts)
    return str(content)


def fmt_seconds(seconds: float) -> str:
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60:02d}s"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "research"


def relay_html(results: dict, timings: dict, active: str = None, failed: str = None) -> str:
    """The four agents on one line, each marked waiting, working, done or failed."""
    stops = []
    for agent in AGENTS:
        key = agent["key"]
        if key == failed:
            cls, state = "is-failed", "Stopped with an error"
        elif key in results:
            took = timings.get(key)
            cls = "is-done"
            state = f"Done in {fmt_seconds(took)}" if took is not None else "Done"
        elif key == active:
            cls, state = "is-active", f"{agent['working']}…"
        else:
            cls, state = "", "Waiting"
        stops.append(
            f'<div class="stop {cls}" role="listitem">'
            f'<span class="stop-dot"></span>'
            f'<div class="stop-name">{html.escape(agent["name"])}</div>'
            f'<div class="stop-does">{html.escape(agent["does"])}</div>'
            f'<div class="stop-state">{html.escape(state)}</div>'
            f"</div>"
        )
    return f'<div class="relay" role="list" aria-live="polite">{"".join(stops)}</div>'


# ── The four steps (same calls as before) ────────────────────────────────────
def run_search(topic: str, results: dict) -> str:
    agent = build_search_agent()
    out = agent.invoke({
        "messages": [
            ("user", f"Find recent, reliable and detailed information about: {topic}")
        ]
    })
    return as_text(out["messages"][-1].content)


def run_reader(topic: str, results: dict) -> str:
    agent = build_reader_agent()
    out = agent.invoke({
        "messages": [(
            "user",
            f"Based on the following search results about '{topic}', "
            f"pick the most relevant URL and scrape it for deeper content.\n\n"
            f"Search Results:\n{results['search'][:READER_CONTEXT_CHARS]}"
        )]
    })
    return as_text(out["messages"][-1].content)


def run_writer(topic: str, results: dict) -> str:
    research = (
        f"SEARCH RESULTS:\n{results['search']}\n\n"
        f"DETAILED SCRAPED CONTENT:\n{results['reader']}"
    )
    return as_text(writer_chain.invoke({"topic": topic, "research": research}))


def run_critic(topic: str, results: dict) -> str:
    return as_text(critic_chain.invoke({"report": results["writer"]}))


STEPS = {
    "search": run_search,
    "reader": run_reader,
    "writer": run_writer,
    "critic": run_critic,
}


def run_pipeline(topic: str, slot) -> None:
    """Run the agents in order, redrawing the relay as each one starts and finishes."""
    ss = st.session_state
    ss.results, ss.timings = {}, {}
    ss.error, ss.failed = None, None
    ss.topic_done = topic

    for agent in AGENTS:
        key = agent["key"]
        slot.markdown(relay_html(ss.results, ss.timings, active=key), unsafe_allow_html=True)
        started = time.perf_counter()
        try:
            ss.results[key] = STEPS[key](topic, ss.results)
        except Exception as exc:  # keep what finished, show what broke
            ss.failed = key
            ss.error = f"{type(exc).__name__}: {exc}"
            break
        ss.timings[key] = time.perf_counter() - started

    slot.markdown(relay_html(ss.results, ss.timings, failed=ss.failed), unsafe_allow_html=True)


def use_example(text: str) -> None:
    st.session_state.topic_input = text


# ── Session state ────────────────────────────────────────────────────────────
ss = st.session_state
ss.setdefault("results", {})
ss.setdefault("timings", {})
ss.setdefault("error", None)
ss.setdefault("failed", None)
ss.setdefault("topic_done", "")


# ── Masthead ─────────────────────────────────────────────────────────────────
names = [f"<b>{html.escape(a['name'])}</b>" for a in AGENTS]
st.markdown(
    f'<div class="wordmark">{html.escape(APP_NAME)}</div>'
    f'<h1 class="lede">Hand over a topic. Get back a report that has already been reviewed.</h1>'
    f'<p class="sublede">{names[0]} searches the web, {names[1]} reads the best source, '
    f"{names[2]} writes the report and {names[3]} reviews it.</p>",
    unsafe_allow_html=True,
)


# ── Topic form (Enter also runs it) ──────────────────────────────────────────
with st.form("ask", border=False):
    col_topic, col_run = st.columns([5, 1.5], vertical_alignment="bottom")
    with col_topic:
        topic = st.text_input(
            "Research topic",
            placeholder="e.g. How are AI agents changing software testing?",
            key="topic_input",
        )
    with col_run:
        submitted = st.form_submit_button("Run research", **stretch(st.form_submit_button))

st.markdown('<p class="examples-label">Or start from an example</p>', unsafe_allow_html=True)
with st.container(key="examples"):
    for col, example in zip(st.columns(len(EXAMPLES)), EXAMPLES):
        col.button(example, key=f"ex_{slugify(example)}", on_click=use_example, args=(example,))

topic_to_run = None
if submitted:
    if topic.strip():
        topic_to_run = topic.strip()
    else:
        st.warning("Enter a topic to research.")


# ── Relay ────────────────────────────────────────────────────────────────────
relay_slot = st.empty()
relay_slot.markdown(
    relay_html(ss.results, ss.timings, failed=ss.failed),
    unsafe_allow_html=True,
)

if topic_to_run:
    run_pipeline(topic_to_run, relay_slot)


# ── Results ──────────────────────────────────────────────────────────────────
results = ss.results

if ss.error:
    st.error(
        f"{AGENT[ss.failed]['name']} stopped before finishing. {ss.error}\n\n"
        "Anything the earlier agents produced is kept below. Run the research again to retry."
    )

if results:
    st.markdown(
        f'<h2 class="results-topic">{html.escape(ss.topic_done)}</h2>',
        unsafe_allow_html=True,
    )

    # Report first, then the review, then the raw material behind them.
    order = ["writer", "critic", "search", "reader"]
    available = [k for k in order if k in results]
    tabs = dict(zip(available, st.tabs([AGENT[k]["tab"] for k in available])))

    if "writer" in tabs:
        with tabs["writer"]:
            st.markdown(
                f'<p class="byline">Written by {AGENT["writer"]["name"]} from '
                f'{AGENT["search"]["name"]}\'s findings and {AGENT["reader"]["name"]}\'s notes.</p>',
                unsafe_allow_html=True,
            )
            with st.container(key="report"):
                st.markdown(results["writer"])
            st.download_button(
                "Download report (.md)",
                data=results["writer"],
                file_name=f"{slugify(ss.topic_done)}-report.md",
                mime="text/markdown",
            )

    if "critic" in tabs:
        with tabs["critic"]:
            st.markdown(
                f'<p class="byline">{AGENT["critic"]["name"]}\'s review of the report.</p>',
                unsafe_allow_html=True,
            )
            with st.container(key="review"):
                st.markdown(results["critic"])

    if "search" in tabs:
        with tabs["search"]:
            st.markdown(
                f'<p class="byline">What {AGENT["search"]["name"]} found on the web, unedited.</p>',
                unsafe_allow_html=True,
            )
            with st.container(key="findings"):
                st.markdown(results["search"])

    if "reader" in tabs:
        with tabs["reader"]:
            st.markdown(
                f'<p class="byline">What {AGENT["reader"]["name"]} pulled from the page it read, unedited.</p>',
                unsafe_allow_html=True,
            )
            with st.container(key="notes"):
                st.markdown(results["reader"])

elif not ss.error:
    st.markdown(
        '<p class="empty-note">The report, the review and each agent\'s raw notes appear here after a run.</p>',
        unsafe_allow_html=True,
    )


# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown(
    f'<p class="colophon">{html.escape(APP_NAME)} runs on LangChain and Streamlit.</p>',
    unsafe_allow_html=True,
)