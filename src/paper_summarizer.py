"""
Paper summarizer: uses Claude to generate structured summaries
of academic working papers, a few papers at a time.
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
- Write summaries as if briefing a portfolio manager: clear, precise, no jargon for jargon's sake
- Highlight empirical findings and magnitudes where available
- Connect findings to current market debates when possible
- If the abstract is thin, do your best with available information
- Be honest about limitations or narrow scope
- Return ONLY the JSON, with no text before or after it
- Inside text values, use single quotes instead of double quotes
"""


class PaperSummarizer:
    """Summarizes papers via Claude API in small batches."""

    def __init__(self, batch_size=4):
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        self.model = "claude-sonnet-5"
        self.batch_size = batch_size

    def summarize_batch(self, papers: list) -> list[dict]:
        results = []
        for i in range(0, len(papers), self.batch_size):
            chunk = papers[i:i + self.batch_size]
            logger.info(f"Summarizing papers {i + 1} to {i + len(chunk)}...")
            results.extend(self._summarize_chunk(chunk))
        return results

    def _summarize_chunk(self, papers: list) -> list[dict]:
        prompt = self._build_prompt(papers)
        for attempt in (1, 2):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=16000,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = "".join(b.text for b in response.content if b.type == "text")
                logger.info(f"  Claude stop reason: {response.stop_reason}")
                parsed = self._parse(raw)
                if parsed:
                    return parsed
                logger.error(f"  Could not read Claude's answer (attempt {attempt}). Start: {raw[:300]}")
            except Exception as e:
                logger.error(f"  Claude call failed (attempt {attempt}): {e}")
        logger.error("  Using backup summaries for this batch")
        return self._fallback(papers)

    def _parse(self, raw: str):
        text = raw.strip()
        for opener, closer in (("{", "}"), ("[", "]")):
            start = text.find(opener)
            end = text.rfind(closer)
            if start == -1 or end <= start:
                continue
            snippet = text[start:end + 1]
            try:
                obj = json.loads(snippet, strict=False)
            except json.JSONDecodeError:
                try:
                    import json_repair
                    obj = json_repair.loads(snippet)
                except Exception:
                    continue
            if not obj:
                continue
            if isinstance(obj, dict) and "papers" in obj:
                return obj["papers"]
            if isinstance(obj, list):
                return obj
            if isinstance(obj, dict):
                return [obj]
        return None

    def _fallback(self, papers: list) -> list[dict]:
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
            "Return a JSON object in this form: {\"papers\": [ ...one summary object per paper... ]}",
            "",
        ]
        for i, p in enumerate(papers):
            parts.append("=" * 60)
            parts.append(f"PAPER {i + 1}")
            parts.append("=" * 60)
            parts.append(f"Title: {p.title}")
            parts.append(f"Authors: {p.authors}")
            parts.append(f"Source: {p.source}")
            parts.append(f"URL: {p.url}")
            parts.append(f"Published: {p.published}")
            parts.append("Abstract/Text:")
            parts.append(p.abstract[:2000] if p.abstract else "(No abstract available)")
            parts.append("")
        return "\n".join(parts)
