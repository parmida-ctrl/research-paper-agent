"""
Digest builder — produces Gmail-compatible email and
interactive browser HTML versions of the paper digest.
"""

import logging

logger = logging.getLogger("papers.digest")

# Gmail-safe colors
TEXT = "#1e293b"
TEXT_MUTED = "#64748b"
TEXT_BRIGHT = "#0f172a"
ACCENT = "#7c3aed"
ACCENT_LIGHT = "#ede9fe"
GREEN = "#059669"
BORDER = "#e2e8f0"
BG_CARD = "#f8fafc"
FONT = "Helvetica, Arial, sans-serif"

CATEGORY_COLORS = {
    "Monetary Policy": "#2563eb",
    "Inflation": "#dc2626",
    "Labor Markets": "#7c3aed",
    "Financial Stability": "#d97706",
    "Asset Pricing": "#059669",
    "Credit Markets": "#0891b2",
    "FX & International": "#0d9488",
    "Fiscal Policy": "#4f46e5",
    "Banking": "#b45309",
    "Other": "#64748b",
}


class DigestBuilder:
    """Builds email and browser versions of the research digest."""

    def build_email(self, summaries, report_date, week_label, total_collected, total_selected):
        papers_html = self._build_email_papers(summaries)
        return self._wrap_email(
            papers_html=papers_html,
            report_date=report_date,
            week_label=week_label,
            total_collected=total_collected,
            total_selected=total_selected,
        )

    def build_browser(self, summaries, report_date, week_label, total_collected, total_selected):
        papers_html = self._build_browser_papers(summaries)
        return self._wrap_browser(
            papers_html=papers_html,
            report_date=report_date,
            week_label=week_label,
            total_collected=total_collected,
            total_selected=total_selected,
        )

    def _build_email_papers(self, summaries):
        parts = []
        for i, paper in enumerate(summaries):
            cat = paper.get("category", "Other")
            cat_color = CATEGORY_COLORS.get(cat, "#64748b")
            cat_icon = paper.get("category_icon", "📄")
            difficulty = paper.get("difficulty", "Intermediate")
            diff_color = {"Accessible": GREEN, "Intermediate": "#d97706", "Technical": "#dc2626"}.get(difficulty, TEXT_MUTED)
            url = paper.get("url", "")
            summary_text = paper.get("summary", "").replace("\n", "<br>")

            parts.append(f'''
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;border:1px solid {BORDER};border-radius:8px;border-left:4px solid {cat_color};overflow:hidden;">
                <tr><td style="padding:18px 20px 4px;">
                    <span style="font-family:{FONT};font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:{cat_color};background:{ACCENT_LIGHT};padding:3px 8px;border-radius:4px;">{cat_icon} {cat}</span>
                    <span style="font-family:{FONT};font-size:10px;color:{diff_color};margin-left:8px;">{difficulty}</span>
                </td></tr>
                <tr><td style="padding:8px 20px 4px;">
                    <a href="{url}" style="font-family:{FONT};font-size:16px;font-weight:700;color:{TEXT_BRIGHT};text-decoration:none;line-height:1.4;">{paper.get("title", "Untitled")}</a>
                </td></tr>
                <tr><td style="padding:2px 20px 8px;">
                    <span style="font-family:{FONT};font-size:12px;color:{TEXT_MUTED};">{paper.get("authors", "")} · {paper.get("source", "")}</span>
                </td></tr>
                <tr><td style="padding:4px 20px 14px;font-family:{FONT};font-size:13px;line-height:1.7;color:{TEXT};">
                    {summary_text}
                </td></tr>
                <tr><td style="padding:0 20px 14px;">
                    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;">
                        <tr><td style="padding:10px 14px;font-family:{FONT};font-size:12px;color:#065f46;">
                            <strong>Key finding:</strong> {paper.get("key_finding", "")}
                        </td></tr>
                    </table>
                </td></tr>
                <tr><td style="padding:0 20px 16px;">
                    <span style="font-family:{FONT};font-size:12px;color:{TEXT_MUTED};font-style:italic;">Market relevance: {paper.get("market_relevance", "")}</span>
                </td></tr>
            </table>''')

        return "\n".join(parts)

    def _build_browser_papers(self, summaries):
        parts = []
        for paper in summaries:
            cat = paper.get("category", "Other")
            cat_color = CATEGORY_COLORS.get(cat, "#64748b")
            cat_icon = paper.get("category_icon", "")
            difficulty = paper.get("difficulty", "Intermediate")
            url = paper.get("url", "")
            summary_text = paper.get("summary", "").replace("\n", "<br>")

            parts.append(f'''
            <div class="paper-card" style="border-left-color: {cat_color}">
                <div class="paper-meta">
                    <span class="paper-category" style="color: {cat_color}">{cat_icon} {cat}</span>
                    <span class="paper-difficulty">{difficulty}</span>
                </div>
                <h3 class="paper-title"><a href="{url}" target="_blank">{paper.get("title", "Untitled")}</a></h3>
                <div class="paper-authors">{paper.get("authors", "")} · {paper.get("source", "")}</div>
                <div class="paper-summary">{summary_text}</div>
                <div class="paper-finding">
                    <strong>Key finding:</strong> {paper.get("key_finding", "")}
                </div>
                <div class="paper-relevance">Market relevance: {paper.get("market_relevance", "")}</div>
            </div>''')

        return "\n".join(parts)

    def _wrap_email(self, **kw):
        return f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f1f5f9;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f1f5f9;">
<tr><td align="center" style="padding:24px 12px;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:660px;background:#ffffff;">

<tr><td align="center" style="padding:36px 28px 28px;border-bottom:2px solid {BORDER};">
    <div style="font-family:{FONT};font-size:11px;letter-spacing:3px;text-transform:uppercase;color:{ACCENT};margin-bottom:12px;">Research Paper Digest</div>
    <div style="font-family:Georgia,serif;font-size:26px;font-weight:400;color:{TEXT_BRIGHT};line-height:1.2;margin-bottom:8px;">{kw["week_label"]}</div>
    <div style="font-family:{FONT};font-size:13px;color:{TEXT_MUTED};">Published {kw["report_date"]} · {kw["total_selected"]} papers selected from {kw["total_collected"]} scanned</div>
</td></tr>

<tr><td style="padding:28px;">
    {kw["papers_html"]}
</td></tr>

<tr><td align="center" style="padding:24px 28px;border-top:1px solid {BORDER};">
    <div style="font-family:{FONT};font-size:11px;color:{TEXT_MUTED};line-height:1.8;">
        Generated by Research Paper Summarizer Agent<br>
        Sources: NBER · Federal Reserve · IMF · BIS · ECB · Bank of England · Bank of Canada · Brookings · PIIE · CEPR · CBO · other think tanks · 16 economics and finance journals · arXiv
    </div>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>'''

    def _wrap_browser(self, **kw):
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Research Paper Digest — {kw["week_label"]}</title>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
    --bg: #0f172a;
    --card: #1e293b;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --text-bright: #f8fafc;
    --accent: #8b5cf6;
    --border: #334155;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'DM Sans',sans-serif; background:var(--bg); color:var(--text); line-height:1.7; }}
.container {{ max-width:760px; margin:0 auto; padding:24px 20px 60px; }}
.header {{ text-align:center; padding:48px 20px 40px; border-bottom:1px solid var(--border); margin-bottom:40px; }}
.header .overline {{ font-size:11px; letter-spacing:3px; text-transform:uppercase; color:var(--accent); margin-bottom:14px; }}
.header h1 {{ font-family:'Instrument Serif',serif; font-size:36px; font-weight:400; color:var(--text-bright); margin-bottom:10px; }}
.header .meta {{ font-size:14px; color:var(--text-muted); }}
.paper-card {{ background:var(--card); border:1px solid var(--border); border-left:4px solid var(--accent); border-radius:10px; padding:24px; margin-bottom:24px; }}
.paper-meta {{ margin-bottom:8px; }}
.paper-category {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.8px; }}
.paper-difficulty {{ font-size:11px; color:var(--text-muted); margin-left:12px; }}
.paper-title {{ font-size:18px; font-weight:600; margin-bottom:6px; line-height:1.3; }}
.paper-title a {{ color:var(--text-bright); text-decoration:none; }}
.paper-title a:hover {{ text-decoration:underline; }}
.paper-authors {{ font-size:13px; color:var(--text-muted); margin-bottom:14px; }}
.paper-summary {{ font-size:14px; line-height:1.8; margin-bottom:14px; }}
.paper-finding {{ background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.2); border-radius:8px; padding:12px 16px; font-size:13px; color:#6ee7b7; margin-bottom:10px; }}
.paper-relevance {{ font-size:12px; color:var(--text-muted); font-style:italic; }}
.footer {{ text-align:center; padding:40px; font-size:12px; color:var(--text-muted); border-top:1px solid var(--border); margin-top:20px; }}
@media (max-width:640px) {{ .container {{ padding:16px 14px 40px; }} .paper-card {{ padding:18px; }} }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="overline">Research Paper Digest</div>
        <h1>{kw["week_label"]}</h1>
        <div class="meta">Published {kw["report_date"]} · {kw["total_selected"]} papers selected from {kw["total_collected"]} scanned</div>
    </div>

    {kw["papers_html"]}

    <div class="footer">
        Generated by Research Paper Summarizer Agent<br>
        Sources: NBER · Federal Reserve · IMF · BIS · ECB · Bank of England · Bank of Canada · Brookings · PIIE · CEPR · CBO · other think tanks · 16 economics and finance journals · arXiv
    </div>
</div>
</body>
</html>'''
