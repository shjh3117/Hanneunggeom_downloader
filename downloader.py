"""Core logic for downloading Korean History Proficiency Test past papers."""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional, Set

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://m.historyexam.go.kr"
LIST_PATH = "/pst/list.do"
DETAIL_PATH = "/pst/view.do"
DOWNLOAD_PATH = "/atchFile/FileDown.do"

DEFAULT_DELAY = 1.0

LEVEL_BASIC = "basic"
LEVEL_ADVANCED = "advanced"
LEVEL_UNKNOWN = "unknown"

DOC_TYPE_QUESTION = "question"
DOC_TYPE_ANSWER = "answer"

INVALID_FILENAME_CHARS = re.compile(r"[\\/*?:\"<>|]")


def configure_stdout() -> None:
    """Ensure stdout uses UTF-8 when possible for Korean output."""

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass


def create_session() -> requests.Session:
    """Create a requests session configured with retry/backoff."""

    session = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.setdefault(
        "User-Agent",
        "Mozilla/5.0 (compatible; KHPTDownloader/1.0)",
    )
    return session


def sanitize_filename(name: str) -> str:
    sanitized = INVALID_FILENAME_CHARS.sub("_", name).strip()
    sanitized = sanitized.replace("\u00a0", " ")
    sanitized = re.sub(r"\s+", " ", sanitized)
    return sanitized or "downloaded_file"


def fetch_list_page(session: requests.Session, page: int) -> str:
    params = {"bbs": "dat", "pageIndex": page}
    resp = session.get(BASE_URL + LIST_PATH, params=params)
    resp.raise_for_status()
    return resp.text


def determine_level(title: str) -> str:
    if "심화" in title:
        return LEVEL_ADVANCED
    if "기본" in title:
        return LEVEL_BASIC
    return LEVEL_UNKNOWN


def determine_exam_number(title: str) -> Optional[str]:
    match = re.search(r"제\s*(\d+)\s*회", title)
    if match:
        return match.group(1)
    match = re.search(r"(\d+)\s*회", title)
    if match:
        return match.group(1)
    return None


def parse_entries(html: str) -> List[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table.type_table tbody tr")
    entries = []
    for row in rows:
        link = row.select_one("a[onclick]")
        if not link:
            continue
        onclick = link.get("onclick", "")
        match = re.search(r"fn_goDetail\('(?P<id>\d+)'", onclick)
        if not match:
            continue
        entry_id = match.group("id")
        title = link.get_text(strip=True)
        tds = row.select("td")
        exam_date = tds[2].get_text(strip=True) if len(tds) >= 3 else ""
        entries.append(
            {
                "id": entry_id,
                "title": title,
                "date": exam_date,
                "level": determine_level(title),
                "exam_no": determine_exam_number(title),
            }
        )
    return entries


def fetch_detail_page(session: requests.Session, entry_id: str) -> str:
    params = {"bbs": "dat", "pst_sno": entry_id}
    resp = session.get(BASE_URL + DETAIL_PATH, params=params)
    resp.raise_for_status()
    return resp.text


def determine_document_type(name: str) -> str:
    lowered = name.lower()
    if "정답" in name or "답지" in name or "answer" in lowered:
        return DOC_TYPE_ANSWER
    return DOC_TYPE_QUESTION


def infer_level(entry_level: str, name: str) -> str:
    if entry_level != LEVEL_UNKNOWN:
        return entry_level
    if "심화" in name:
        return LEVEL_ADVANCED
    if "기본" in name:
        return LEVEL_BASIC
    return LEVEL_UNKNOWN


def build_target_filename(entry: dict, attachment: dict) -> str:
    raw_name = attachment.get("file_name", "") or attachment.get("file_id", "")
    extension = Path(raw_name).suffix or ".pdf"
    if not extension.startswith("."):
        extension = f".{extension}"
    exam_no = entry.get("exam_no")
    level = infer_level(entry.get("level", LEVEL_UNKNOWN), raw_name)
    level_label_map = {
        LEVEL_BASIC: "기본",
        LEVEL_ADVANCED: "심화",
    }
    level_label = level_label_map.get(level)
    doc_type = determine_document_type(raw_name)
    doc_label = "문제지" if doc_type == DOC_TYPE_QUESTION else "정답표"
    if exam_no:
        if level_label:
            base_name = f"{exam_no}회 한국사_{doc_label}({level_label})"
        else:
            base_name = f"{exam_no}회 한국사_{doc_label}"
    else:
        base_name = raw_name.rsplit("/", 1)[-1]
    candidate = f"{base_name}{'' if base_name.endswith(extension) else extension}"
    sanitized = sanitize_filename(candidate)
    if not sanitized.lower().endswith(extension.lower()):
        sanitized = f"{sanitized}{extension}"
    return sanitized


def parse_attachments(detail_html: str) -> List[dict]:
    soup = BeautifulSoup(detail_html, "html.parser")
    attachments = []
    for link in soup.select("div.file a[onclick]"):
        onclick = link.get("onclick", "")
        match = re.search(r"fnFileDownload\('(?P<file_id>[^']+)'", onclick)
        if not match:
            continue
        file_id = match.group("file_id")
        raw_name = link.get_text(strip=True)
        if ":" in raw_name:
            _, _, remainder = raw_name.partition(":")
            file_name = remainder.strip()
        else:
            file_name = file_id
        attachments.append({"file_id": file_id, "file_name": file_name})
    return attachments


def stream_download(session: requests.Session, file_id: str, destination: Path) -> None:
    params = {"atch_file_id": file_id}
    with session.get(BASE_URL + DOWNLOAD_PATH, params=params, stream=True) as resp:
        resp.raise_for_status()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            for chunk in resp.iter_content(chunk_size=1 << 14):
                if chunk:
                    handle.write(chunk)


def format_entry(entry: dict) -> str:
    date = entry.get("date")
    prefix = f"[{date}] " if date else ""
    return f"{prefix}{entry.get('title', '')}"


def download_past_exams(
    dest: Path,
    max_pages: Optional[int],
    overwrite: bool,
    delay: float,
    levels: Optional[Set[str]],
) -> int:
    configure_stdout()
    session = create_session()
    total_downloaded = 0
    page = 1
    while True:
        if max_pages is not None and page > max_pages:
            break
        list_html = fetch_list_page(session, page)
        entries = parse_entries(list_html)
        if not entries:
            break
        print(f"Processing page {page} with {len(entries)} entries...")
        for entry in entries:
            title_display = format_entry(entry)
            level = entry.get("level", LEVEL_UNKNOWN)
            if levels and level not in levels:
                print(f"  Skipping entry: {title_display} (level {level})")
                continue
            print(f"  Exam entry: {title_display}")
            try:
                detail_html = fetch_detail_page(session, entry["id"])
            except requests.exceptions.RequestException as exc:
                print(f"    Failed to load detail page: {exc}")
                continue
            attachments = parse_attachments(detail_html)
            if not attachments:
                print("    No attachments found; skipping.")
                continue
            for attachment in attachments:
                target_name = build_target_filename(entry, attachment)
                destination = dest / target_name
                if destination.exists() and not overwrite:
                    print(f"    Skipping existing file: {destination.name}")
                    continue
                print(f"    Downloading {destination.name}...")
                try:
                    stream_download(session, attachment["file_id"], destination)
                except (requests.exceptions.RequestException, OSError) as exc:
                    print(f"    Failed to download {destination.name}: {exc}")
                    if destination.exists():
                        destination.unlink(missing_ok=True)
                    continue
                total_downloaded += 1
                if delay > 0:
                    time.sleep(delay)
        if delay > 0:
            time.sleep(delay)
        page += 1
    return total_downloaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download publicly available past exam papers and answer sheets "
            "for the Korean History Proficiency Test from historyexam.go.kr."
        )
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("downloads"),
        help="Directory where files will be saved (default: ./downloads)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limit the number of list pages to crawl (default: all pages)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help="Seconds to sleep between requests (default: 1.0)",
    )
    parser.add_argument(
        "--levels",
        nargs="+",
        choices=[LEVEL_BASIC, LEVEL_ADVANCED],
        default=None,
        help="Filter by level (basic and/or advanced). Default: both.",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    dest: Path = args.dest.expanduser().resolve()
    delay: float = max(args.delay, 0.0) if args.delay is not None else DEFAULT_DELAY
    selected_levels: Optional[Set[str]] = set(args.levels) if args.levels else None
    downloaded = download_past_exams(dest, args.max_pages, True, delay, selected_levels)
    print(f"Finished. Downloaded {downloaded} new file(s) to {dest}.")


__all__ = [
    "DEFAULT_DELAY",
    "LEVEL_BASIC",
    "LEVEL_ADVANCED",
    "LEVEL_UNKNOWN",
    "DOC_TYPE_QUESTION",
    "DOC_TYPE_ANSWER",
    "download_past_exams",
    "build_parser",
    "main",
]


if __name__ == "__main__":
    main()
