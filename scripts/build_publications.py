#!/usr/bin/env python3
"""
Build `_data/publications.json` from `publications.bib`.

Phase 1 design:
- Keep publications.bib as the source of truth.
- Precompute sorting and display-friendly fields in JSON.
- Let publications.md stay simple (section loop + list rendering).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
BIB_PATH = ROOT / "publications.bib"
OUT_PATH = ROOT / "_data" / "publications.json"


MONTH_ORDER = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

MONTH_LABEL = {
    1: "Jan.",
    2: "Feb.",
    3: "Mar.",
    4: "Apr.",
    5: "May.",
    6: "Jun.",
    7: "Jul.",
    8: "Aug.",
    9: "Sep.",
    10: "Oct.",
    11: "Nov.",
    12: "Dec.",
}

OWN_NAME_KEYS = {
    "yujioyamada",
    "oyamadayuji",
    "小山田雄仁",
}


@dataclass
class BibEntry:
    entry_type: str
    key: str
    fields: Dict[str, str]


def _strip_wrapping(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and ((v[0] == "{" and v[-1] == "}") or (v[0] == '"' and v[-1] == '"')):
        return v[1:-1].strip()
    return v


def _read_balanced(text: str, idx: int, open_ch: str, close_ch: str) -> Tuple[str, int]:
    assert text[idx] == open_ch
    depth = 1
    i = idx + 1
    start = i
    while i < len(text):
        c = text[i]
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
        i += 1
    raise ValueError(f"Unbalanced delimiter: {open_ch}{close_ch}")


def parse_bibtex(text: str) -> List[BibEntry]:
    entries: List[BibEntry] = []
    i = 0
    while i < len(text):
        at = text.find("@", i)
        if at < 0:
            break
        j = at + 1
        while j < len(text) and text[j].isalpha():
            j += 1
        entry_type = text[at + 1 : j].strip().lower()
        while j < len(text) and text[j].isspace():
            j += 1
        if j >= len(text) or text[j] != "{":
            i = j + 1
            continue
        block, next_i = _read_balanced(text, j, "{", "}")
        i = next_i
        if "," not in block:
            continue
        key, rest = block.split(",", 1)
        key = key.strip()
        fields = parse_fields(rest)
        entries.append(BibEntry(entry_type=entry_type, key=key, fields=fields))
    return entries


def parse_fields(block: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    i = 0
    n = len(block)
    while i < n:
        while i < n and (block[i].isspace() or block[i] == ","):
            i += 1
        if i >= n:
            break

        k_start = i
        while i < n and re.match(r"[A-Za-z0-9_-]", block[i]):
            i += 1
        key = block[k_start:i].strip().lower()
        while i < n and block[i].isspace():
            i += 1
        if i >= n or block[i] != "=":
            while i < n and block[i] != ",":
                i += 1
            continue
        i += 1
        while i < n and block[i].isspace():
            i += 1
        if i >= n:
            break

        if block[i] == "{":
            value, i = _read_balanced(block, i, "{", "}")
        elif block[i] == '"':
            value, i = _read_balanced(block, i, '"', '"')
        else:
            v_start = i
            while i < n and block[i] not in ",\n":
                i += 1
            value = block[v_start:i].strip()

        fields[key] = _strip_wrapping(value)
    return fields


def latex_to_text(s: str) -> str:
    replacements = {
        r'{\"u}': "u",
        r'{\"U}': "U",
        r"\'e": "e",
        r"{\'e}": "e",
    }
    out = s
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out.replace("{", "").replace("}", "").strip()


def split_authors(author_field: str) -> List[str]:
    return [latex_to_text(a.strip()) for a in author_field.split(" and ") if a.strip()]


def to_display_author(name: str) -> str:
    n = name.strip()
    if "," in n:
        last, first = [p.strip() for p in n.split(",", 1)]
        n = f"{first} {last}".strip()
    return n


def canonical_name(name: str) -> str:
    return re.sub(r"\s+", "", name).replace(",", "").lower()


def maybe_bold_author(display_name: str) -> str:
    if canonical_name(display_name) in OWN_NAME_KEYS:
        return f"<strong>{escape(display_name)}</strong>"
    return escape(display_name)


def join_authors(display_authors: List[str]) -> str:
    if not display_authors:
        return ""
    if len(display_authors) == 1:
        return display_authors[0]
    if len(display_authors) == 2:
        return f"{display_authors[0]} and {display_authors[1]}"
    return ", ".join(display_authors[:-1]) + f", and {display_authors[-1]}"


def parse_month(v: str) -> int:
    vv = v.strip().lower().strip(".")
    return MONTH_ORDER.get(vv, 0)


def month_year_label(month_num: int, year: int) -> str:
    if year <= 0:
        return ""
    if month_num <= 0:
        return str(year)
    return f"{MONTH_LABEL[month_num]}, {year}"


def has_japanese(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text))


def get_section(entry: BibEntry) -> str:
    kw = [k.strip() for k in entry.fields.get("keywords", "").split(",") if k.strip()]
    kws = set(kw)
    if "award" in kws:
        return "awards"
    if "publication" in kws and "journal" in kws:
        joined = (entry.fields.get("title", "") + " " + entry.fields.get("journal", "")).strip()
        return "ja-journal" if has_japanese(joined) else "journal"
    if "publication" in kws and "int-conf-full" in kws:
        return "int-conf-full"
    if "publication" in kws and "int-conf-abst" in kws:
        return "int-conf-abst"
    if "publication" in kws and "dom-conf" in kws:
        return "dom-conf"
    return "misc"


def make_title_html(title: str, url: str) -> str:
    em = f"<em>{escape(title)}</em>"
    if url:
        return f'<a href="{escape(url)}">{em}</a>'
    return em


def build_display_html(entry: BibEntry, section_id: str) -> str:
    f = entry.fields
    title = latex_to_text(f.get("title", ""))
    url = f.get("url", "").strip()
    venue = latex_to_text(f.get("journal") or f.get("booktitle") or f.get("howpublished") or "")
    note = latex_to_text(f.get("note", ""))
    volume = latex_to_text(f.get("volume", ""))
    number = latex_to_text(f.get("number", ""))
    pages = latex_to_text(f.get("pages", ""))
    year = int(re.sub(r"[^\d]", "", f.get("year", "0")) or "0")
    month_num = parse_month(f.get("month", ""))
    date_label = month_year_label(month_num, year)

    if section_id == "awards":
        base = make_title_html(title, url)
        parts = [base]
        if venue:
            parts.append(escape(venue))
        if date_label:
            parts.append(escape(date_label))
        if note:
            parts.append(escape(note))
        return ", ".join(parts) + "."

    authors = split_authors(f.get("author", ""))
    display_authors = [maybe_bold_author(to_display_author(a)) for a in authors]
    author_html = join_authors(display_authors)
    title_html = make_title_html(title, url)

    details: List[str] = []
    if venue:
        details.append(f"<em>{escape(venue)}</em>")
    if volume:
        details.append(f"Vol. {escape(volume)}")
    if number:
        details.append(f"No. {escape(number)}")
    if pages:
        details.append(f"pp. {escape(pages)}")
    if note:
        details.append(escape(note))
    if date_label:
        details.append(escape(date_label))

    main = f"{author_html}, {title_html}"
    if details:
        main += ", " + ", ".join(details)
    return main + "."


def sort_key(item: Dict[str, object]) -> Tuple[int, int, str]:
    return (
        int(item.get("year", 0)),
        int(item.get("month_num", 0)),
        str(item.get("key", "")),
    )


def main() -> None:
    raw = BIB_PATH.read_text(encoding="utf-8")
    entries = parse_bibtex(raw)

    section_order = [
        ("journal", "Journal Papers"),
        ("ja-journal", "和文論文誌"),
        ("int-conf-full", "International Conferences (Full Papers)"),
        ("int-conf-abst", "International Conferences (Presentations / Abstracts)"),
        ("dom-conf", "国内学会・研究会"),
        ("misc", "Misc"),
        ("awards", "Awards"),
    ]

    grouped: Dict[str, List[Dict[str, object]]] = {sid: [] for sid, _ in section_order}
    for e in entries:
        sid = get_section(e)
        year = int(re.sub(r"[^\d]", "", e.fields.get("year", "0")) or "0")
        month_num = parse_month(e.fields.get("month", ""))
        grouped.setdefault(sid, []).append(
            {
                "key": e.key,
                "year": year,
                "month_num": month_num,
                "display_html": build_display_html(e, sid),
            }
        )

    sections = []
    for sid, title in section_order:
        items = sorted(grouped.get(sid, []), key=sort_key, reverse=True)
        sections.append(
            {
                "id": sid,
                "title": title,
                "items": items,
            }
        )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": str(BIB_PATH.name),
        "sections": sections,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(entries)} entries)")


if __name__ == "__main__":
    main()
