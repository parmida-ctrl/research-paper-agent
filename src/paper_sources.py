"""
Paper source collectors for the Research Paper Summarizer.
Each collector pulls recent working papers from a specific institution.
"""

import os
import logging
import datetime
import hashlib
from dataclasses import dataclass, field
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup
import trafilatura

logger = logging.getLogger("papers.sources")


@dataclass
class Paper:
    """Represents a working paper or research article."""
    title: str
    authors: str
    source: str          # e.g., "NBER", "BIS", "IMF"
    url: str
    published: str
    abstract: str
    full_text: str = ""  # Extracted text (first ~4000 chars)
    topics: list = field(default_factory=list)
    relevance_score: float = 0.0

    @property
    def id(self):
        return hashlib.md5(self.url.encode()).hexdigest()[:12]


class BaseCollector:
    """Base class for paper collectors."""
    source_name = "Unknown"

    def __init__(self, lookback_days=7):
        self.cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=lookback_days)

    def collect(self) -> list[Paper]:
        raise NotImplementedError

    def _parse_rss(self, feed_url, max_items=20) -> list[dict]:
        feed = feedparser.parse(feed_url)
        items = []
        for entry in feed.entries[:max_items]:
            pub_date = self._parse_date(entry)
            if pub_date and pub_date < self.cutoff:
                continue
            summary = entry.get("summary", entry.get("description", ""))
            if summary:
                summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)
            items.append({
                "title": entry.get("title", "Untitled"),
                "url": entry.get("link", ""),
                "published": pub_date.isoformat() if pub_date else "",
                "summary": summary,
                "authors": self._extract_authors(entry),
            })
        return items

    def _parse_date(self, entry) -> Optional[datetime.datetime]:
        for key in ("published_parsed", "updated_parsed"):
            parsed = entry.get(key)
            if parsed:
                try:
                    return datetime.datetime(*parsed[:6], tzinfo=datetime.timezone.utc)
                except Exception:
                    pass
        return None

    def _extract_authors(self, entry) -> str:
        if "authors" in entry:
            return ", ".join(a.get("name", "") for a in entry.authors)
        if "author" in entry:
            return entry.author
        return ""

    def _fetch_abstract(self, url) -> str:
        if not url:
            return ""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(downloaded, include_comments=False)
                return (text or "")[:4000]
        except Exception:
            pass
        return ""


class NBERCollector(BaseCollector):
    """Collects new working papers from NBER."""
    source_name = "NBER"

    def collect(self) -> list[Paper]:
        papers = []
        feed_url = "https://www.nber.org/rss/new.xml"
        items = self._parse_rss(feed_url, max_items=30)

        for item in items:
            abstract = item["summary"]
            if not abstract or len(abstract) < 50:
                abstract = self._fetch_abstract(item["url"])

            papers.append(Paper(
                title=item["title"],
                authors=item["authors"],
                source=self.source_name,
                url=item["url"],
                published=item["published"],
                abstract=abstract[:2000],
            ))
        return papers


class BISCollector(BaseCollector):
    """Collects working papers from the Bank for International Settlements."""
    source_name = "BIS"

    def collect(self) -> list[Paper]:
        papers = []
        feeds = [
            "https://www.bis.org/doclist/bis_fsi_publs.rss",
            "https://www.bis.org/doclist/wppub.rss",
        ]
        for feed_url in feeds:
            items = self._parse_rss(feed_url, max_items=15)
            for item in items:
                abstract = item["summary"]
                if not abstract or len(abstract) < 50:
                    abstract = self._fetch_abstract(item["url"])
                papers.append(Paper(
                    title=item["title"],
                    authors=item["authors"],
                    source=self.source_name,
                    url=item["url"],
                    published=item["published"],
                    abstract=abstract[:2000],
                ))

        # Deduplicate
        seen = set()
        unique = []
        for p in papers:
            if p.url not in seen:
                seen.add(p.url)
                unique.append(p)
        return unique


class IMFCollector(BaseCollector):
    """Collects working papers from the IMF."""
    source_name = "IMF"

    def collect(self) -> list[Paper]:
        papers = []
        feeds = [
            "https://www.imf.org/en/Publications/RSS?type=WP",
            "https://www.imf.org/en/Blogs/rss",
        ]
        for feed_url in feeds:
            items = self._parse_rss(feed_url, max_items=15)
            for item in items:
                abstract = item["summary"]
                if not abstract or len(abstract) < 50:
                    abstract = self._fetch_abstract(item["url"])
                papers.append(Paper(
                    title=item["title"],
                    authors=item["authors"],
                    source=self.source_name,
                    url=item["url"],
                    published=item["published"],
                    abstract=abstract[:2000],
                ))

        seen = set()
        unique = []
        for p in papers:
            if p.url not in seen:
                seen.add(p.url)
                unique.append(p)
        return unique


class FedCollector(BaseCollector):
    """Collects research papers from Federal Reserve banks."""
    source_name = "Federal Reserve"

    def collect(self) -> list[Paper]:
        papers = []
        feeds = {
            "Fed Board":        "https://www.federalreserve.gov/feeds/feds_workingpapers.xml",
            "NY Fed":           "https://libertystreeteconomics.newyorkfed.org/feed/",
            "SF Fed":           "https://www.frbsf.org/research-and-insights/publications/economic-letter/feed/",
            "St. Louis Fed":    "https://fredblog.stlouisfed.org/feed/",
            "Atlanta Fed":      "https://www.atlantafed.org/rss/macroblog",
            "Chicago Fed":      "https://www.chicagofed.org/rss/publications",
            "Dallas Fed":       "https://www.dallasfed.org/rss/ecod.aspx",
            "Cleveland Fed":    "https://www.clevelandfed.org/rss/economic-commentary",
            "Richmond Fed":     "https://www.richmondfed.org/rss/publications",
            "Kansas City Fed":  "https://www.kansascityfed.org/rss/research/",
            "Boston Fed":       "https://www.bostonfed.org/rss/publications",
            "Minneapolis Fed":  "https://www.minneapolisfed.org/rss/publications",
            "Philadelphia Fed": "https://www.philadelphiafed.org/rss/publications",
        }
        for label, feed_url in feeds.items():
            try:
                items = self._parse_rss(feed_url, max_items=10)
                for item in items:
                    abstract = item["summary"]
                    if not abstract or len(abstract) < 50:
                        abstract = self._fetch_abstract(item["url"])
                    papers.append(Paper(
                        title=item["title"],
                        authors=item["authors"],
                        source=f"{self.source_name} ({label})",
                        url=item["url"],
                        published=item["published"],
                        abstract=abstract[:2000],
                    ))
            except Exception as e:
                logger.warning(f"Fed feed '{label}' failed: {e}")

        seen = set()
        unique = []
        for p in papers:
            if p.url not in seen:
                seen.add(p.url)
                unique.append(p)
        return unique


class ECBCollector(BaseCollector):
    """Collects working papers from the ECB."""
    source_name = "ECB"

    def collect(self) -> list[Paper]:
        papers = []
        feeds = [
            "https://www.ecb.europa.eu/rss/wppub.html",
            "https://www.ecb.europa.eu/rss/press.html",
        ]
        for feed_url in feeds:
            try:
                items = self._parse_rss(feed_url, max_items=15)
                for item in items:
                    abstract = item["summary"]
                    if not abstract or len(abstract) < 50:
                        abstract = self._fetch_abstract(item["url"])
                    papers.append(Paper(
                        title=item["title"],
                        authors=item["authors"],
                        source=self.source_name,
                        url=item["url"],
                        published=item["published"],
                        abstract=abstract[:2000],
                    ))
            except Exception as e:
                logger.warning(f"ECB feed failed: {e}")

        seen = set()
        unique = []
        for p in papers:
            if p.url not in seen:
                seen.add(p.url)
                unique.append(p)
        return unique


class SSRNCollector(BaseCollector):
    """Collects recent finance/economics papers from SSRN via RSS."""
    source_name = "SSRN"

    def collect(self) -> list[Paper]:
        papers = []
        # SSRN provides RSS for specific networks
        feeds = [
            "https://papers.ssrn.com/sol3/Jeljour_results.cfm?form_name=journalBrowse&journal_id=1526269&Network=no&lim=false&npage=1&SortOrder=ab_approval_date&stype=desc&output_format=rss20",  # Monetary Economics
        ]
        for feed_url in feeds:
            try:
                items = self._parse_rss(feed_url, max_items=20)
                for item in items:
                    papers.append(Paper(
                        title=item["title"],
                        authors=item["authors"],
                        source=self.source_name,
                        url=item["url"],
                        published=item["published"],
                        abstract=item["summary"][:2000] if item["summary"] else "",
                    ))
            except Exception as e:
                logger.warning(f"SSRN feed failed: {e}")
        return papers
