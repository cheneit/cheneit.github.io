#!/usr/bin/env python3
"""Research Library v5.2 metadata updater and historical PDF backfill.

Daily mode refreshes already identifiable records without downloading PDFs.
Backfill mode uses a conservative two-stage pipeline:
1) DOI/arXiv/title matching from index.json;
2) for unresolved records, download/read the first PDF pages and match again.

Only scholarly/citations/review fields are refreshed. A missing v5 paperCard is
initialized once from the first accepted match; an existing paperCard is never
overwritten. Manual title, topics, tags, notes, links and evaluations are safe.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


OPENALEX = "https://api.openalex.org"
CROSSREF = "https://api.crossref.org"
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
ARXIV_RE = re.compile(r"(?:arxiv\s*[:/]?\s*)?(\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v\d+)?", re.I)
GENERIC_TITLE_RE = re.compile(
    r"^(?:paper|article|document|untitled|manuscript|download|fulltext|main|supp|si|sm)[-_\s\d.]*$",
    re.I,
)


def now_ms() -> int:
    return int(time.time() * 1000)


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def clean_doi(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", text, flags=re.I)
    match = DOI_RE.search(text)
    return (match.group(0) if match else text).rstrip(".,;:)]}").lower()


def extract_doi(value: object) -> str:
    match = DOI_RE.search(str(value or ""))
    return clean_doi(match.group(0)) if match else ""


def extract_arxiv(value: object) -> str:
    match = ARXIV_RE.search(str(value or ""))
    return match.group(1) if match else ""


def compact_title(value: object) -> str:
    return re.sub(r"[^\w]+", " ", str(value or "").lower(), flags=re.UNICODE).strip()


def generic_title(value: object) -> bool:
    text = str(value or "").strip()
    return (
        len(text) < 8
        or bool(GENERIC_TITLE_RE.fullmatch(text))
        or bool(re.fullmatch(r"[a-f0-9_-]{12,}", text, flags=re.I))
        or bool(re.fullmatch(r"\d+(?:[-_.]\d+)*", text))
    )


def similarity(a: object, b: object) -> float:
    aa, bb = compact_title(a), compact_title(b)
    if not aa or not bb:
        return 0.0
    return difflib.SequenceMatcher(None, aa, bb).ratio()


def request_json(url: str, retries: int = 3) -> dict:
    mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    if mailto and "api.openalex.org" in url:
        url += ("&" if "?" in url else "?") + "mailto=" + urllib.parse.quote(mailto)
    headers = {"User-Agent": "Research-Library-Metadata-Updater/5.2"}
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=35) as response:
                return json.load(response)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2**attempt)
    raise RuntimeError(f"request failed: {last_error}")


def openalex_work(seed: dict) -> tuple[dict | None, dict]:
    openalex_id = str(seed.get("openAlexId") or "").strip()
    if openalex_id:
        work_id = openalex_id.rstrip("/").split("/")[-1]
        return request_json(f"{OPENALEX}/works/{urllib.parse.quote(work_id)}"), {
            "method": "openalex-id",
            "confidence": 1.0,
        }

    doi = clean_doi(seed.get("doi"))
    if doi:
        encoded = urllib.parse.quote(f"https://doi.org/{doi}", safe="")
        results = request_json(f"{OPENALEX}/works?filter=doi:{encoded}&per_page=1").get("results") or []
        if results:
            return results[0], {"method": "doi-exact", "confidence": 0.99}

    arxiv_id = str(seed.get("arxivId") or "").strip()
    title = str(seed.get("title") or "").strip()
    query = arxiv_id or title
    if not query:
        return None, {"method": "no-query", "confidence": 0.0}
    results = request_json(f"{OPENALEX}/works?search={urllib.parse.quote(query)}&per_page=5").get("results") or []
    if not results:
        return None, {"method": "no-result", "confidence": 0.0}
    ranked = sorted(results, key=lambda work: similarity(title, work.get("title")), reverse=True)
    score = similarity(title, ranked[0].get("title"))
    if arxiv_id:
        return ranked[0], {"method": "arxiv-search", "confidence": max(0.93, score)}
    if score < 0.45:
        return None, {"method": "title-search", "confidence": score}
    return ranked[0], {"method": "title-search", "confidence": score}


def crossref_work(seed: dict) -> tuple[dict | None, dict]:
    doi = clean_doi(seed.get("doi"))
    if not doi:
        return None, {"method": "no-doi", "confidence": 0.0}
    try:
        message = request_json(f"{CROSSREF}/works/{urllib.parse.quote(doi)}").get("message")
        return message, {"method": "doi-crossref", "confidence": 0.98}
    except Exception:
        return None, {"method": "crossref-failed", "confidence": 0.0}


def reconstruct_abstract(inverted: object) -> str:
    if not isinstance(inverted, dict):
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in inverted.items():
        for position in positions or []:
            positioned.append((int(position), str(word)))
    return " ".join(word for _, word in sorted(positioned))


def normalize_openalex(work: dict, previous: dict, seed: dict, match: dict) -> dict:
    authors: list[dict] = []
    institutions: dict[str, dict] = {}
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        affiliations = []
        for institution in authorship.get("institutions") or []:
            row = {
                "name": institution.get("display_name") or "",
                "openAlexId": institution.get("id") or "",
                "countryCode": institution.get("country_code") or "",
                "type": institution.get("type") or "",
            }
            if row["name"]:
                institutions[row["name"].casefold()] = row
                affiliations.append(row)
        name = author.get("display_name") or ""
        if name:
            authors.append(
                {
                    "name": name,
                    "openAlexId": author.get("id") or "",
                    "orcid": author.get("orcid") or "",
                    "position": authorship.get("author_position") or "",
                    "corresponding": bool(authorship.get("is_corresponding")),
                    "institutions": affiliations,
                }
            )

    topics = []
    for topic in (work.get("topics") or [])[:8]:
        topics.append(
            {
                "name": topic.get("display_name") or "",
                "id": topic.get("id") or "",
                "score": float(topic.get("score") or 0),
                "subfield": (topic.get("subfield") or {}).get("display_name") or "",
                "field": (topic.get("field") or {}).get("display_name") or "",
                "domain": (topic.get("domain") or {}).get("display_name") or "",
            }
        )

    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    stamp = now_ms()
    citations = {"count": int(work.get("cited_by_count") or 0), "source": "OpenAlex", "updatedAt": stamp}
    scholarly = {
        **previous,
        "title": work.get("title") or previous.get("title") or seed.get("title") or "",
        "doi": clean_doi(work.get("doi") or previous.get("doi") or seed.get("doi")),
        "arxivId": seed.get("arxivId") or previous.get("arxivId") or "",
        "openAlexId": work.get("id") or previous.get("openAlexId") or "",
        "publicationDate": work.get("publication_date") or previous.get("publicationDate") or "",
        "year": work.get("publication_year") or previous.get("year"),
        "venue": source.get("display_name") or previous.get("venue") or "",
        "venueId": source.get("id") or previous.get("venueId") or "",
        "volume": (work.get("biblio") or {}).get("volume") or previous.get("volume") or "",
        "issue": (work.get("biblio") or {}).get("issue") or previous.get("issue") or "",
        "pages": "-".join(str(value) for value in [(work.get("biblio") or {}).get("first_page"), (work.get("biblio") or {}).get("last_page")] if value) or previous.get("pages") or "",
        "publisher": source.get("host_organization_name") or previous.get("publisher") or "",
        "type": work.get("type") or previous.get("type") or "",
        "authors": authors or previous.get("authors") or seed.get("authors") or [],
        "institutions": list(institutions.values()) or previous.get("institutions") or [],
        "abstract": reconstruct_abstract(work.get("abstract_inverted_index")) or previous.get("abstract") or seed.get("abstract") or "",
        "automaticTopics": [topic for topic in topics if topic["name"]],
        "primaryTopic": (work.get("primary_topic") or {}).get("display_name") or (topics[0]["name"] if topics else ""),
        "keywords": [row.get("display_name") for row in (work.get("keywords") or [])[:12] if row.get("display_name")],
        "relatedWorks": (work.get("related_works") or [])[:30],
        "referencedWorks": (work.get("referenced_works") or [])[:200],
        "openAccess": work.get("open_access"),
        "landingPageUrl": location.get("landing_page_url") or work.get("doi") or "",
        "metadataSource": "OpenAlex",
        "matchMethod": match["method"],
        "matchConfidence": round(float(match["confidence"]), 4),
        "matchedFromPdf": bool(seed.get("fromHistoricalPdf")),
        "updatedAt": stamp,
        "metadataError": "",
        "citations": citations,
    }
    return {"scholarly": scholarly, "citations": citations}


def normalize_crossref(message: dict, previous: dict, seed: dict, match: dict) -> dict:
    date_parts = ((message.get("published") or {}).get("date-parts") or [[None]])[0]
    year = date_parts[0] if date_parts else None
    publication_date = "-".join(str(value) for value in date_parts if value) if year else ""
    authors = []
    for author in message.get("author") or []:
        name = " ".join(value for value in [author.get("given"), author.get("family")] if value)
        if name:
            authors.append(
                {
                    "name": name,
                    "orcid": author.get("ORCID") or "",
                    "institutions": [{"name": row.get("name") or ""} for row in author.get("affiliation") or [] if row.get("name")],
                }
            )
    stamp = now_ms()
    citations = {"count": int(message.get("is-referenced-by-count") or 0), "source": "Crossref", "updatedAt": stamp}
    scholarly = {
        **previous,
        "title": (message.get("title") or [seed.get("title") or ""])[0],
        "doi": clean_doi(message.get("DOI") or seed.get("doi")),
        "arxivId": seed.get("arxivId") or previous.get("arxivId") or "",
        "publicationDate": publication_date or previous.get("publicationDate") or "",
        "year": year or previous.get("year"),
        "venue": (message.get("container-title") or [previous.get("venue") or ""])[0],
        "volume": message.get("volume") or previous.get("volume") or "",
        "issue": message.get("issue") or previous.get("issue") or "",
        "pages": message.get("page") or message.get("article-number") or previous.get("pages") or "",
        "publisher": message.get("publisher") or previous.get("publisher") or "",
        "type": message.get("type") or previous.get("type") or "",
        "authors": authors or previous.get("authors") or seed.get("authors") or [],
        "abstract": re.sub(r"<[^>]+>", " ", str(message.get("abstract") or previous.get("abstract") or seed.get("abstract") or "")).strip(),
        "keywords": message.get("subject") or previous.get("keywords") or [],
        "metadataSource": "Crossref",
        "matchMethod": match["method"],
        "matchConfidence": round(float(match["confidence"]), 4),
        "matchedFromPdf": bool(seed.get("fromHistoricalPdf")),
        "updatedAt": stamp,
        "metadataError": "",
        "citations": citations,
    }
    return {"scholarly": scholarly, "citations": citations}


def resolve(seed: dict, previous: dict) -> tuple[dict | None, dict]:
    work, match = openalex_work(seed)
    if work:
        return normalize_openalex(work, previous, seed, match), match
    message, crossref_match = crossref_work(seed)
    if message:
        return normalize_crossref(message, previous, seed, crossref_match), crossref_match
    return None, match


def name_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for row in value:
        name = row.get("name") if isinstance(row, dict) else row
        name = str(name or "").strip()
        if name and name.casefold() not in {x.casefold() for x in result}:
            result.append(name)
    return result


def build_paper_card(item: dict, scholarly: dict, source: str) -> dict:
    authors = name_list(scholarly.get("authors") or [])
    affiliations = name_list(scholarly.get("institutions") or [])
    for author in scholarly.get("authors") or []:
        if isinstance(author, dict):
            for name in name_list(author.get("institutions") or []):
                if name.casefold() not in {x.casefold() for x in affiliations}:
                    affiliations.append(name)
    year = scholarly.get("year") or str(scholarly.get("publicationDate") or "")[:4] or None
    try:
        year = int(year) if year else None
    except (TypeError, ValueError):
        year = None
    doi = clean_doi(scholarly.get("doi") or item.get("doi"))
    arxiv_id = str(scholarly.get("arxivId") or item.get("arxivId") or "").strip()
    venue = str(scholarly.get("venue") or "").strip()
    status = "preprint" if arxiv_id and (not venue or re.search(r"arxiv|preprint", venue, re.I)) else ("published" if venue or doi else "unpublished")
    title = str(scholarly.get("title") or item.get("title") or Path(str(item.get("filename") or "paper")).stem).strip()
    surname = (authors[0].split()[-1] if authors else "paper")
    keyword = next((word for word in re.findall(r"[A-Za-z0-9]+", title.lower()) if len(word) > 3), "work")
    citation_key = re.sub(r"[^A-Za-z0-9_-]", "", f"{surname}{year or 'nd'}{keyword}") or f"paper{year or 'nd'}work"
    stamp = now_ms()
    return {
        "schemaVersion": 1,
        "frozenAt": stamp,
        "updatedAt": stamp,
        "source": source,
        "title": title,
        "authors": authors,
        "affiliations": affiliations,
        "publicationStatus": status,
        "journal": venue,
        "year": year,
        "volume": scholarly.get("volume") or "",
        "issue": scholarly.get("issue") or "",
        "pages": scholarly.get("pages") or "",
        "publisher": scholarly.get("publisher") or "",
        "doi": doi,
        "arxivId": arxiv_id,
        "citationKey": citation_key,
        "bibtexEntryType": "article" if status == "published" else "misc",
        "links": {
            "pdf": "",
            "doi": f"https://doi.org/{doi}" if doi else "",
            "arxiv": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
            "publisher": scholarly.get("landingPageUrl") or "",
            "code": "",
            "project": "",
        },
        "evaluation": {"shortReview": "", "relevance": "", "readingStatus": "unread", "starred": False},
    }


def item_seed(item: dict) -> dict:
    scholarly = item.get("scholarly") or {}
    card = item.get("paperCard") if isinstance(item.get("paperCard"), dict) else {}
    raw_title = card.get("title") or scholarly.get("title") or item.get("title") or Path(str(item.get("filename") or "")).stem
    combined = " ".join(str(item.get(key) or "") for key in ("title", "filename", "desc"))
    card_authors = [{"name": name} for name in name_list(card.get("authors") or [])]
    return {
        "title": "" if generic_title(raw_title) else raw_title,
        "doi": clean_doi(card.get("doi") or scholarly.get("doi") or item.get("doi") or extract_doi(combined)),
        "arxivId": card.get("arxivId") or scholarly.get("arxivId") or extract_arxiv(combined),
        "openAlexId": scholarly.get("openAlexId") or "",
        "authors": card_authors or scholarly.get("authors") or [],
        "abstract": scholarly.get("abstract") or item.get("desc") or "",
        "keywords": scholarly.get("keywords") or item.get("tags") or [],
    }


def incomplete(item: dict) -> bool:
    if str(item.get("kind") or "").lower() not in {"pdf", ""}:
        return False
    scholarly = item.get("scholarly") or {}
    review_status = str((scholarly.get("metadataReview") or {}).get("status") or "")
    if review_status.startswith("accepted"):
        return False
    return bool(
        not scholarly.get("metadataSource")
        or scholarly.get("metadataError")
        or not scholarly.get("authors")
        or (not scholarly.get("doi") and not scholarly.get("arxivId"))
        or (not scholarly.get("publicationDate") and not scholarly.get("year"))
    )


def raw_storage_url(storage: dict) -> str:
    owner, repo, path = storage.get("owner"), storage.get("repo"), storage.get("path")
    if not owner or not repo or not path:
        return ""
    branch = storage.get("branch") or "main"
    encoded_path = urllib.parse.quote(str(path).lstrip("/"), safe="/")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{urllib.parse.quote(str(branch))}/{encoded_path}"


def read_remote_bytes(url: str, max_bytes: int, github_token: str = "") -> bytes:
    headers = {"User-Agent": "Research-Library-Metadata-Updater/5.2"}
    if github_token and ("githubusercontent.com" in url or "api.github.com" in url):
        headers["Authorization"] = f"Bearer {github_token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=90) as response:
        length = int(response.headers.get("content-length") or 0)
        if length and length > max_bytes:
            raise RuntimeError(f"PDF exceeds size limit ({length} bytes)")
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise RuntimeError(f"PDF exceeds size limit ({max_bytes} bytes)")
    if not data:
        raise RuntimeError("downloaded PDF is empty")
    return data


def load_pdf_bytes(item: dict, repo_root: Path, max_pdf_mb: int, github_token: str) -> tuple[bytes, str]:
    max_bytes = max_pdf_mb * 1024 * 1024
    path_value = str(item.get("path") or "").strip()
    candidates: list[tuple[str, str]] = []
    if item.get("storage"):
        url = raw_storage_url(item["storage"])
        if url:
            candidates.append(("url", url))
    if path_value.startswith(("http://", "https://")):
        candidates.append(("url", path_value))
    elif path_value:
        candidates.append(("file", str(repo_root / path_value.lstrip("/"))))

    errors = []
    seen = set()
    for kind, source in candidates:
        if source in seen:
            continue
        seen.add(source)
        try:
            if kind == "file":
                path = Path(source)
                if not path.exists():
                    raise FileNotFoundError(source)
                if path.stat().st_size > max_bytes:
                    raise RuntimeError(f"PDF exceeds {max_pdf_mb} MB")
                return path.read_bytes(), source
            return read_remote_bytes(source, max_bytes, github_token), source
        except Exception as exc:
            errors.append(f"{source}: {exc}")
    raise RuntimeError("; ".join(errors) if errors else "no readable PDF path")


def guess_first_page_title(text: str) -> str:
    for raw in text.splitlines()[:35]:
        line = re.sub(r"\s+", " ", raw).strip()
        if not 14 <= len(line) <= 260:
            continue
        if generic_title(line) or DOI_RE.search(line) or re.search(r"\b(?:arxiv|abstract|journal|volume|copyright)\b", line, re.I):
            continue
        if line.count(",") >= 4 or "@" in line:
            continue
        return line
    return ""


def parse_authors(value: object) -> list[dict]:
    text = str(value or "").strip()
    if not text:
        return []
    parts = re.split(r"\s+and\s+|[;；]", text, flags=re.I)
    return [{"name": part.strip()} for part in parts if part.strip()]


def extract_pdf_seed(item: dict, repo_root: Path, pages: int, max_pdf_mb: int, github_token: str) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("backfill mode requires pypdf; run: python -m pip install pypdf") from exc

    data, source = load_pdf_bytes(item, repo_root, max_pdf_mb, github_token)
    reader = PdfReader(io.BytesIO(data))
    metadata = reader.metadata or {}
    page_texts = []
    for page in reader.pages[: max(1, pages)]:
        try:
            page_texts.append(page.extract_text() or "")
        except Exception:
            page_texts.append("")
    text = "\n".join(page_texts)
    metadata_title = str(metadata.get("/Title") or "").strip()
    existing = item_seed(item)
    title = metadata_title if not generic_title(metadata_title) else existing.get("title") or guess_first_page_title(page_texts[0] if page_texts else "")
    combined = " ".join(
        [
            text,
            str(metadata.get("/Subject") or ""),
            str(metadata.get("/Keywords") or ""),
            str(item.get("filename") or ""),
        ]
    )
    abstract_match = re.search(
        r"\babstract\b[\s:—-]*(.{80,2500}?)(?=\b(?:keywords?|pacs|introduction|i\.|1\.)\b)",
        re.sub(r"\s+", " ", text),
        flags=re.I,
    )
    return {
        "title": title or "",
        "doi": extract_doi(combined) or existing.get("doi") or "",
        "arxivId": extract_arxiv(combined) or existing.get("arxivId") or "",
        "authors": parse_authors(metadata.get("/Author")) or existing.get("authors") or [],
        "abstract": abstract_match.group(1).strip() if abstract_match else existing.get("abstract") or "",
        "keywords": [part.strip() for part in re.split(r"[,;；]", str(metadata.get("/Keywords") or "")) if part.strip()],
        "fromHistoricalPdf": True,
        "pdfPages": len(reader.pages),
        "pdfSource": source,
        "historicalExtractedAt": now_ms(),
    }


def apply_match(item: dict, resolved: dict, match: dict, stage: str) -> None:
    review = {
        "status": "accepted-auto",
        "confidence": round(float(match.get("confidence") or 0), 4),
        "method": match.get("method") or "",
        "stage": stage,
        "reviewedAt": now_ms(),
    }
    scholarly = {**resolved["scholarly"], "metadataReview": review}
    item["scholarly"] = scholarly
    item["citations"] = resolved["citations"]
    # Core v5 invariant: initialize once, never refresh or overwrite a user card.
    if not isinstance(item.get("paperCard"), dict):
        item["paperCard"] = build_paper_card(item, scholarly, "backfill-auto" if stage == "pdf" else "metadata-first-match")


def record_scan(item: dict, status: str, match: dict, stage: str, message: str = "") -> None:
    scholarly = item.setdefault("scholarly", {})
    scholarly["backfillScan"] = {
        "status": status,
        "confidence": round(float(match.get("confidence") or 0), 4),
        "method": match.get("method") or "",
        "stage": stage,
        "message": message,
        "scannedAt": now_ms(),
    }


def report_row(item: dict, status: str, match: dict, stage: str, resolved: dict | None, message: str = "") -> dict:
    scholarly = (resolved or {}).get("scholarly") or {}
    return {
        "itemId": item.get("id") or "",
        "originalTitle": item.get("title") or item.get("filename") or "",
        "status": status,
        "confidence": round(float(match.get("confidence") or 0), 4),
        "method": match.get("method") or "",
        "stage": stage,
        "matchedTitle": scholarly.get("title") or "",
        "doi": scholarly.get("doi") or "",
        "authors": [author.get("name") or "" for author in scholarly.get("authors") or []][:12],
        "message": message,
    }


def run_daily(items: list[dict], threshold: float, max_items: int | None) -> tuple[int, list[dict]]:
    updated = 0
    report = []
    processed = 0
    for item in items:
        if str(item.get("kind") or "").lower() not in {"pdf", ""}:
            continue
        if max_items is not None and processed >= max_items:
            break
        processed += 1
        try:
            seed = item_seed(item)
            resolved, match = resolve(seed, item.get("scholarly") or {})
            if resolved and float(match.get("confidence") or 0) >= threshold:
                apply_match(item, resolved, match, "index")
                updated += 1
                report.append(report_row(item, "accepted", match, "index", resolved))
            else:
                report.append(report_row(item, "unmatched", match, "index", resolved, "No reliable daily match"))
        except Exception as exc:
            report.append(report_row(item, "error", {"method": "error", "confidence": 0}, "index", None, str(exc)))
        time.sleep(0.12)
    return updated, report


def run_backfill(
    items: list[dict],
    repo_root: Path,
    threshold: float,
    max_items: int | None,
    pages: int,
    max_pdf_mb: int,
    github_token: str,
) -> tuple[int, list[dict]]:
    updated = 0
    report = []
    targets = [item for item in items if incomplete(item)]
    targets.sort(key=lambda item: bool(((item.get("scholarly") or {}).get("backfillScan"))))
    if max_items is not None:
        targets = targets[:max_items]
    for item in targets:
        first_resolved = None
        first_match = {"method": "no-query", "confidence": 0.0}
        try:
            first_resolved, first_match = resolve(item_seed(item), item.get("scholarly") or {})
            if first_resolved and float(first_match.get("confidence") or 0) >= threshold:
                apply_match(item, first_resolved, first_match, "index")
                record_scan(item, "accepted", first_match, "index")
                updated += 1
                report.append(report_row(item, "accepted", first_match, "index", first_resolved))
                time.sleep(0.12)
                continue
        except Exception as exc:
            first_match = {"method": "index-error", "confidence": 0.0}
            first_error = str(exc)
        else:
            first_error = ""

        try:
            pdf_seed = extract_pdf_seed(item, repo_root, pages, max_pdf_mb, github_token)
            resolved, match = resolve(pdf_seed, item.get("scholarly") or {})
            if resolved and float(match.get("confidence") or 0) >= threshold:
                resolved["scholarly"].update(
                    {
                        "pdfPages": pdf_seed.get("pdfPages"),
                        "historicalExtractedAt": pdf_seed.get("historicalExtractedAt"),
                    }
                )
                apply_match(item, resolved, match, "pdf")
                record_scan(item, "accepted", match, "pdf")
                updated += 1
                report.append(report_row(item, "accepted", match, "pdf", resolved))
            elif resolved:
                record_scan(item, "review", match, "pdf", "Below automatic acceptance threshold")
                report.append(report_row(item, "review", match, "pdf", resolved, "Below automatic acceptance threshold"))
            else:
                local_candidate = {
                    "scholarly": {
                        "title": pdf_seed.get("title") or "",
                        "doi": pdf_seed.get("doi") or "",
                        "arxivId": pdf_seed.get("arxivId") or "",
                        "authors": pdf_seed.get("authors") or [],
                    }
                }
                message = "PDF parsed but database match was not reliable"
                record_scan(item, "review", match, "pdf", message)
                report.append(report_row(item, "review", match, "pdf", local_candidate, message))
        except Exception as exc:
            if first_resolved:
                message = f"PDF fallback failed: {exc}"
                record_scan(item, "review", first_match, "index", message)
                report.append(report_row(item, "review", first_match, "index", first_resolved, message))
            else:
                message = "; ".join(part for part in [first_error, str(exc)] if part)
                record_scan(item, "error", {"method": "pdf-error", "confidence": 0}, "pdf", message)
                report.append(report_row(item, "error", {"method": "pdf-error", "confidence": 0}, "pdf", None, message))
        time.sleep(0.12)
    return updated, report


def write_report(path: Path, mode: str, threshold: float, report: list[dict]) -> None:
    summary = {
        "accepted": sum(row["status"] == "accepted" for row in report),
        "review": sum(row["status"] == "review" for row in report),
        "unmatched": sum(row["status"] == "unmatched" for row in report),
        "error": sum(row["status"] == "error" for row in report),
    }
    payload = {
        "schemaVersion": 1,
        "mode": mode,
        "generatedAt": iso_now(),
        "acceptThreshold": threshold,
        "summary": summary,
        "results": report,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", default="data/index.json")
    parser.add_argument("--mode", choices=("daily", "backfill"), default="daily")
    parser.add_argument("--report", default="data/metadata-review.json")
    parser.add_argument("--accept-threshold", type=float, default=0.78)
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--pdf-pages", type=int, default=3)
    parser.add_argument("--max-pdf-mb", type=int, default=95)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    index_path = Path(args.index)
    if not index_path.exists():
        print(f"index not found: {index_path}", file=sys.stderr)
        return 2
    data: Any = json.loads(index_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        data = {"items": data}
    items = data.get("items") or []
    repo_root = index_path.parent.parent.resolve()

    if args.mode == "backfill":
        updated, report = run_backfill(
            items,
            repo_root,
            args.accept_threshold,
            args.max_items,
            args.pdf_pages,
            args.max_pdf_mb,
            os.environ.get("REPO_LIBRARY_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN") or "",
        )
        data["historicalMetadataUpdatedAt"] = now_ms()
    else:
        updated, report = run_daily(items, args.accept_threshold, args.max_items)

    data["schemaVersion"] = max(5, int(data.get("schemaVersion") or 0))
    data["appVersion"] = "5.2"
    data["paperCardSchemaVersion"] = 1
    data["metadataUpdatedAt"] = now_ms()
    data["metadataUpdatedAtIso"] = iso_now()

    report_path = Path(args.report)
    if not args.dry_run:
        if args.mode == "backfill" and report:
            backup_dir = index_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            shutil.copy2(index_path, backup_dir / f"index-before-v5-backfill-{stamp}.json")
        index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_report(report_path, args.mode, args.accept_threshold, report)

    summary = {
        "mode": args.mode,
        "processed": len(report),
        "updated": updated,
        "review": sum(row["status"] == "review" for row in report),
        "unmatched": sum(row["status"] == "unmatched" for row in report),
        "errors": sum(row["status"] == "error" for row in report),
        "dryRun": args.dry_run,
    }
    print(json.dumps(summary, ensure_ascii=False))
    for row in report:
        if row["status"] in {"review", "error"}:
            print(f"{row['status']}: {row['originalTitle']}: {row['message']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
