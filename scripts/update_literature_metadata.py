#!/usr/bin/env python3
"""Research Library v5.3 trustworthy metadata updater and PDF backfill.

Daily mode refreshes only identity-verified records without downloading PDFs.
Backfill mode uses a conservative two-stage pipeline:
1) DOI/arXiv/title matching from index.json;
2) for unresolved records, download/read the first PDF pages and match again.

Every candidate is verified by an exact DOI/arXiv identifier or by composite
title/author/year evidence.  A stale OpenAlex ID is evidence to check, not a
reason to trust a record. Only scholarly/citations/review fields are refreshed.
A missing v5 paperCard is initialized once from the first accepted match; an
existing paperCard is never overwritten. Manual title, topics, tags, notes,
links, BibTeX and evaluations are safe.
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
LIBRARY_LABEL_RE = re.compile(
    r"^(?P<author>[A-Z][A-Za-z'`-]{1,30})(?P<year>(?:19|20)\d{2})(?:[A-Za-z]{1,12})?[-_\s:]+(?P<title>.+)$"
)
YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
VERIFIED_REASONS = {"exact-doi", "exact-arxiv", "composite"}


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


def clean_arxiv(value: object) -> str:
    arxiv_id = extract_arxiv(value) or str(value or "").strip()
    return re.sub(r"v\d+$", "", arxiv_id, flags=re.I).lower()


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


def clean_library_title(value: object) -> str:
    """Turn labels such as Author2025arXiv-Actual title into search text."""
    text = re.sub(r"\.(?:pdf|epub)$", "", str(value or "").strip(), flags=re.I)
    match = LIBRARY_LABEL_RE.match(text)
    if match:
        text = match.group("title")
    text = re.sub(r"[_|]+", " ", text)
    text = re.sub(r"\s*[-–—]\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip(" -_:;")


def seed_year(value: object) -> int | None:
    match = YEAR_RE.search(str(value or ""))
    return int(match.group(1)) if match else None


def author_names(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for row in value:
        name = row.get("name") if isinstance(row, dict) else row
        name = re.sub(r"\s+", " ", str(name or "")).strip()
        if name and name.casefold() not in {existing.casefold() for existing in names}:
            names.append(name)
    return names


def filename_author_year(value: object) -> tuple[str, int | None]:
    match = LIBRARY_LABEL_RE.match(Path(str(value or "")).stem)
    return (match.group("author"), int(match.group("year"))) if match else ("", None)


def normalized_person_name(value: object) -> str:
    return re.sub(r"[^\w]+", " ", str(value or "").casefold(), flags=re.UNICODE).strip()


def surname(value: object) -> str:
    parts = normalized_person_name(value).split()
    return parts[-1] if parts else ""


def author_similarity(seed_authors: object, candidate_authors: object) -> tuple[float, bool]:
    seeds, candidates = author_names(seed_authors), author_names(candidate_authors)
    if not seeds or not candidates:
        return 0.0, False
    scores = []
    for seed_name in seeds[:6]:
        seed_surname = surname(seed_name)
        best = 0.0
        for candidate_name in candidates:
            candidate_surname = surname(candidate_name)
            if seed_surname and seed_surname == candidate_surname:
                best = 1.0
                break
            best = max(best, similarity(seed_name, candidate_name))
        scores.append(best)
    return sum(scores) / len(scores), True


def work_arxiv_ids(work: dict) -> set[str]:
    values: list[object] = [work.get("doi"), work.get("id")]
    for location in [work.get("primary_location"), *(work.get("locations") or [])]:
        if isinstance(location, dict):
            values.extend([location.get("landing_page_url"), location.get("pdf_url")])
    result = {clean_arxiv(value) for value in values if extract_arxiv(value)}
    return {value for value in result if value}


def work_author_names(work: dict) -> list[str]:
    return [
        str((authorship.get("author") or {}).get("display_name") or "").strip()
        for authorship in work.get("authorships") or []
        if str((authorship.get("author") or {}).get("display_name") or "").strip()
    ]


def candidate_evidence(seed: dict, work: dict, method: str) -> dict:
    seed_doi = clean_doi(seed.get("doi"))
    candidate_doi = clean_doi(work.get("doi"))
    seed_arxiv = clean_arxiv(seed.get("arxivId"))
    candidate_arxiv = work_arxiv_ids(work)
    doi_exact = bool(seed_doi and candidate_doi and seed_doi == candidate_doi)
    arxiv_exact = bool(seed_arxiv and seed_arxiv in candidate_arxiv)
    title_score = similarity(seed.get("title"), work.get("title"))
    author_score, has_author_evidence = author_similarity(seed.get("authors"), work_author_names(work))
    seed_year_value = seed.get("year")
    candidate_year = work.get("publication_year")
    has_year_evidence = bool(seed_year_value and candidate_year)
    try:
        year_delta = abs(int(seed_year_value) - int(candidate_year)) if has_year_evidence else None
    except (TypeError, ValueError):
        year_delta = None
        has_year_evidence = False
    year_score = 1.0 if year_delta == 0 else (0.5 if year_delta == 1 else 0.0)

    warnings: list[str] = []
    if seed.get("openAlexId") and str(seed.get("openAlexId")).rstrip("/").split("/")[-1] == str(work.get("id") or "").rstrip("/").split("/")[-1]:
        if title_score < 0.72:
            warnings.append("stored-openalex-id-title-conflict")
        if has_author_evidence and author_score < 0.30:
            warnings.append("stored-openalex-id-author-conflict")
        if has_year_evidence and year_score == 0:
            warnings.append("stored-openalex-id-year-conflict")

    if doi_exact:
        verification, confidence = "exact-doi", 0.995
    elif arxiv_exact:
        verification, confidence = "exact-arxiv", 0.99
    else:
        confidence = 0.76 * title_score
        confidence += 0.16 * (author_score if has_author_evidence else 0.5)
        confidence += 0.08 * (year_score if has_year_evidence else 0.5)
        support = (has_author_evidence and author_score >= 0.55) or (has_year_evidence and year_score >= 0.5)
        verification = "composite" if title_score >= 0.88 and (support or title_score >= 0.96) else "unverified"
    if warnings and not (doi_exact or arxiv_exact):
        verification = "conflict"

    return {
        "method": method,
        "confidence": round(float(confidence), 4),
        "verification": verification,
        "verified": verification in VERIFIED_REASONS,
        "identifierMatch": "doi" if doi_exact else ("arxiv" if arxiv_exact else ""),
        "titleScore": round(title_score, 4),
        "authorScore": round(author_score, 4),
        "yearScore": round(year_score, 4),
        "hasAuthorEvidence": has_author_evidence,
        "hasYearEvidence": has_year_evidence,
        "seedTitle": seed.get("title") or "",
        "candidateTitle": work.get("title") or "",
        "seedAuthors": author_names(seed.get("authors"))[:12],
        "candidateAuthors": work_author_names(work)[:12],
        "seedYear": seed_year_value,
        "candidateYear": candidate_year,
        "seedDoi": seed_doi,
        "candidateDoi": candidate_doi,
        "seedArxivId": seed_arxiv,
        "candidateArxivIds": sorted(candidate_arxiv),
        "candidateOpenAlexId": work.get("id") or "",
        "warnings": warnings,
    }


def match_is_accepted(match: dict, threshold: float) -> bool:
    return bool(match.get("verified")) and float(match.get("confidence") or 0) >= threshold


def request_json(url: str, retries: int = 3) -> dict:
    mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    if mailto and "api.openalex.org" in url:
        url += ("&" if "?" in url else "?") + "mailto=" + urllib.parse.quote(mailto)
    headers = {"User-Agent": "Research-Library-Metadata-Updater/5.3"}
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
    """Return the strongest candidate, but never trust a stored ID by itself."""
    candidates: dict[str, tuple[dict, str]] = {}
    errors: list[str] = []

    def add(work: dict | None, method: str) -> None:
        if not isinstance(work, dict):
            return
        key = str(work.get("id") or work.get("doi") or work.get("title") or len(candidates))
        previous = candidates.get(key)
        if previous is None or method.startswith("doi"):
            candidates[key] = (work, method)

    openalex_id = str(seed.get("openAlexId") or "").strip()
    if openalex_id:
        work_id = openalex_id.rstrip("/").split("/")[-1]
        try:
            add(request_json(f"{OPENALEX}/works/{urllib.parse.quote(work_id)}"), "openalex-id-revalidated")
        except Exception as exc:
            errors.append(f"stored OpenAlex ID failed: {exc}")

    doi = clean_doi(seed.get("doi"))
    if doi:
        try:
            encoded = urllib.parse.quote(f"https://doi.org/{doi}", safe="")
            results = request_json(f"{OPENALEX}/works?filter=doi:{encoded}&per_page=3").get("results") or []
            for work in results:
                add(work, "doi-query")
        except Exception as exc:
            errors.append(f"DOI query failed: {exc}")

    arxiv_id = clean_arxiv(seed.get("arxivId"))
    title = str(seed.get("title") or "").strip()
    queries = []
    if arxiv_id:
        queries.append((arxiv_id, "arxiv-search"))
    if title:
        queries.append((title, "title-search"))
    seen_queries: set[str] = set()
    for query, method in queries:
        if query.casefold() in seen_queries:
            continue
        seen_queries.add(query.casefold())
        try:
            results = request_json(f"{OPENALEX}/works?search={urllib.parse.quote(query)}&per_page=10").get("results") or []
            for work in results:
                add(work, method)
        except Exception as exc:
            errors.append(f"{method} failed: {exc}")

    if not candidates:
        method = "no-query" if not (openalex_id or doi or arxiv_id or title) else "no-result"
        return None, {
            "method": method,
            "confidence": 0.0,
            "verification": "unverified",
            "verified": False,
            "warnings": errors,
        }

    ranked: list[tuple[dict, dict]] = []
    for work, method in candidates.values():
        evidence = candidate_evidence(seed, work, method)
        ranked.append((work, evidence))
    ranked.sort(
        key=lambda row: (
            bool(row[1].get("verified")),
            row[1].get("verification") in {"exact-doi", "exact-arxiv"},
            float(row[1].get("confidence") or 0),
            float(row[1].get("titleScore") or 0),
        ),
        reverse=True,
    )
    work, match = ranked[0]
    if errors:
        match["warnings"] = [*(match.get("warnings") or []), *errors]
    return work, match


def crossref_work(seed: dict) -> tuple[dict | None, dict]:
    doi = clean_doi(seed.get("doi"))
    if not doi:
        return None, {"method": "no-doi", "confidence": 0.0}
    try:
        message = request_json(f"{CROSSREF}/works/{urllib.parse.quote(doi)}").get("message")
        candidate_doi = clean_doi((message or {}).get("DOI"))
        exact = bool(candidate_doi and candidate_doi == doi)
        return message, {
            "method": "doi-crossref",
            "confidence": 0.995 if exact else 0.0,
            "verification": "exact-doi" if exact else "conflict",
            "verified": exact,
            "identifierMatch": "doi" if exact else "",
            "seedDoi": doi,
            "candidateDoi": candidate_doi,
            "seedTitle": seed.get("title") or "",
            "candidateTitle": ((message or {}).get("title") or [""])[0],
            "warnings": [] if exact else ["crossref-doi-conflict"],
        }
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
        "matchVerification": match.get("verification") or "unverified",
        "matchEvidence": {key: value for key, value in match.items() if key not in {"method", "confidence", "verified"}},
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
        "matchVerification": match.get("verification") or "unverified",
        "matchEvidence": {key: value for key, value in match.items() if key not in {"method", "confidence", "verified"}},
        "matchedFromPdf": bool(seed.get("fromHistoricalPdf")),
        "updatedAt": stamp,
        "metadataError": "",
        "citations": citations,
    }
    return {"scholarly": scholarly, "citations": citations}


def resolve(seed: dict, previous: dict) -> tuple[dict | None, dict]:
    work, match = openalex_work(seed)
    if work and match.get("verified"):
        return normalize_openalex(work, previous, seed, match), match
    message, crossref_match = crossref_work(seed)
    if message and crossref_match.get("verified"):
        return normalize_crossref(message, previous, seed, crossref_match), crossref_match
    # Keep the strongest unverified OpenAlex candidate for the review report,
    # without merging it into the item.
    if work:
        candidate = normalize_openalex(work, {}, seed, match)
        return candidate, match
    return None, match if match.get("confidence", 0) >= crossref_match.get("confidence", 0) else crossref_match


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
    verification = scholarly.get("metadataVerification") or {}
    review_status = str((scholarly.get("metadataReview") or {}).get("status") or "")
    trusted_scholarly = review_status == "accepted-manually" or verification.get("status") == "verified"
    frozen_at = int(card.get("frozenAt") or 0)
    updated_at = int(card.get("updatedAt") or 0)
    card_source = str(card.get("source") or "")
    card_manually_maintained = bool(card) and (
        review_status == "accepted-manually"
        or (updated_at and frozen_at and updated_at > frozen_at)
        or card_source not in {"backfill-auto", "metadata-first-match", "upload-metadata"}
    )
    source_label = (
        card.get("title") if card_manually_maintained else None
    ) or item.get("title") or Path(str(item.get("filename") or "")).stem or card.get("title") or scholarly.get("title")
    raw_title = source_label or scholarly.get("title") or ""
    title = clean_library_title(raw_title)
    guessed_author, guessed_year = filename_author_year(item.get("filename") or item.get("title") or "")
    combined = " ".join(str(item.get(key) or "") for key in ("title", "filename", "desc"))
    card_authors = [{"name": name} for name in name_list(card.get("authors") or [])] if card_manually_maintained else []
    known_authors = card_authors or (scholarly.get("authors") or [] if trusted_scholarly else [])
    if not known_authors and guessed_author:
        known_authors = [{"name": guessed_author}]
    doi = clean_doi(card.get("doi")) if card_manually_maintained else ""
    arxiv_id = str(card.get("arxivId") or "") if card_manually_maintained else ""
    if trusted_scholarly:
        doi = doi or clean_doi(scholarly.get("doi"))
        arxiv_id = arxiv_id or str(scholarly.get("arxivId") or "")
    return {
        "title": "" if generic_title(title) else title,
        "doi": doi or clean_doi(item.get("doi") or extract_doi(combined)),
        "arxivId": arxiv_id or extract_arxiv(combined),
        "openAlexId": scholarly.get("openAlexId") or "",
        "authors": known_authors,
        "year": (card.get("year") if card_manually_maintained else None)
        or (scholarly.get("year") if trusted_scholarly else None)
        or guessed_year
        or seed_year(combined),
        "abstract": scholarly.get("abstract") or item.get("desc") or "",
        "keywords": scholarly.get("keywords") or item.get("tags") or [],
    }


def incomplete(item: dict) -> bool:
    if str(item.get("kind") or "").lower() not in {"pdf", ""}:
        return False
    scholarly = item.get("scholarly") or {}
    review = scholarly.get("metadataReview") or {}
    review_status = str(review.get("status") or "")
    verification = scholarly.get("metadataVerification") or {}
    if review_status == "accepted-manually":
        return False
    if verification.get("status") == "verified" and verification.get("reason") in VERIFIED_REASONS:
        return False
    return bool(
        review_status == "accepted-auto"
        or not scholarly.get("metadataSource")
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
    headers = {"User-Agent": "Research-Library-Metadata-Updater/5.3"}
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
    first_page_title = guess_first_page_title(page_texts[0] if page_texts else "")
    title = metadata_title if not generic_title(metadata_title) else first_page_title or existing.get("title")
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
        "year": seed_year(text) or existing.get("year"),
        "abstract": abstract_match.group(1).strip() if abstract_match else existing.get("abstract") or "",
        "keywords": [part.strip() for part in re.split(r"[,;；]", str(metadata.get("/Keywords") or "")) if part.strip()],
        "fromHistoricalPdf": True,
        "pdfPages": len(reader.pages),
        "pdfSource": source,
        "historicalExtractedAt": now_ms(),
    }


def apply_match(item: dict, resolved: dict, match: dict, stage: str) -> None:
    stamp = now_ms()
    previous_review = ((item.get("scholarly") or {}).get("metadataReview") or {})
    manually_accepted = previous_review.get("status") == "accepted-manually"
    review = {
        "status": "accepted-manually" if manually_accepted else "accepted-auto",
        "confidence": round(float(match.get("confidence") or 0), 4),
        "method": match.get("method") or "",
        "stage": stage,
        "verification": match.get("verification") or "unverified",
        "evidence": {key: value for key, value in match.items() if key not in {"method", "confidence", "verified"}},
        "reviewedAt": previous_review.get("reviewedAt") if manually_accepted else stamp,
        "autoVerifiedAt": stamp,
    }
    verification = {
        "status": "verified",
        "reason": match.get("verification") or "",
        "confidence": round(float(match.get("confidence") or 0), 4),
        "method": match.get("method") or "",
        "stage": stage,
        "verifiedAt": stamp,
        "warnings": match.get("warnings") or [],
    }
    scholarly = {**resolved["scholarly"], "metadataReview": review, "metadataVerification": verification}
    item["scholarly"] = scholarly
    item["citations"] = resolved["citations"]
    # Core v5 invariant: initialize once, never refresh or overwrite a user card.
    if not isinstance(item.get("paperCard"), dict):
        item["paperCard"] = build_paper_card(item, scholarly, "backfill-auto" if stage == "pdf" else "metadata-first-match")


def mark_review_required(item: dict, match: dict, stage: str, resolved: dict | None, message: str) -> None:
    """Record a conflict without merging the candidate or touching citations/card."""
    scholarly = item.setdefault("scholarly", {})
    previous_review = scholarly.get("metadataReview") or {}
    candidate = (resolved or {}).get("scholarly") or {}
    stamp = now_ms()
    scholarly["metadataReview"] = {
        "status": "review-required",
        "previousStatus": previous_review.get("status") or "",
        "confidence": round(float(match.get("confidence") or 0), 4),
        "method": match.get("method") or "",
        "stage": stage,
        "verification": match.get("verification") or "unverified",
        "message": message,
        "candidate": {
            "title": candidate.get("title") or match.get("candidateTitle") or "",
            "doi": candidate.get("doi") or match.get("candidateDoi") or "",
            "openAlexId": candidate.get("openAlexId") or match.get("candidateOpenAlexId") or "",
            "authors": author_names(candidate.get("authors"))[:12],
            "year": candidate.get("year") or match.get("candidateYear"),
        },
        "evidence": {key: value for key, value in match.items() if key not in {"method", "confidence", "verified"}},
        "reviewedAt": stamp,
    }
    scholarly["metadataVerification"] = {
        "status": "conflict" if match.get("verification") == "conflict" else "unverified",
        "reason": match.get("verification") or "unverified",
        "confidence": round(float(match.get("confidence") or 0), 4),
        "checkedAt": stamp,
        "warnings": match.get("warnings") or [],
    }


def record_scan(item: dict, status: str, match: dict, stage: str, message: str = "") -> None:
    scholarly = item.setdefault("scholarly", {})
    scholarly["backfillScan"] = {
        "status": status,
        "confidence": round(float(match.get("confidence") or 0), 4),
        "method": match.get("method") or "",
        "verification": match.get("verification") or "unverified",
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
        "verification": match.get("verification") or "unverified",
        "verified": bool(match.get("verified")),
        "stage": stage,
        "candidateTitle": scholarly.get("title") or match.get("candidateTitle") or "",
        "currentTitle": ((item.get("scholarly") or {}).get("title") or ""),
        "doi": scholarly.get("doi") or "",
        "openAlexId": scholarly.get("openAlexId") or match.get("candidateOpenAlexId") or "",
        "authors": author_names(scholarly.get("authors"))[:12],
        "year": scholarly.get("year") or match.get("candidateYear"),
        "identifierMatch": match.get("identifierMatch") or "",
        "titleScore": match.get("titleScore"),
        "authorScore": match.get("authorScore"),
        "yearScore": match.get("yearScore"),
        "warnings": match.get("warnings") or [],
        "message": message,
    }


def run_daily(items: list[dict], threshold: float, max_items: int | None) -> tuple[int, list[dict]]:
    updated = 0
    report = []
    processed = 0
    for item in items:
        if str(item.get("kind") or "").lower() not in {"pdf", ""}:
            continue
        if str((((item.get("scholarly") or {}).get("metadataReview") or {}).get("status") or "")) == "accepted-manually":
            continue
        if max_items is not None and processed >= max_items:
            break
        processed += 1
        try:
            seed = item_seed(item)
            resolved, match = resolve(seed, item.get("scholarly") or {})
            if resolved and match_is_accepted(match, threshold):
                apply_match(item, resolved, match, "index")
                updated += 1
                report.append(report_row(item, "accepted", match, "index", resolved))
            else:
                old_auto = str((((item.get("scholarly") or {}).get("metadataReview") or {}).get("status") or "")) == "accepted-auto"
                status = "review" if resolved or old_auto or match.get("verification") == "conflict" else "unmatched"
                message = "Existing automatic match could not be reverified" if old_auto else "No identity-verified daily match"
                if status == "review":
                    mark_review_required(item, match, "index", resolved, message)
                report.append(report_row(item, status, match, "index", resolved, message))
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
            if first_resolved and match_is_accepted(first_match, threshold):
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
            if resolved and match_is_accepted(match, threshold):
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
                message = "PDF candidate lacks sufficient identity evidence"
                mark_review_required(item, match, "pdf", resolved, message)
                record_scan(item, "review", match, "pdf", message)
                report.append(report_row(item, "review", match, "pdf", resolved, message))
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
                mark_review_required(item, match, "pdf", local_candidate, message)
                record_scan(item, "review", match, "pdf", message)
                report.append(report_row(item, "review", match, "pdf", local_candidate, message))
        except Exception as exc:
            if first_resolved:
                message = f"PDF fallback failed: {exc}"
                mark_review_required(item, first_match, "index", first_resolved, message)
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
        "conflicts": sum(row.get("verification") == "conflict" for row in report),
        "pdfParsed": sum(row.get("stage") == "pdf" for row in report),
        "exactVerified": sum(row.get("verification") in {"exact-doi", "exact-arxiv"} for row in report),
        "compositeVerified": sum(row.get("verification") == "composite" and row.get("verified") for row in report),
    }
    payload = {
        "schemaVersion": 2,
        "updaterVersion": "5.3",
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
    parser.add_argument("--pdf-pages", type=int, default=5)
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
    data["appVersion"] = "5.3"
    data["paperCardSchemaVersion"] = 1
    data["metadataUpdatedAt"] = now_ms()
    data["metadataUpdatedAtIso"] = iso_now()

    report_path = Path(args.report)
    if not args.dry_run:
        if args.mode == "backfill" and report:
            backup_dir = index_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            shutil.copy2(index_path, backup_dir / f"index-before-v5.3-backfill-{stamp}.json")
        index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_report(report_path, args.mode, args.accept_threshold, report)

    summary = {
        "mode": args.mode,
        "processed": len(report),
        "updated": updated,
        "review": sum(row["status"] == "review" for row in report),
        "unmatched": sum(row["status"] == "unmatched" for row in report),
        "errors": sum(row["status"] == "error" for row in report),
        "conflicts": sum(row.get("verification") == "conflict" for row in report),
        "verified": sum(bool(row.get("verified")) for row in report),
        "dryRun": args.dry_run,
    }
    print(json.dumps(summary, ensure_ascii=False))
    for row in report:
        if row["status"] in {"review", "error"}:
            print(f"{row['status']}: {row['originalTitle']}: {row['message']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
