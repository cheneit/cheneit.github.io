#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, re, sys, html
from urllib.parse import urlparse, urljoin
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import feedparser, httpx

ASIA_TAIPEI = ZoneInfo("Asia/Taipei")
PRIMARY_WINDOW_DAYS = 3
FALLBACK_WINDOW_DAYS = 14

with open("data/sources.json","r",encoding="utf-8") as f:
    SOURCES = json.load(f)

client = httpx.Client(timeout=25)
UA = {"User-Agent": "organic-chem-feeds/1.0 (+github actions)"}

def log(*a): print("[build]", *a, file=sys.stderr)
def iso(dt): return dt.astimezone(timezone.utc).isoformat() if isinstance(dt, datetime) else dt

DOI_PAT   = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
TAG_PAT   = re.compile(r"<[^>]+>")
DATE_KEYS = ["dc_date","date","prism_publicationdate","prism_publicationDate","issued","dc_issued"]

def ensure_https(u):
    if not u: return u
    if u.startswith("//"): return "https:" + u
    if u.startswith("http://"): return "https://" + u[7:]
    return u

def _strip_authors_prefix(text, authors):
    s = text.lstrip()
    if not re.match(r'^(?:authors?|author\(s\))\s*:', s, re.I):
        return text
    last_end = -1
    low = s.lower()
    for name in (authors or []):
        nm = (name or "").strip()
        if not nm: continue
        pos = low.find(nm.lower())
        if 0 <= pos < 300:
            last_end = max(last_end, pos + len(nm))
    if last_end > 0:
        rest = s[last_end:]
        rest = re.sub(r'^[\s,.;:–—-]*(?:and)?\s*', '', rest, flags=re.I)
        return rest
    m = re.search(r'\.\s+| {2,}', s)
    return s[m.end():] if m else s

def clean_summary(raw, authors=None, src_key=""):
    s = raw or ""
    if isinstance(s, dict): s = s.get("value") or ""
    if isinstance(s, list) and s: s = s[0].get("value") or ""
    s = TAG_PAT.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = _strip_authors_prefix(s, authors or [])
    s = re.sub(r'^\s*DOI:\s*\S+\s*', '', s, flags=re.I)
    s = re.sub(r'\s*\[[^]]+\]\s*$', '', s)
    return s

def extract_doi(entry):
    for k in ("prism_doi","doi","dc_identifier","id"):
        v = entry.get(k)
        if isinstance(v, str):
            m = DOI_PAT.search(v)
            if m: return m.group(0)
    for k in ("summary","summary_detail","content"):
        v = entry.get(k)
        if isinstance(v, dict): v = v.get("value")
        if isinstance(v, list) and v: v = v[0].get("value")
        if isinstance(v, str):
            m = DOI_PAT.search(v)
            if m: return m.group(0)
    for L in entry.get("links", []):
        href = L.get("href", "") or ""
        m = DOI_PAT.search(href)
        if m: return m.group(0)
    link = entry.get("link", "") or ""
    m = DOI_PAT.search(link)
    return m.group(0) if m else None

def parse_date(entry):
    for k in ("updated_parsed","published_parsed","created_parsed"):
        t = entry.get(k)
        if t: return datetime(*t[:6], tzinfo=timezone.utc)
    for k in ("updated","published","created"):
        s = entry.get(k)
        if isinstance(s,str):
            try: return datetime.fromisoformat(s.replace("Z","+00:00"))
            except Exception: pass
    for k in DATE_KEYS:
        v = entry.get(k)
        if isinstance(v, dict): v = v.get("value")
        if isinstance(v, list) and v: v = v[0].get("value")
        if isinstance(v, str):
            try:
                if len(v) == 10:
                    return datetime.fromisoformat(v + "T00:00:00+00:00")
                return datetime.fromisoformat(v.replace("Z","+00:00"))
            except Exception: pass
    return None

def fetch_feed(url):
    return feedparser.parse(client.get(url, headers=UA).text)

def canon_link(raw_link, feed_url, doi):
    if raw_link and re.match(r"^https?://", raw_link): return raw_link
    if raw_link and raw_link.startswith("//"):         return "https:" + raw_link
    if raw_link:
        p = urlparse(feed_url); base = f"{p.scheme}://{p.netloc}/"
        return urljoin(base, raw_link)
    if doi: return "https://doi.org/" + doi
    return ""

# -------- Main --------
now_local = datetime.now(ASIA_TAIPEI)
now_utc = now_local.astimezone(timezone.utc)

items_raw = []
seen = set()
def seen_key(doi, link):
    if doi: return ("doi", doi.lower())
    return ("link", (link or "").lower())

for src in SOURCES:
    key, journal = src["key"], src["journal"]
    feeds = []
    if src.get("recent"): feeds.append(("published", src["recent"]))

    for typ, feed_url in feeds:
        try:
            fp = fetch_feed(feed_url)
        except Exception as e:
            log("feed fetch failed:", key, feed_url, e); continue

        fallback_idx = 0
        for e in fp.entries[:200]:
            dt = parse_date(e)
            if not dt:
                dt = now_utc - timedelta(hours=fallback_idx); fallback_idx += 1

            doi = extract_doi(e)
            raw = e.get("link") or (e.get("links",[{}])[0].get("href") if e.get("links") else "")
            link = canon_link(raw, feed_url, doi)

            s_key = seen_key(doi, link)
            if s_key in seen: continue
            seen.add(s_key)

            title   = html.unescape(e.get("title","" )).strip()
            authors = []
            if isinstance(e.get("authors"), list):
                for a in e["authors"]:
                    nm = a.get("name") or ((a.get("given","")+" "+a.get("family","")).strip())
                    if nm: authors.append(nm)
            elif e.get("author"): authors = [e["author"]]

            raw_summary = e.get("summary") or (e.get("content",[{}])[0].get("value") if e.get("content") else "" )
            summary = clean_summary(raw_summary, authors, key)

            item = {
                "journalKey": key,
                "journal": journal,
                "journalShort": src.get("short", key),
                "type": typ,
                "title": title,
                "authors": authors,
                "date": iso(dt),
                "link": ensure_https(link),
                "doi": doi,
                "summary": summary
            }
            items_raw.append((dt, item))

def filter_by_days(pairs, days):
    cutoff = now_utc - timedelta(days=days)
    return [it for dt, it in pairs if dt >= cutoff]

items = filter_by_days(items_raw, PRIMARY_WINDOW_DAYS)
window_days = PRIMARY_WINDOW_DAYS
if not items:
    items = filter_by_days(items_raw, FALLBACK_WINDOW_DAYS)
    window_days = FALLBACK_WINDOW_DAYS

items.sort(key=lambda x: x["date"], reverse=True)
with open("data/articles.json","w",encoding="utf-8") as f:
    json.dump({"generatedAt": iso(now_utc), "windowDays": window_days, "items": items}, f, ensure_ascii=False, indent=2)

log("done. items =", len(items), "windowDays =", window_days)
