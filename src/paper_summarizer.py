"""
Paper summarizer — uses Claude to generate structured summaries
of academic working papers.
"""

import os
import json
import logging

import anthropic

logger = logging.getLogger("papers.summarizer")

SYSTEM_PROMPT = """You are a research analyst at a top asset management firm, summarizing 
academic working papers for a finance professional who is building deep expertise in 
macroeconomics, monetary policy, and financial markets.

For each paper, produce a JSON object with this exact structure:

{
    "title": "Paper title",
    "authors": "Author names",
    "source": "Institution",
    "url": "Paper URL",
    "category": "One of: Monetary Policy, Inflation, Labor Markets, Financial Stability, Asset Pricing, Credit Markets, FX & International, Fiscal Policy, Banking, Other",
    "category_icon": "Emoji matching the category",
    "summary": "2-3 paragraph summary written for a finance professional. First paragraph: what question the paper addresses and why it matters. Second paragraph: methodology and key findings. Third paragraph (if warranted): implications for markets, policy, or investment thinking.",
    "key_finding": "One sentence capturing the single most important takeaway.",
    "market_relevance": "One sentence on why this matters for someone in asset management.",
    "difficulty": "Accessible | Intermediate | Technical"
}

Guidelines:
- Write summaries as if briefing a portfolio manager — clear, precise, no jargon for jargon's sake
- Highlight empirical findings and magnitudes where available
- Connect findings to current market debates when possible
- If the abstract is thin, do your best with available information
- Be honest about limitations or narrow scope
"""


class PaperSummarizer:
    """Summarizes papers via Claude API."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        self.model = "claude-sonnet-4-20250514"

    def summarize_batch(self, papers: list) -> list[dict]:
        """Summarize a batch of papers in a single API call for efficiency."""
        if not papers:
            return []

        user_prompt = self._build_prompt(papers)

        logger.info(f"Sending {len(papers)} papers to Claude for summarization...")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=6000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text

        try:
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            result = json.loads(cleaned)
            if isinstance(result, dict) and "papers" in result:
                return result["papers"]
            elif isinstance(result, list):
                return result
            else:
                return [result]
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            logger.error(f"Raw (first 500): {raw_text[:500]}")
            # Fallback: return basic info
            return [
                {
                    "title": p.title,
                    "authors": p.authors,
                    "source": p.source,
                    "url": p.url,
                    "category": "Other",
                    "category_icon": "📄",
                    "summary": p.abstract[:500] if p.abstract else "Summary unavailable.",
                    "key_finding": "See full paper for details.",
                    "market_relevance": "",
                    "difficulty": "Intermediate",
                }
                for p in papers
            ]

    def _build_prompt(self, papers: list) -> str:
        parts = [
            f"Please summarize the following {len(papers)} working papers.",
            "Return a JSON array of summary objects, one per paper.",
            "Wrap the array in a JSON object: {\"papers\": [...]}",
            "",
        ]
        for i, p in enumerate(papers):
            parts.append(f"{'='*60}")
            parts.append(f"PAPER {i+1}")
            parts.append(f"{'='*60}")
            parts.append(f"Title: {p.title}")
            parts.append(f"Authors: {p.authors}")
            parts.append(f"Source: {p.source}")
            parts.append(f"URL: {p.url}")
            parts.append(f"Published: {p.published}")
            parts.append(f"Abstract/Text:")
            parts.append(p.abstract[:2000] if p.abstract else "(No abstract available)")
            parts.append("")

        return "\n".join(parts)
