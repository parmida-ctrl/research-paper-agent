# 📚 Research Paper Summarizer Agent

Automatically monitors new working papers from top economics and finance research institutions, ranks them by relevance to your interests, summarizes them via Claude, and emails you a weekly digest every Saturday morning.

## Sources

- **NBER** — National Bureau of Economic Research working papers
- **BIS** — Bank for International Settlements research
- **IMF** — International Monetary Fund working papers & blog
- **Federal Reserve** — Papers from the Board + all 12 regional Fed banks
- **ECB** — European Central Bank working papers
- **SSRN** — Social Science Research Network (economics/finance)

## How It Works

1. **Collect** — Pulls new papers from RSS feeds across all sources
2. **Rank** — Scores each paper against your interest profile (monetary policy, inflation, labor markets, financial stability, asset pricing, credit, FX, fiscal policy)
3. **Summarize** — Claude reads the top 12 papers and writes 2-3 paragraph summaries with key findings and market relevance
4. **Email** — Sends a clean digest to your inbox with an attached interactive HTML version

## Setup

Same pattern as the Market Economist Agent:

1. Create a new GitHub repo (`research-paper-agent`)
2. Push this code
3. Add secrets: `ANTHROPIC_API_KEY`, `SENDGRID_API_KEY`, `REPORT_EMAIL_TO`, `REPORT_EMAIL_FROM`
4. Run from Actions tab

## Cost

~$1-2/month (one Claude API call per week, no FRED or search APIs needed).
