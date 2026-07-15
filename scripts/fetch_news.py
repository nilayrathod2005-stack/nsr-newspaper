#!/usr/bin/env python3
"""
NR TIMES — News Fetcher & Gen-Z Rewriter
Fetches RSS feeds, filters by topic, rewrites in Gen-Z tone, outputs news_data.json
"""

import feedparser
import json
import os
import re
import random
import hashlib
from datetime import datetime, timezone, timedelta
from html import unescape

# ── Configuration ──────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(REPO_ROOT, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "news_data.json")
STATE_FILE = os.path.join(DATA_DIR, "fetcher_state.json")

IST = timezone(timedelta(hours=5, minutes=30))

# ── RSS Feed Sources ───────────────────────────────────────────────────────────

RSS_FEEDS = [
    # LiveMint feeds (verified working)
    {"url": "https://www.livemint.com/rss/markets", "source": "LIVEMINT", "default_cat": "stonks"},
    {"url": "https://www.livemint.com/rss/companies", "source": "LIVEMINT", "default_cat": "stonks"},
    {"url": "https://www.livemint.com/rss/industry", "source": "LIVEMINT", "default_cat": "global"},
    {"url": "https://www.livemint.com/rss/technology", "source": "LIVEMINT", "default_cat": "tech"},
    {"url": "https://www.livemint.com/rss/money", "source": "LIVEMINT", "default_cat": "stonks"},

    # Moneycontrol feeds (verified working)
    {"url": "https://www.moneycontrol.com/rss/marketreports.xml", "source": "MONEYCONTROL", "default_cat": "stonks"},
    {"url": "https://www.moneycontrol.com/rss/business.xml", "source": "MONEYCONTROL", "default_cat": "global"},
    {"url": "https://www.moneycontrol.com/rss/latestnews.xml", "source": "MONEYCONTROL", "default_cat": "global"},

    # ── The Hindu (verified working) ──
    {"url": "https://www.thehindu.com/news/national/?service=rss", "source": "THE HINDU", "default_cat": "politics"},
    {"url": "https://www.thehindu.com/news/international/?service=rss", "source": "THE HINDU", "default_cat": "geopolitics"},
    {"url": "https://www.thehindu.com/opinion/?service=rss", "source": "THE HINDU", "default_cat": "readingcorner"},
    {"url": "https://www.thehindu.com/opinion/editorial/?service=rss", "source": "THE HINDU", "default_cat": "readingcorner"},

    # ── Hindustan Times (verified working) ──
    {"url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "source": "HINDUSTAN TIMES", "default_cat": "politics"},
    {"url": "https://www.hindustantimes.com/feeds/rss/world-news/rssfeed.xml", "source": "HINDUSTAN TIMES", "default_cat": "geopolitics"},
    {"url": "https://www.hindustantimes.com/feeds/rss/opinion/rssfeed.xml", "source": "HINDUSTAN TIMES", "default_cat": "readingcorner"},

    # ── Times of India (verified working) ──
    {"url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "source": "TIMES OF INDIA", "default_cat": "politics"},
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "source": "TIMES OF INDIA", "default_cat": "geopolitics"},

    # ── The Guardian (verified working) ──
    {"url": "https://www.theguardian.com/uk/commentisfree/rss", "source": "THE GUARDIAN", "default_cat": "readingcorner"},
    {"url": "https://www.theguardian.com/world/rss", "source": "THE GUARDIAN", "default_cat": "geopolitics"},

    # ── New York Times (verified working) ──
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/Opinion.xml", "source": "NEW YORK TIMES", "default_cat": "readingcorner"},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "source": "NEW YORK TIMES", "default_cat": "geopolitics"},

    # ── Google News RSS for niche topics ──
    {"url": "https://news.google.com/rss/search?q=aluminium+LME+metals+commodity+price&hl=en-IN&gl=IN&ceid=IN:en", "source": "GOOGLE NEWS", "default_cat": "metal"},
    {"url": "https://news.google.com/rss/search?q=startup+funding+VC+India&hl=en-IN&gl=IN&ceid=IN:en", "source": "GOOGLE NEWS", "default_cat": "vc"},
    {"url": "https://news.google.com/rss/search?q=Indian+stock+market+NIFTY+SENSEX&hl=en-IN&gl=IN&ceid=IN:en", "source": "GOOGLE NEWS", "default_cat": "stonks"},
    {"url": "https://news.google.com/rss/search?q=Formula+1+F1+Grand+Prix&hl=en-IN&gl=IN&ceid=IN:en", "source": "GOOGLE NEWS", "default_cat": "pitlane"},
    {"url": "https://news.google.com/rss/search?q=tennis+ATP+WTA+Grand+Slam&hl=en-IN&gl=IN&ceid=IN:en", "source": "GOOGLE NEWS", "default_cat": "pitlane"},
    {"url": "https://news.google.com/rss/search?q=RBI+SEBI+India+regulation+policy&hl=en-IN&gl=IN&ceid=IN:en", "source": "GOOGLE NEWS", "default_cat": "regulation"},
    {"url": "https://news.google.com/rss/search?q=India+energy+grid+solar+power+electricity&hl=en-IN&gl=IN&ceid=IN:en", "source": "GOOGLE NEWS", "default_cat": "energy"},
    {"url": "https://news.google.com/rss/search?q=India+politics+parliament+Modi+government&hl=en-IN&gl=IN&ceid=IN:en", "source": "GOOGLE NEWS", "default_cat": "politics"},
    {"url": "https://news.google.com/rss/search?q=India+politics+BJP+Congress+state+elections&hl=en-IN&gl=IN&ceid=IN:en", "source": "GOOGLE NEWS", "default_cat": "politics"},
    {"url": "https://news.google.com/rss/search?q=geopolitics+war+NATO+China+Russia+sanctions+diplomacy&hl=en-IN&gl=IN&ceid=IN:en", "source": "GOOGLE NEWS", "default_cat": "geopolitics"},
    {"url": "https://news.google.com/rss/search?q=US+China+trade+war+Middle+East+conflict+Ukraine&hl=en-IN&gl=IN&ceid=IN:en", "source": "GOOGLE NEWS", "default_cat": "geopolitics"},
]

# ── Topic Keyword Maps ─────────────────────────────────────────────────────────

TOPIC_KEYWORDS = {
    "tech": ["tech", "software", "ai ", "artificial intelligence", "startup", "saas", "cloud",
             "semiconductor", "chip", "gadget", "apple", "google", "microsoft", "meta",
             "openai", "nvidia", "computing", "cyber", "digital", "app ", "platform"],
    "energy": ["energy", "solar", "wind", "power", "grid", "electricity", "renewable",
               "coal", "thermal", "nuclear", "ev ", "electric vehicle", "battery", "green hydrogen",
               "adani green", "tata power", "ntpc", "oil", "petroleum", "gas"],
    "stonks": ["stock", "share", "equity", "nifty", "sensex", "bse", "nse", "ipo",
               "bull", "bear", "rally", "crash", "market", "index", "mutual fund",
               "sip", "etf", "portfolio", "dividend", "earnings", "quarter", "q1", "q2", "q3", "q4",
               "profit", "revenue", "target", "buy", "sell", "hold", "upgrade", "downgrade",
               "fii", "dii", "sebi", "listing", "demat"],
    "metal": ["aluminium", "aluminum", "metal", "steel", "copper", "zinc", "nickel",
              "lme", "commodity", "commodities", "gold", "silver", "platinum",
              "mining", "ore", "hindalco", "vedanta", "tata steel", "jsw", "sail",
              "fabrication", "smelter", "foundry"],
    "vc": ["funding", "venture capital", "seed round", "series a", "series b", "series c",
           "unicorn", "startup", "raised", "valuation", "investor", "accelerator",
           "incubator", "vc ", "angel", "pre-seed", "acquisition", "acqui-hire"],
    "regulation": ["rbi", "sebi", "regulation", "policy", "budget", "gst", "tax",
                   "compliance", "law", "act", "bill", "amendment", "circular",
                   "guideline", "norms", "penalty", "fine", "ban", "restriction",
                   "reform", "rate cut", "rate hike", "inflation", "fiscal"],
    "politics": ["politics", "parliament", "lok sabha", "rajya sabha", "modi", "pm ",
                 "prime minister", "bjp", "congress", "aap", "opposition", "coalition",
                 "election", "vote", "constituency", "minister", "cabinet", "governor",
                 "chief minister", "cm ", "political", "party", "government", "bill",
                 "legislation", "supreme court", "high court", "judiciary", "verdict",
                 "rahul gandhi", "amit shah", "nda", "india bloc", "state assembly",
                 "reservation", "protest", "agitation", "strike", "oath", "swearing",
                 "debate", "session", "ordinance", "governor", "president of india"],
    "geopolitics": ["geopolit", "nato", "ukraine", "russia", "china", "taiwan",
                    "middle east", "gaza", "israel", "iran", "sanctions", "diplomacy",
                    "summit", "g7", "g20", "brics", "united nations", "un ",
                    "war", "conflict", "ceasefire", "peace deal", "treaty", "missile",
                    "nuclear", "korea", "pentagon", "white house", "state department",
                    "border", "territory", "sovereignty", "annexation", "invasion",
                    "refugee", "asylum", "migration", "eu ", "european union",
                    "trade war", "tariff", "embargo", "arms deal", "defense pact",
                    "south china sea", "indo-pacific", "quad", "aukus", "asean",
                    "africa", "latin america", "coup", "regime", "election abroad",
                    "trump", "biden", "xi jinping", "putin", "zelensky", "macron"],
    "global": ["global", "world", "us ", "europe", "fed ", "federal reserve",
               "gdp", "recession", "imf", "world bank",
               "forex", "dollar", "euro", "yen", "pound", "crude", "brent", "opec"],
    "readingcorner": ["opinion", "editorial", "column", "op-ed", "commentary",
                      "analysis", "perspective", "viewpoint", "essay", "long read",
                      "deep dive", "explainer", "think piece", "reflection",
                      "book review", "letter to editor", "guest column", "insight"],
    "smartreads": ["book", "read", "feature", "research", "report", "whitepaper",
                   "case study", "data", "survey"],
    "pitlane": ["formula 1", "f1 ", "grand prix", "verstappen", "hamilton", "leclerc",
                "mclaren", "ferrari", "red bull", "mercedes", "qualifying", "race",
                "tennis", "atp", "wta", "wimbledon", "us open", "french open",
                "australian open", "djokovic", "alcaraz", "sinner", "nadal", "federer",
                "roland garros", "grand slam"],
}

# ── Exclusion Keywords (Bollywood / celebrity gossip) ──────────────────────────

EXCLUDE_KEYWORDS = [
    "bollywood", "celebrity", "entertainment", "movie", "film", "actress", "actor",
    "cricket", "ipl", "bcci",  # cricket is not in the interest list
    "gossip", "reality show", "bigg boss", "koffee with", "wedding", "divorce",
]

# ── Polished Newspaper Rewriter (Mint / broadsheet style) ──────────────────────

# Tighten verbose phrases into crisp newspaper English
POLISH_SUBSTITUTIONS = {
    "according to sources": "sources indicate",
    "according to reports": "reports suggest",
    "as per sources": "sources said",
    "it has been reported that": "",
    "it is worth noting that": "",
    "it is important to note that": "",
    "in a move that": "",
    "in a bid to": "to",
    "is expected to": "is likely to",
    "is all set to": "is set to",
    "is going to": "will",
    "has been announced": "was announced",
    "has been launched": "was launched",
    "experts believe that": "analysts expect",
    "experts believe": "analysts expect",
    "market experts say": "market observers note",
    "analysts say that": "analysts say",
    "the company said in a statement": "the company said",
    "the company said in a filing": "the company said in a filing",
    "on a year-on-year basis": "year-on-year",
    "on a quarter-on-quarter basis": "quarter-on-quarter",
    "on a month-on-month basis": "month-on-month",
    "going forward": "ahead",
    "at this point in time": "currently",
    "at the present time": "currently",
    "in the near future": "shortly",
    "due to the fact that": "because",
    "in order to": "to",
    "a total of": "",
    "each and every": "every",
    "absolutely essential": "essential",
    "very significant": "significant",
    "hugely important": "important",
}

# Headlines: strip filler words, tighten phrasing
HEADLINE_TIGHTENERS = {
    "Check Details": "",
    "Here's What You Need To Know": "",
    "Here's what you need to know": "",
    "All You Need To Know": "",
    "All you need to know": "",
    "— Check Details": "",
    "— check details": "",
    "| Check details": "",
    "- Check Details": "",
    "Details Inside": "",
    "details inside": "",
    "Read More": "",
    "WATCH": "",
    "PHOTOS": "",
    "EXPLAINED": "",
    "BREAKING": "",
}


def rewrite_polished(text, is_headline=False):
    """Rewrite text in crisp, polished newspaper English. Never invent facts."""
    if not text:
        return text

    modified = text.strip()

    if is_headline:
        # Remove clickbait suffixes
        for filler, replacement in HEADLINE_TIGHTENERS.items():
            modified = modified.replace(filler, replacement)

        # Clean up trailing punctuation artifacts
        modified = re.sub(r'\s*[|—–-]\s*$', '', modified)
        modified = re.sub(r'\s{2,}', ' ', modified).strip()

        # Ensure headline ends cleanly (no trailing period for headlines)
        if modified.endswith('.'):
            modified = modified[:-1]

    else:
        # Teasers: apply polishing substitutions
        for verbose, concise in POLISH_SUBSTITUTIONS.items():
            pattern = re.compile(re.escape(verbose), re.IGNORECASE)
            if pattern.search(modified):
                if concise:
                    modified = pattern.sub(concise, modified, count=1)
                else:
                    modified = pattern.sub('', modified, count=1)

        # Clean double spaces introduced by removals
        modified = re.sub(r'\s{2,}', ' ', modified).strip()

        # Ensure teaser ends with a period
        if modified and not modified[-1] in '.!?':
            modified += '.'

        # Capitalise first letter after cleanup
        if modified and modified[0].islower():
            modified = modified[0].upper() + modified[1:]

    return modified


# ── Helper Functions ───────────────────────────────────────────────────────────

def clean_html(raw_html):
    """Strip HTML tags and decode entities."""
    if not raw_html:
        return ""
    clean = re.sub(r'<[^>]+>', '', raw_html)
    clean = unescape(clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    # Remove image alt-text artifacts from Moneycontrol
    clean = re.sub(r'^.*?border="0"[^/]*/>\s*', '', clean)
    return clean


def classify_article(title, description):
    """Classify article into a topic category."""
    combined = (title + " " + description).lower()

    # Check exclusions first
    for kw in EXCLUDE_KEYWORDS:
        if kw in combined:
            return None  # excluded

    # Score each topic
    scores = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            scores[topic] = score

    if scores:
        return max(scores, key=scores.get)
    return None  # doesn't match any topic → skip


def make_article_id(url, title):
    """Create a unique ID from URL + title."""
    raw = (url or "") + (title or "")
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def parse_pub_date(entry):
    """Parse publication date from a feed entry."""
    pub = entry.get("published_parsed") or entry.get("updated_parsed")
    if pub:
        try:
            dt = datetime(*pub[:6], tzinfo=timezone.utc)
            return dt.astimezone(IST).isoformat()
        except Exception:
            pass
    # Fallback: use published string
    return entry.get("published", entry.get("updated", datetime.now(IST).isoformat()))


def extract_image(entry):
    """Try to extract an image URL from the feed entry."""
    # media:content
    media = entry.get("media_content", [])
    if media and isinstance(media, list):
        for m in media:
            url = m.get("url", "")
            if url:
                return url

    # media:thumbnail
    thumb = entry.get("media_thumbnail", [])
    if thumb and isinstance(thumb, list):
        for t in thumb:
            url = t.get("url", "")
            if url:
                return url

    # Fallback: extract from description HTML
    desc = entry.get("description", "") or entry.get("summary", "")
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc)
    if img_match:
        return img_match.group(1)

    return ""


def extract_source_from_google_news(entry):
    """Google News wraps articles — extract the real source name."""
    source = entry.get("source", {})
    if isinstance(source, dict):
        return source.get("title", "GOOGLE NEWS").upper()
    # Try from title suffix " - Source Name"
    title = entry.get("title", "")
    if " - " in title:
        parts = title.rsplit(" - ", 1)
        if len(parts) == 2:
            return parts[1].strip().upper()
    return "GOOGLE NEWS"


# ── Main Fetch Logic ──────────────────────────────────────────────────────────

def load_state():
    """Load persisted state (issue number)."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"issueNumber": 0}


def save_state(state):
    """Save state to disk."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def fetch_all_feeds():
    """Fetch all RSS feeds and return raw entries with metadata."""
    all_entries = []
    for feed_cfg in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_cfg["url"])
            if feed.bozo and not feed.entries:
                print(f"  ⚠ Feed error for {feed_cfg['url']}: {feed.bozo_exception}")
                continue
            print(f"  ✓ {feed_cfg['source']}: {len(feed.entries)} items from {feed_cfg['url']}")
            for entry in feed.entries:
                entry["_source_config"] = feed_cfg
            all_entries.extend(feed.entries)
        except Exception as e:
            print(f"  ✗ Failed {feed_cfg['url']}: {e}")
    return all_entries


def process_entries(entries):
    """Process raw feed entries into structured articles."""
    seen_urls = set()
    seen_titles = set()
    articles = []

    for entry in entries:
        cfg = entry.get("_source_config", {})
        is_google = cfg.get("source") == "GOOGLE NEWS"

        # Extract fields
        raw_title = entry.get("title", "").strip()
        raw_link = entry.get("link", "").strip()
        raw_desc = clean_html(entry.get("description", "") or entry.get("summary", ""))

        if not raw_title or not raw_link:
            continue

        # Google News: strip source suffix from title
        display_title = raw_title
        actual_source = cfg.get("source", "UNKNOWN")
        if is_google and " - " in raw_title:
            parts = raw_title.rsplit(" - ", 1)
            display_title = parts[0].strip()
            actual_source = parts[1].strip().upper()

        # Dedup by URL
        if raw_link in seen_urls:
            continue
        seen_urls.add(raw_link)

        # Dedup by title (fuzzy — lowercase first 60 chars)
        title_key = display_title.lower()[:60]
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        # Classify
        category = classify_article(display_title, raw_desc)
        if category is None:
            # Try default category from feed config
            default_cat = cfg.get("default_cat")
            if default_cat:
                # Still check exclusions
                combined = (display_title + " " + raw_desc).lower()
                excluded = any(kw in combined for kw in EXCLUDE_KEYWORDS)
                if not excluded:
                    category = default_cat
            if category is None:
                continue

        # Ensure description isn't too short
        if len(raw_desc) < 20:
            raw_desc = display_title  # use title as fallback teaser

        # Rewrite in polished newspaper English
        polished_headline = rewrite_polished(display_title, is_headline=True)
        polished_teaser = rewrite_polished(raw_desc, is_headline=False)

        # Truncate teaser to ~4 sentences max
        sentences = re.split(r'(?<=[.!?])\s+', polished_teaser)
        if len(sentences) > 4:
            polished_teaser = " ".join(sentences[:4])

        article = {
            "id": make_article_id(raw_link, display_title),
            "headline": polished_headline,
            "teaser": polished_teaser,
            "originalHeadline": display_title,
            "source": actual_source,
            "sourceUrl": raw_link,
            "category": category,
            "timestamp": parse_pub_date(entry),
            "imageUrl": extract_image(entry),
        }
        articles.append(article)

    # Sort by timestamp (newest first)
    articles.sort(key=lambda a: a.get("timestamp", ""), reverse=True)

    return articles


def main():
    print("🗞️  NR TIMES — Fetching news feeds...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load state & increment issue number
    state = load_state()
    state["issueNumber"] = state.get("issueNumber", 0) + 1
    save_state(state)

    # Fetch
    raw_entries = fetch_all_feeds()
    print(f"\n📰 Total raw entries: {len(raw_entries)}")

    # Process
    articles = process_entries(raw_entries)
    print(f"✅ Final articles after filtering: {len(articles)}")

    # Category breakdown
    cat_counts = {}
    for a in articles:
        cat_counts[a["category"]] = cat_counts.get(a["category"], 0) + 1
    for cat, count in sorted(cat_counts.items()):
        print(f"   {cat}: {count}")

    # Write output
    output = {
        "lastUpdated": datetime.now(IST).isoformat(),
        "issueNumber": state["issueNumber"],
        "articles": articles,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved {len(articles)} articles to {OUTPUT_FILE}")
    print(json.dumps({"status": "ok", "count": len(articles), "issue": state["issueNumber"]}))


if __name__ == "__main__":
    main()
