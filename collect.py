#!/usr/bin/env python3
"""Collect free public signals and generate the static dashboard data."""
import datetime as dt
import html
import json
import math
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
NOW = dt.datetime.now(dt.timezone.utc)
TODAY = NOW.date().isoformat()
UA = "OpportunityRadar/0.1 (personal research dashboard; public feed reader)"

RELEVANCE = re.compile(r"\b(ai|agent|automation|api|saas|software|tool|platform|marketplace|lead|agency|client|customer|service|sell|selling|revenue|profit|income|business|contract|freelance|creator|affiliate|newsletter|data|directory|local)\b", re.I)
HYPE = re.compile(r"\b(get rich|overnight|guaranteed|passive income|signals group|pump|10000.{0,12}(day|week)|course.{0,20}(buy|sale)|betting lock|airdrop)\b", re.I)
MECHANISM = re.compile(r"\b(ai|agent|automation|api|saas|software|tool|platform|marketplace|lead|agency|service|affiliate|newsletter|data|directory|contract|creator)\b", re.I)
EXECUTION = re.compile(r"\b(sell|selling|made|make|revenue|profit|income|launched|launch|client|customer|signed|charge|charging|paid|offer|offering)\b", re.I)
LOW_SIGNAL = re.compile(r"(^\s*\[for hire\]|can somebody help|how do i (make|find|start)|looking for (a |some )?(side hustle|work|job)|what side hustle|need a side hustle|do you think|job ideas|amazon affiliate program|can't tell you how to|medical resident.*side hustle|almost got beaten up)", re.I)
STOP = set("a an and are as at be by for from how in is it of on or that the this to with you your new make money business people using sell service".split())
SOURCE_WEIGHT = {"Hacker News": 1.0, "Reddit": 0.8, "RSS / YouTube": 0.7}

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, application/atom+xml, application/rss+xml, text/xml"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read()

def clean(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()

def tokens(text):
    value = text.lower()
    words = {word for word in re.findall(r"[a-z][a-z0-9-]{2,}", value) if word not in STOP}
    # Small, explainable concept bridges for the MVP. Replace with embeddings only after
    # the dashboard proves useful enough to justify their operational complexity.
    bridges = {"voice-agent": r"(ai\s+receptionist|phone\s+answering|voice\s+agent|answering\s+bot)",
               "home-services": r"\b(plumb\w*|hvac|electrician|roofing)\b",
               "local-leads": r"(lead\s+gen|local\s+lead|appointment\s+setting)",
               "creator-video": r"(short[ -]form\s+video|ugc|video\s+ads?)"}
    words.update(label for label, pattern in bridges.items() if re.search(pattern, value))
    return words

def category(text):
    value = text.lower()
    if re.search(r"\b(ai|agent|automation|llm)\b", value): return "AI-enabled service"
    if re.search(r"\b(sa[a]?s|api|software|micro)\b", value): return "Software / micro-SaaS"
    if re.search(r"\b(lead|agency|client|local)\b", value): return "Lead generation / agency"
    if re.search(r"\b(creator|youtube|newsletter|affiliate)\b", value): return "Creator monetization"
    if re.search(r"\b(data|directory|marketplace|platform)\b", value): return "Data / marketplace"
    return "Service business"

def collect_reddit(names):
    items = []
    for name in names:
        try:
            root = ET.fromstring(fetch(f"https://www.reddit.com/r/{name}/new/.rss?limit=75"))
            ns = {"a": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("a:entry", ns):
                title = clean(entry.findtext("a:title", default="", namespaces=ns))
                content = clean(entry.findtext("a:content", default="", namespaces=ns))
                link = next((node.attrib.get("href") for node in entry.findall("a:link", ns) if node.attrib.get("href", "").startswith("http")), "")
                published = entry.findtext("a:published", default=NOW.isoformat(), namespaces=ns)
                items.append({"id": "reddit:" + entry.findtext("a:id", default=link, namespaces=ns), "source": "Reddit", "source_detail": "r/" + name, "title": title, "text": content, "url": link, "published": published, "engagement": 0})
        except Exception as error:
            print(f"Reddit r/{name}: {error}")
    return items

def collect_hn():
    items = []
    try:
        ids = json.loads(fetch("https://hacker-news.firebaseio.com/v0/newstories.json"))[:120]
        for item_id in ids:
            try:
                item = json.loads(fetch(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"))
                if item and item.get("type") == "story":
                    items.append({"id": f"hn:{item_id}", "source": "Hacker News", "source_detail": "new stories", "title": clean(item.get("title")), "text": clean(item.get("text", "")), "url": item.get("url") or f"https://news.ycombinator.com/item?id={item_id}", "published": dt.datetime.fromtimestamp(item.get("time", 0), dt.timezone.utc).isoformat(), "engagement": int(item.get("score", 0)) + int(item.get("descendants", 0))})
            except Exception: pass
    except Exception as error:
        print(f"Hacker News: {error}")
    return items

def collect_rss(urls, channels):
    items = []
    urls = list(urls) + [f"https://www.youtube.com/feeds/videos.xml?channel_id={channel}" for channel in channels]
    for url in urls:
        try:
            root = ET.fromstring(fetch(url))
            for entry in root.findall(".//{*}entry") + root.findall(".//item"):
                title = clean(entry.findtext("{*}title", ""))
                link_node = entry.find("{*}link")
                link = (link_node.attrib.get("href", "") if link_node is not None else entry.findtext("{*}link", ""))
                published = entry.findtext("{*}published") or entry.findtext("{*}pubDate") or NOW.isoformat()
                items.append({"id": "rss:" + (entry.findtext("{*}id") or link or title), "source": "RSS / YouTube", "source_detail": url, "title": title, "text": clean(entry.findtext("{*}content", "") or entry.findtext("{*}description", "")), "url": link, "published": published, "engagement": 0})
        except Exception as error:
            print(f"RSS {url}: {error}")
    return items

def viable(items):
    output = []
    seen = set()
    for item in items:
        combined = item["title"] + " " + item["text"]
        if (item["id"] in seen or len(item["title"]) < 15 or item["title"].rstrip().endswith("?") or not RELEVANCE.search(combined)
                or not MECHANISM.search(combined) or not EXECUTION.search(combined)
                or HYPE.search(combined) or LOW_SIGNAL.search(item["title"])): continue
        seen.add(item["id"])
        item["tokens"] = tokens(combined)
        output.append(item)
    return output

def clusters(items):
    groups = []
    for item in sorted(items, key=lambda x: (x["source"] == "Hacker News", x["engagement"]), reverse=True):
        best, best_score = None, 0
        for group in groups:
            union = set().union(*(member["tokens"] for member in group))
            score = len(item["tokens"] & union) / max(1, len(item["tokens"] | union))
            if score > best_score: best, best_score = group, score
        if best is not None and best_score >= 0.22:
            best.append(item)
        else:
            groups.append([item])
    return groups

def clamp(value): return max(0, min(100, round(value)))
def build(groups, old_history):
    result, today_mentions = [], []
    for members in groups:
        representative = max(members, key=lambda x: x["engagement"] + (20 if x["source"] == "Reddit" else 0))
        joined = " ".join(member["title"] + " " + member["text"] for member in members)
        key_words = [word for word, _ in Counter(word for m in members for word in m["tokens"]).most_common(5)]
        fingerprint = " ".join(sorted(key_words[:4])) or representative["id"]
        past = old_history.get(fingerprint, {"first_detected": TODAY, "daily_mentions": []})
        previous = [entry["mentions"] for entry in past.get("daily_mentions", [])[-7:]]
        mentions = len(members)
        avg = sum(previous) / len(previous) if previous else 0
        first = past.get("first_detected", TODAY)
        age = max(0, (dt.date.fromisoformat(TODAY) - dt.date.fromisoformat(first)).days)
        sources = len({member["source"] for member in members})
        engagement = sum(member["engagement"] for member in members)
        novelty = clamp(92 - age * 2 - max(0, mentions - 2) * 4)
        momentum = clamp(28 + (mentions - avg) * 18 + min(25, engagement / 12)) if previous else clamp(35 + mentions * 8 + min(15, engagement / 20))
        source_strength = sum(SOURCE_WEIGHT.get(source, 0.6) for source in {m["source"] for m in members})
        evidence = clamp(16 + source_strength * 18 + min(30, engagement / 15) + (12 if re.search(r"\b(i made|we made|revenue|profit|customer|clients)\b", joined, re.I) else 0))
        saturation = clamp(20 + age * 2 + max(0, mentions - 3) * 6)
        access = 62 if not re.search(r"\b(license|regulated|capital|inventory|real estate)\b", joined, re.I) else 38
        monetization = 65 if re.search(r"\b(sell|client|customer|revenue|profit|service|subscription)\b", joined, re.I) else 38
        score = clamp(.24 * novelty + .23 * momentum + .18 * evidence + .18 * access + .17 * monetization - .14 * saturation)
        lifecycle = "Very Early" if age < 3 and mentions <= 2 else "Accelerating" if momentum >= 65 else "Emerging" if age < 30 else "Mainstream" if saturation < 72 else "Saturated"
        description = representative["title"]
        result.append({"id": fingerprint.replace(" ", "-")[:80], "fingerprint": fingerprint, "opportunity": description, "summary": "Potential signal detected from " + ", ".join(sorted({m["source"] for m in members})) + ". Open the source links and validate the monetization mechanism before acting.", "category": category(joined), "first_detected": first, "mentions_today": mentions, "mentions_7d": sum(previous[-6:]) + mentions, "source_count": sources, "scores": {"momentum": momentum, "novelty": novelty, "saturation": saturation, "evidence": evidence, "accessibility": access, "monetization": monetization, "opportunity": score}, "lifecycle": lifecycle, "why_now": "New or recently accelerating discussion in monitored public communities. This is a hypothesis, not a verified market change.", "evidence_label": "Firsthand / engagement signal" if evidence >= 55 else "Discussion signal only", "sources": [{k: m[k] for k in ("source", "source_detail", "title", "url", "published", "engagement")} for m in members[:8]]})
        today_mentions.append((fingerprint, mentions, first))
    history = old_history.copy()
    for fingerprint, mentions, first in today_mentions:
        entry = history.setdefault(fingerprint, {"first_detected": first, "daily_mentions": []})
        entry["daily_mentions"].append({"date": TODAY, "mentions": mentions})
        entry["daily_mentions"] = entry["daily_mentions"][-365:]
    return sorted(result, key=lambda x: x["scores"]["opportunity"], reverse=True)[:80], history

def main():
    config = json.loads((DATA / "source_config.json").read_text())
    history_path = DATA / "history.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else {}
    raw = collect_reddit(config["subreddits"]) + collect_hn() + collect_rss(config.get("rss_feeds", []), config.get("youtube_channel_ids", []))
    opportunities, new_history = build(clusters(viable(raw)), history)
    (DATA / "history.json").write_text(json.dumps(new_history, indent=2))
    (DATA / "opportunities.json").write_text(json.dumps({"generated_at": NOW.isoformat(), "raw_items_seen": len(raw), "opportunities": opportunities}, indent=2))
    print(f"Generated {len(opportunities)} opportunities from {len(raw)} raw items")

if __name__ == "__main__": main()
