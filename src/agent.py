# v1 research paper summarizer
"""
Research Paper Summarizer Agent
===============================
Monitors new working papers from NBER, BIS, IMF, Fed banks, ECB, and
academic repositories. Filters for relevance, summarizes via Claude,
and emails a weekly digest every Saturday.
"""

import os
import json
import logging
import datetime
from pathlib import Path

from paper_sources import (
    NBERCollector,
    BISCollector,
    IMFCollector,
    FedCollector,
    ECBCollector,
    SSRNCollector,
    extra_collectors,
)
from paper_ranker import PaperRanker
from paper_summarizer import PaperSummarizer
from digest_builder import DigestBuilder
from emailer import DigestEmailer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("papers")


# Topics and keywords that define your research interests
INTEREST_PROFILE = {
    "primary_topics": [
        "monetary policy",
        "interest rates",
        "inflation",
        "price stability",
        "labor markets",
        "employment",
        "financial stability",
        "banking",
        "asset management",
        "equities",
        "bonds",
        "fixed income",
        "financial markets",
    ],
    "secondary_topics": [
        "asset pricing",
        "portfolio theory",
        "credit markets",
        "corporate bonds",
        "credit spreads",
        "foreign exchange",
        "capital flows",
        "international finance",
        "fiscal policy",
        "sovereign debt",
        "government bonds",
        "treasury",
        "yield curve",
        "term structure",
        "central banking",
        "quantitative easing",
        "quantitative tightening",
        "money supply",
        "financial conditions",
        "systemic risk",
        "macroprudential",
        "real estate",
        "housing",
        "commodities",
        "oil prices",
        "emerging markets",
        "exchange rates",
        "balance of payments",
        "trade",
        "recession",
        "business cycle",
        "economic growth",
        "GDP",
        "consumer spending",
        "investment",
        "savings",
        "wealth inequality",
        "fintech",
        "digital currencies",
        "stablecoins",
        "private credit",
        "leveraged lending",
        "market microstructure",
        "volatility",
        "risk premia",
    ],
    "max_papers": 15,
    "max_per_source": 2,
}


def run_pipeline():
    today = datetime.date.today()
    report_date = today.strftime("%B %d, %Y")
    week_label = f"Week of {today.strftime('%B %d, %Y')}"

    logger.info(f"=== Research Paper Summarizer — {report_date} ===")

    # ------------------------------------------------------------------
    # 1  COLLECT papers from all sources
    # ------------------------------------------------------------------
    logger.info("Phase 1: Collecting new papers...")

    collectors = [
        NBERCollector(lookback_days=7),
        BISCollector(lookback_days=7),
        IMFCollector(lookback_days=7),
        FedCollector(lookback_days=7),
        ECBCollector(lookback_days=7),
        SSRNCollector(lookback_days=7),
    ] + extra_collectors(lookback_days=7)

    all_papers = []
    for collector in collectors:
        try:
            papers = collector.collect()
            all_papers.extend(papers)
            logger.info(f"  {collector.source_name}: {len(papers)} papers")
        except Exception as e:
            logger.warning(f"  {collector.source_name} failed: {e}")

    logger.info(f"  Total collected: {len(all_papers)} papers")

    if not all_papers:
        logger.warning("No papers collected — skipping digest")
        return

    # ------------------------------------------------------------------
    # 2  RANK & FILTER by relevance to interests
    # ------------------------------------------------------------------
    logger.info("Phase 2: Ranking papers by relevance...")

    ranker = PaperRanker(interests=INTEREST_PROFILE)
    ranked_papers = ranker.rank(all_papers)
    # Drop duplicates (the same paper can arrive from two feeds)
    seen_urls, seen_titles, unique = set(), set(), []
    for p in ranked_papers:
        key = "".join(c for c in p.title.lower() if c.isalnum())[:70]
        if p.url in seen_urls or key in seen_titles:
            continue
        seen_urls.add(p.url); seen_titles.add(key)
        unique.append(p)

    # Diversify: at most a couple of papers per institution, so no single
    # source (ECB, NBER...) dominates. All Fed banks count as one institution.
    def family(p):
        return "Federal Reserve" if "Federal Reserve" in p.source else p.source

    limit = INTEREST_PROFILE["max_papers"]
    per_source = INTEREST_PROFILE["max_per_source"]
    top_papers, counts = [], {}
    while len(top_papers) < limit and per_source <= limit:
        for p in unique:
            if len(top_papers) >= limit:
                break
            if p in top_papers or p.relevance_score <= 0:
                continue
            if counts.get(family(p), 0) < per_source:
                top_papers.append(p)
                counts[family(p)] = counts.get(family(p), 0) + 1
        per_source += 1  # only loosens if there were not enough papers
    top_papers.sort(key=lambda p: p.relevance_score, reverse=True)

    collected = {}
    for p in all_papers:
        collected[family(p)] = collected.get(family(p), 0) + 1
    print("::notice title=Papers collected per source::" + ", ".join(f"{k} {v}" for k, v in sorted(collected.items())))
    print("::notice title=Papers selected per source::" + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))

    logger.info(f"  Selected top {len(top_papers)} papers")

    # ------------------------------------------------------------------
    # 3  SUMMARIZE via Claude
    # ------------------------------------------------------------------
    logger.info("Phase 3: Summarizing papers via Claude...")

    summarizer = PaperSummarizer()
    summaries = summarizer.summarize_batch(top_papers)

    logger.info(f"  Summarized {len(summaries)} papers")

    # ------------------------------------------------------------------
    # 4  BUILD DIGEST
    # ------------------------------------------------------------------
    logger.info("Phase 4: Building digest...")

    builder = DigestBuilder()
    email_html = builder.build_email(
        summaries=summaries,
        report_date=report_date,
        week_label=week_label,
        total_collected=len(all_papers),
        total_selected=len(top_papers),
    )
    browser_html = builder.build_browser(
        summaries=summaries,
        report_date=report_date,
        week_label=week_label,
        total_collected=len(all_papers),
        total_selected=len(top_papers),
    )

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    (output_dir / f"paper_digest_{today.isoformat()}_email.html").write_text(email_html, encoding="utf-8")
    (output_dir / f"paper_digest_{today.isoformat()}_browser.html").write_text(browser_html, encoding="utf-8")

    # ------------------------------------------------------------------
    # 5  EMAIL
    # ------------------------------------------------------------------
    logger.info("Phase 5: Emailing digest...")

    emailer = DigestEmailer()
    emailer.send(
        subject=f"📚 Research Paper Digest — {week_label}",
        html_body=email_html,


    )

    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    run_pipeline()
