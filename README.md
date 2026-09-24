# Opportunity Radar

A private-use, static early-warning dashboard for specific, emerging ways to make money. It collects a small set of public sources nightly, remembers what it saw, filters obvious hype, combines near-duplicate discussions, and publishes `data/opportunities.json` for the dashboard.

## What this MVP does

- Collects new public posts from selected Reddit communities and Hacker News—no API key required.
- Applies relevance and hype filters before scoring.
- Groups related discussions with a deliberately transparent token-similarity method, including a few business-concept bridges (for example, AI receptionist ↔ phone-answering bot). It is a lightweight semantic approximation—not an embedding model.
- Retains daily mention history in `data/history.json`; it never replaces prior history.
- Creates explainable, heuristic scores for novelty, momentum, evidence, accessibility, monetization clarity, saturation, and an overall opportunity score.
- Provides a static dashboard with search, source/category/lifecycle filters, sorting, local watchlisting, and hide/ignore controls.

The scores are triage signals, not measurements of business viability. A first run has no historical baseline, so its momentum and saturation signals are intentionally conservative.

## Source decision for the free MVP

| Source | MVP decision | Why |
| --- | --- | --- |
| Reddit community RSS | Include | Public feeds, early firsthand discussion; substantial noise is filtered. |
| Hacker News API | Include | Official no-auth public API; good for new tools, APIs, and technical business models. |
| YouTube channel RSS | Ready, opt-in | Free feed format, but channels must be curated; titles alone are weak evidence. Add channel IDs in `data/source_config.json`. |
| Curated RSS | Ready, opt-in | Stable feeds can be added one at a time without scraper maintenance. |
| Google Trends | Manual/Phase 2 | Useful confirmation, but no stable public automation is assumed here. |
| Product Hunt | Phase 2 | Its API uses bearer authentication; add only after creating a free developer credential. |
| Indie Hackers | Phase 2 | Do not rely on an undocumented feed or scraper. |
| X / TikTok | Avoid for now | Access and compliance costs/fragility do not justify delaying the MVP. |

Hacker News documents a public, near-real-time Firebase API with no rate limit. Google Trends supports exports but this project deliberately does not automate undocumented endpoints. Product Hunt's API requires bearer authentication. 

## Run locally

```bash
cd opportunity-radar
python3 collect.py
python3 -m http.server 8000
```

Open `http://localhost:8000`. The collector uses only Python's standard library.

## Publish for free with GitHub Pages

1. Create a new **public** GitHub repository named `opportunity-radar`.
2. Upload this folder's contents, preserving `.github/workflows/nightly.yml`.
3. In GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. In the **Actions** tab, run **Collect and publish dashboard** once. Afterwards it runs nightly at 11:15 PM Dallas time (04:15 UTC during CDT; adjust the cron after the seasonal clock change if exact local time matters).
5. Bookmark the Pages URL. It is public but unlisted—do not put personal information into the project.

## Customize sources

Edit `data/source_config.json`. Keep Reddit to communities where people report work, customers, tools, or actual execution. Add a YouTube channel ID only for a creator whose videos are consistently useful; the collector reads the channel's public RSS feed. Add RSS URLs that you have a right to monitor. The job handles a failed feed without losing historical data.

## Feedback and future upgrades

Watchlist and hide/ignore are stored in the browser on the device you use. True cross-device feedback is intentionally deferred to avoid a database and login system. The first upgrades worth considering only after you find signal are: a free Supabase database for shared feedback, an official YouTube API for richer metadata, and paid LLM analysis only for top clusters—not raw posts.

## Guardrails

The collector excludes common get-rich-quick, crypto-pump, course-funnel, and deception terms. It does not treat revenue claims as verified: evidence labels distinguish firsthand reports from speculation. Review original links, legal/regulatory requirements, platform policies, and economics before acting.
