import re
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
            "Fed Board":        "https://www.federalreserve.gov/feeds/feds.xml",
            "Fed Board IFDP":   "https://www.federalreserve.gov/feeds/ifdp.xml",
            "FEDS Notes":       "https://www.federalreserve.gov/feeds/feds_notes.xml",
            "NY Fed":           "https://libertystreeteconomics.newyorkfed.org/feed/",
            "SF Fed":           "https://www.frbsf.org/research-and-insights/publications/economic-letter/feed/",
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


# ---------------------------------------------------------------------------
#  Additional research sources (one generic collector per institution)
# ---------------------------------------------------------------------------
EXTRA_SOURCES = {
    # ---- Central banks & international institutions (working papers) ----
    "IMF": [
        "https://www.imf.org/en/Publications/RSS?language=eng&series=IMF%20Working%20Papers",
        "https://www.imf.org/en/Publications/RSS?language=eng&series=Staff%20Discussion%20Notes",
    ],
    "BIS": [
        "https://www.bis.org/doclist/wppubls.rss",
        "https://www.bis.org/doclist/bis_fsi_publs.rss",
    ],
    "Bank of England": ["https://www.bankofengland.co.uk/rss/publications"],
    "Bank of Canada": [
        "https://www.bankofcanada.ca/content_type/working-papers/feed/",
        "https://www.bankofcanada.ca/content_type/staff-analytical-notes/feed/",
        "https://www.bankofcanada.ca/content_type/discussion-papers/feed/",
    ],
    "Reserve Bank of Australia": ["https://www.rba.gov.au/rss/rss-cb-rdp.xml"],
    "World Bank": [
        "https://openknowledge.worldbank.org/server/opensearch/search?format=rss&scope=9&sort=dc.date.issued&sort_direction=desc&query=*",
    ],
    "OECD": ["https://www.oecd.org/en/publications/rss.xml"],
    "CBO": ["https://www.cbo.gov/publications/all/rss.xml"],

    # ---- Think tanks ----
    "CEPR VoxEU": ["https://cepr.org/rss/vox-content"],
    "Peterson Institute": ["https://www.piie.com/rss/update.xml"],
    "Brookings": [
        "https://www.brookings.edu/feed/",
        "https://www.brookings.edu/programs/economic-studies/feed/",
        "https://www.brookings.edu/topic/economy/feed/",
    ],
    "Bruegel": ["https://www.bruegel.org/rss.xml"],
    "Economic Policy Institute": ["https://www.epi.org/feed/"],
    "American Enterprise Institute": ["https://www.aei.org/policy-areas/economics/feed/"],
    "Hoover Institution": ["https://www.hoover.org/rss.xml"],
    "Cato Institute": ["https://www.cato.org/rss/recent-opeds", "https://www.cato.org/rss/working-paper"],
    "Becker Friedman Institute": ["https://bfi.uchicago.edu/feed/"],
    "Tax Foundation": ["https://taxfoundation.org/feed/"],
    "Urban Institute": ["https://www.urban.org/rss.xml"],
    "Mercatus Center": ["https://www.mercatus.org/rss.xml"],
    "Council on Foreign Relations": ["https://www.cfr.org/rss.xml"],
    "Roosevelt Institute": ["https://rooseveltinstitute.org/feed/"],
    "Kiel Institute": ["https://www.ifw-kiel.de/rss.xml"],
    "Equitable Growth": ["https://equitablegrowth.org/feed/"],

    # ---- New working papers across many institutions (RePEc weekly reports) ----
    "RePEc: Monetary Economics": ["http://nep.repec.org/rss/nep-mon.rss.xml"],
    "RePEc: Macroeconomics": ["http://nep.repec.org/rss/nep-mac.rss.xml"],
    "RePEc: Financial Markets": ["http://nep.repec.org/rss/nep-fmk.rss.xml"],
    "RePEc: Central Banking": ["http://nep.repec.org/rss/nep-cba.rss.xml"],
    "RePEc: Banking": ["http://nep.repec.org/rss/nep-ban.rss.xml"],

    # ---- Preprints ----
    "arXiv (economics & finance)": [
        "http://export.arxiv.org/api/query?search_query=cat:econ.GN+OR+cat:q-fin.GN+OR+cat:q-fin.PM+OR+cat:q-fin.RM"
        "&sortBy=submittedDate&sortOrder=descending&max_results=40",
    ],
}

# Titles that are clearly not research papers
NOT_A_PAPER = re.compile(
    r"\b(press release|speech|remarks|podcast|webinar|event|testimony|interview|video|newsletter|"
    r"statement|op-ed|opinion|commentary|q&a|agenda|minutes|annual report|job|vacancy)\b", re.I)

# ---------------------------------------------------------------------------
#  Journals and working-paper series via OpenAlex (a free index of research)
# ---------------------------------------------------------------------------
JOURNAL_ISSNS = {
    "0002-8282": "American Economic Review",
    "0033-5533": "Quarterly Journal of Economics",
    "0022-3808": "Journal of Political Economy",
    "0012-9682": "Econometrica",
    "0034-6527": "Review of Economic Studies",
    "0022-1082": "Journal of Finance",
    "0304-405X": "Journal of Financial Economics",
    "0893-9454": "Review of Financial Studies",
    "0304-3932": "Journal of Monetary Economics",
    "1945-7707": "AEJ: Macroeconomics",
    "0895-3309": "Journal of Economic Perspectives",
    "0007-2303": "Brookings Papers on Economic Activity",
    "2041-4161": "IMF Economic Review",
    "0022-2879": "Journal of Money, Credit and Banking",
    "0015-198X": "Financial Analysts Journal",
    "0095-4918": "Journal of Portfolio Management",
}
SERIES_ISSNS = {
    "1018-5941": "IMF",          # IMF Working Papers
    "1813-9450": "World Bank",   # Policy Research Working Papers
}


class OpenAlexCollector(BaseCollector):
    source_name = "Journals & working paper series"

    def __init__(self, lookback_days=14):
        super().__init__(lookback_days)
        self.days = lookback_days

    def collect(self) -> list[Paper]:
        papers = []
        today = datetime.date.today()
        start = today - datetime.timedelta(days=self.days)
        for issns, is_journal in ((JOURNAL_ISSNS, True), (SERIES_ISSNS, False)):
            url = "https://api.openalex.org/works"
            params = {
                "filter": f"primary_location.source.issn:{'|'.join(issns)},"
                          f"from_publication_date:{start},to_publication_date:{today}",
                "sort": "publication_date:desc",
                "per-page": 100,
            }
            try:
                r = requests.get(url, params=params, timeout=30, headers={"User-Agent": "research-paper-digest"})
                r.raise_for_status()
                results = r.json().get("results", [])
            except Exception as e:
                logger.warning(f"OpenAlex failed: {e}")
                continue
            for w in results:
                title = (w.get("title") or "").strip()
                if not title or w.get("type") not in ("article", "preprint", "report", "review"):
                    continue
                src = ((w.get("primary_location") or {}).get("source") or {})
                name = None
                for i in src.get("issn") or []:
                    name = name or issns.get(i)
                name = name or src.get("display_name") or "Journal"
                inv = w.get("abstract_inverted_index") or {}
                words = sorted((pos, word) for word, poss in inv.items() for pos in poss)
                abstract = " ".join(word for _, word in words)
                authors = ", ".join(a["author"]["display_name"] for a in (w.get("authorships") or [])[:6] if a.get("author"))
                papers.append(Paper(
                    title=title,
                    authors=authors,
                    source=f"{name} (journal)" if is_journal else name,
                    url=w.get("doi") or (w.get("primary_location") or {}).get("landing_page_url") or w.get("id", ""),
                    published=w.get("publication_date", ""),
                    abstract=abstract[:2000],
                ))
        return papers


FEED_REPORT: list = []


class FeedCollector(BaseCollector):
    """Generic collector: one institution, one or more feeds."""

    def __init__(self, name, urls, lookback_days=7):
        super().__init__(lookback_days)
        self.source_name = name
        self.urls = urls

    def collect(self) -> list[Paper]:
        papers, seen = [], set()
        for url in self.urls:
            try:
                items = self._parse_rss(url, max_items=40)
            except Exception as e:
                logger.warning(f"{self.source_name} feed failed: {e}")
                items = []
            FEED_REPORT.append(f"{len(items)} {url[:70]}")
            if not items:
                continue
            for item in items:
                if not item["url"] or item["url"] in seen or not item["published"]:
                    continue
                if NOT_A_PAPER.search(item["title"]):
                    continue
                seen.add(item["url"])
                papers.append(Paper(
                    title=" ".join(item["title"].split()),
                    authors=item["authors"],
                    source=self.source_name,
                    url=item["url"],
                    published=item["published"],
                    abstract=(item["summary"] or "")[:2000],
                ))
        return papers


def extra_collectors(lookback_days=7):
    return [FeedCollector(name, urls, lookback_days) for name, urls in EXTRA_SOURCES.items()] + [OpenAlexCollector()]
