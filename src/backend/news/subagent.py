"""Load the news-analyst subagent from agents/news-analyst/AGENTS.md.

The main agent uses langchain's create_agent, so the subagent is exposed to it
as a single tool (`ask_news_analyst`) that runs its own agent loop.
"""

import os

import yaml
from langchain.agents import create_agent
from langchain.tools import tool

from backend.news import config
from backend.news.tools import NEWS_TOOLS

AGENT_FILE = os.path.join(config.AGENTS_DIR, "news-analyst", "AGENTS.md")


def parse_agent_file(text):
    """Split an AGENTS.md into (frontmatter dict, body). Requires name + description."""
    if not text.startswith("---"):
        raise ValueError("AGENTS.md must start with a '---' YAML frontmatter block")
    _, front, body = text.split("---", 2)
    meta = yaml.safe_load(front) or {}
    missing = [k for k in ("name", "description") if not meta.get(k)]
    if missing:
        raise ValueError(f"AGENTS.md frontmatter missing: {', '.join(missing)}")
    body = body.strip()
    if not body:
        raise ValueError("AGENTS.md has an empty system prompt")
    return meta, body


def load_agent_file(path=AGENT_FILE):
    with open(path, encoding="utf-8") as fh:
        return parse_agent_file(fh.read())


def build_news_subagent_tool(model, path=AGENT_FILE):
    """Create the subagent and wrap it as a tool for the main agent."""
    meta, prompt = load_agent_file(path)
    subagent = create_agent(model=model, tools=NEWS_TOOLS, system_prompt=prompt)

    def ask_news_analyst(question: str) -> str:
        try:
            result = subagent.invoke({"messages": [{"role": "user", "content": question}]})
            return result["messages"][-1].content
        except Exception as exc:
            return f"News analyst error: {exc}"

    ask_news_analyst.__doc__ = (
        " ".join(meta["description"].split())
        + "\n\nArgs:\n    question: The full question, naming the stocks and time window."
    )
    return tool(ask_news_analyst)
