#!/usr/bin/env python3
"""Push Embase RIS or JSON metadata to Zotero via local Connector API.

Input:
  python push_to_zotero.py export.ris
  python push_to_zotero.py export.json
  type export.ris | python push_to_zotero.py --ris -

The script is intentionally local-only. It does not handle browser cookies,
Embase credentials, or institution tokens.
"""

import hashlib
import io
import json
import os
import sys
import urllib.error
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

ZOTERO_API = "http://127.0.0.1:23119/connector"
HTTP_TIMEOUT = 15


def zotero_request(endpoint, data=None, timeout=HTTP_TIMEOUT):
    url = f"{ZOTERO_API}/{endpoint}"
    body = json.dumps(data or {}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Zotero-Connector-API-Version": "3",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        text = resp.read().decode("utf-8")
        return resp.status, json.loads(text) if text else None
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(text) if text else None
        except json.JSONDecodeError:
            return exc.code, {"error": text}
    except urllib.error.URLError:
        return 0, None
    except TimeoutError:
        return -1, {"error": f"Timeout ({timeout}s)"}


def read_text(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8-sig") as handle:
        return handle.read()


def normalize_tag(tag):
    return tag.strip().upper()


def parse_ris(text):
    records = []
    current = {}

    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        if len(raw_line) >= 6 and raw_line[2:6] == "  - ":
            tag = normalize_tag(raw_line[:2])
            value = raw_line[6:].strip()
        else:
            # Continuation line.
            if current:
                current.setdefault("_continuation", [])
                current["_continuation"].append(raw_line.strip())
            continue

        if tag == "TY":
            current = {"TY": [value]}
        elif tag == "ER":
            if current:
                records.append(current)
            current = {}
        else:
            current.setdefault(tag, []).append(value)

    if current:
        records.append(current)
    return records


def first(record, *tags):
    for tag in tags:
        values = record.get(tag)
        if values:
            return values[0]
    return ""


def all_values(record, *tags):
    values = []
    for tag in tags:
        values.extend(record.get(tag, []))
    return [v for v in values if v]


def split_author(name):
    name = name.strip()
    if not name:
        return None
    if "," in name:
        last, first_name = name.split(",", 1)
        return {
            "lastName": last.strip(),
            "firstName": first_name.strip(),
            "creatorType": "author",
        }
    return {"name": name, "creatorType": "author"}


def ris_to_item(record):
    creators = [split_author(name) for name in all_values(record, "AU", "A1")]
    creators = [creator for creator in creators if creator]

    start_page = first(record, "SP")
    end_page = first(record, "EP")
    pages = first(record, "PG")
    if not pages and (start_page or end_page):
        pages = f"{start_page}-{end_page}".strip("-")

    doi = first(record, "DO")
    pmid = first(record, "PMID", "PM")
    embase_id = first(record, "ID", "AN", "M1")

    extra = []
    if embase_id:
        extra.append(f"Embase ID: {embase_id}")
    if pmid:
        extra.append(f"PMID: {pmid}")
    for note in all_values(record, "N1", "N2"):
        if "embase" in note.lower() or "pui" in note.lower() or "lui" in note.lower():
            extra.append(note)

    item = {
        "itemType": "journalArticle",
        "title": first(record, "TI", "T1", "CT"),
        "creators": creators,
        "publicationTitle": first(record, "JO", "JF", "T2", "JA"),
        "date": first(record, "PY", "Y1", "DA"),
        "volume": first(record, "VL"),
        "issue": first(record, "IS"),
        "pages": pages,
        "DOI": doi,
        "ISSN": first(record, "SN"),
        "abstractNote": first(record, "AB", "N2"),
        "url": first(record, "UR"),
        "libraryCatalog": "Embase",
        "language": first(record, "LA"),
        "tags": [{"tag": kw, "type": 1} for kw in all_values(record, "KW")],
        "attachments": [],
    }

    if extra:
        item["extra"] = "\n".join(extra)

    return {key: value for key, value in item.items() if value not in ("", [], None)}


def normalize_json(data):
    if isinstance(data, dict) and "items" in data:
        items = data["items"]
    elif isinstance(data, list):
        items = data
    else:
        items = [data]

    normalized = []
    for item in items:
        if "itemType" in item:
            normalized.append(item)
            continue

        authors = item.get("authors", [])
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.replace(" and ", ";").split(";") if a.strip()]

        creators = [split_author(author) for author in authors]
        creators = [creator for creator in creators if creator]

        extra = []
        for label, key in [
            ("Embase ID", "id"),
            ("PUI", "pui"),
            ("LUI", "lui"),
            ("PMID", "pmid"),
            ("Publication type", "publicationType"),
        ]:
            if item.get(key):
                extra.append(f"{label}: {item[key]}")

        normalized.append(
            {
                "itemType": "journalArticle",
                "title": item.get("title", ""),
                "creators": creators,
                "publicationTitle": item.get("source", "") or item.get("journal", ""),
                "date": str(item.get("year", "") or item.get("date", "")),
                "volume": str(item.get("volume", "") or ""),
                "issue": str(item.get("issue", "") or ""),
                "pages": str(item.get("pages", "") or ""),
                "DOI": item.get("doi", ""),
                "ISSN": item.get("issn", ""),
                "abstractNote": item.get("abstract", ""),
                "url": item.get("url", ""),
                "libraryCatalog": "Embase",
                "language": item.get("language", ""),
                "tags": [{"tag": kw, "type": 1} for kw in item.get("indexTerms", [])],
                "extra": "\n".join(extra),
                "attachments": [],
            }
        )

    return [{k: v for k, v in item.items() if v not in ("", [], None)} for item in normalized]


def make_session_id(items):
    keys = []
    for item in items:
        keys.append(
            item.get("DOI")
            or item.get("url")
            or item.get("title")
            or json.dumps(item, ensure_ascii=False, sort_keys=True)
        )
    raw = "|".join(sorted(keys))
    return hashlib.md5(raw.encode("utf-8", errors="surrogateescape")).hexdigest()[:12]


def save_items(items, uri=""):
    session_id = make_session_id(items)
    for index, item in enumerate(items):
        item.setdefault("id", f"embase_{session_id}_{index}")

    status, response = zotero_request(
        "saveItems",
        {"sessionID": session_id, "uri": uri, "items": items},
    )
    if status == 201:
        return 201, f"Saved (session: {session_id})"
    if status == 409:
        return 201, f"Already saved (session: {session_id})"
    if status == 0:
        return 0, "Zotero not running"
    if status == -1:
        return -1, f"Timeout ({HTTP_TIMEOUT}s)"
    return status, f"HTTP {status}: {response}"


def load_items(argv):
    if not argv or argv[0] == "-":
        text = sys.stdin.read()
        source = "-"
    else:
        source = argv[0]
        text = read_text(source)

    ext = os.path.splitext(source)[1].lower()
    stripped = text.lstrip()

    if ext == ".json" or stripped.startswith("{") or stripped.startswith("["):
        data = json.loads(text)
        return normalize_json(data)

    records = parse_ris(text)
    return [ris_to_item(record) for record in records]


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "--list":
        status, data = zotero_request("getSelectedCollection")
        if status != 200 or not data:
            print("Error: Cannot connect to Zotero.")
            sys.exit(1)
        print(f"Current collection: {data.get('name', '?')}")
        for target in data.get("targets", []):
            indent = " " * target.get("level", 0)
            print(f" {indent}{target['name']} (ID: {target['id']})")
        return

    if argv and argv[0] == "--ris":
        argv = argv[1:]

    status, _ = zotero_request("ping")
    if status == 0:
        print("Error: Zotero not running.")
        sys.exit(1)

    items = load_items(argv)
    items = [item for item in items if item.get("title") or item.get("DOI")]
    if not items:
        print("Error: No valid RIS or JSON items found.")
        sys.exit(1)

    col_status, collection = zotero_request("getSelectedCollection")
    if col_status == 200 and collection:
        print(f"Zotero collection: {collection.get('name', '?')}")

    status, message = save_items(items, items[0].get("url", ""))
    if status == 201:
        print(f"OK: {message} ({len(items)} papers)")
        for item in items[:20]:
            print(f" - {item.get('title', '?')}")
        if len(items) > 20:
            print(f" ... {len(items) - 20} more")
        return

    print(f"Error: {message}")
    sys.exit(1)


if __name__ == "__main__":
    main()
