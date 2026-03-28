"""
Paper ranker — scores papers by relevance to user interests
using keyword matching and topic classification.
"""

import logging
import re

logger = logging.getLogger("papers.ranker")


class PaperRanker:
    """Ranks papers by relevance to a defined interest profile."""

    def __init__(self, interests: dict):
        self.primary = [t.lower() for t in interests.get("primary_topics", [])]
        self.secondary = [t.lower() for t in interests.get("secondary_topics", [])]

    def rank(self, papers: list) -> list:
        """Score and sort papers by relevance. Returns sorted list."""
        for paper in papers:
            paper.relevance_score = self._score(paper)

        ranked = sorted(papers, key=lambda p: p.relevance_score, reverse=True)

        # Log top scores for debugging
        for p in ranked[:5]:
            logger.info(f"  Score {p.relevance_score:.1f}: [{p.source}] {p.title[:80]}")

        return ranked

    def _score(self, paper) -> float:
        """Score a paper based on keyword matches in title and abstract."""
        text = f"{paper.title} {paper.abstract}".lower()
        score = 0.0

        # Primary topics: 10 points each
        for topic in self.primary:
            if self._topic_match(topic, text):
                score += 10.0

        # Secondary topics: 5 points each
        for topic in self.secondary:
            if self._topic_match(topic, text):
                score += 5.0

        # Bonus for institutional prestige
        source_bonuses = {
            "NBER": 3.0,
            "BIS": 3.0,
            "IMF": 3.0,
            "ECB": 2.0,
            "Federal Reserve": 2.5,
            "Fed Board": 3.0,
            "NY Fed": 3.0,
        }
        for source_key, bonus in source_bonuses.items():
            if source_key.lower() in paper.source.lower():
                score += bonus
                break

        # Bonus for having a substantial abstract
        if len(paper.abstract) > 500:
            score += 2.0
        elif len(paper.abstract) > 200:
            score += 1.0

        # Penalty for very short or missing abstracts
        if len(paper.abstract) < 50:
            score *= 0.5

        return score

    def _topic_match(self, topic: str, text: str) -> bool:
        """Check if a topic phrase appears in text, with word boundary awareness."""
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(topic) + r'\b'
        return bool(re.search(pattern, text))
