"""AGENTS.md parsing, routine classification and announcement parsing."""

import pytest

from backend.news.client import attachment_url
from backend.news.ingest import is_routine, parse_announcement
from backend.news.subagent import AGENT_FILE, load_agent_file, parse_agent_file

# Field names/types as returned live by BSE (CRITICALNEWS is a string there).
RAW = {
    "NEWSID": "25f3312c-2c87-4aad-8564-22db915a9103",
    "SCRIP_CD": 532540,
    "NEWSSUB": "Announcement under Regulation 30 (LODR)-Acquisition",
    "DT_TM": "2026-10-01T18:41:45.643",
    "NEWS_DT": "2026-10-01T18:41:45.643",
    "CRITICALNEWS": "1",
    "ATTACHMENTNAME": "b9aa9da2-26fd-47a3-b7fc-c4960b515818.pdf",
    "HEADLINE": "Tata Consultancy Services Limited has<BR>informed the Exchange about the Acquisition",
    "CATEGORYNAME": "Company Update",
    "PDFFLAG": 0,
    "SLONGNAME": "Tata Consultancy Services Ltd",
    "SUBCATNAME": "Acquisition",
}


def test_parse_real_agents_file():
    meta, body = load_agent_file(AGENT_FILE)
    assert meta["name"] == "news-analyst"
    assert "announcements" in meta["description"]
    assert "never invent" in body.lower()


def test_parse_agent_file_rejects_bad_frontmatter():
    with pytest.raises(ValueError):
        parse_agent_file("no frontmatter here")
    with pytest.raises(ValueError, match="description"):
        parse_agent_file("---\nname: x\n---\nprompt")
    with pytest.raises(ValueError, match="empty"):
        parse_agent_file("---\nname: x\ndescription: y\n---\n   ")


def test_parse_agent_file_keeps_dashes_in_body():
    meta, body = parse_agent_file("---\nname: a\ndescription: b\n---\nline one\n---\nline two")
    assert meta == {"name": "a", "description": "b"}
    assert body == "line one\n---\nline two"


@pytest.mark.parametrize("subject", [
    "Closure of Trading Window",
    "Compliances-Certificate under Reg. 74 (5) of SEBI (DP) Regulations, 2018",
    "Compliances-Reg. 39 (3) - Details of Loss of Certificate / Duplicate Certificate",
    "Announcement under Regulation 30 (LODR)-Newspaper Publication",
])
def test_routine_filings_flagged(subject):
    assert is_routine(subject)


@pytest.mark.parametrize("subject", [
    "Announcement under Regulation 30 (LODR)-Acquisition",
    "Board Meeting Outcome for Financial Results For Quarter Ended June 2026",
    "Corp. Action-Dividend",
])
def test_material_filings_not_flagged(subject):
    assert not is_routine(subject)


def test_routine_matches_any_field_case_insensitively():
    assert is_routine("General Update", None, "NEWSPAPER PUBLICATION")
    assert not is_routine(None, "", None)


def test_attachment_url_depends_on_pdf_flag():
    assert attachment_url("a.pdf", 0) == "https://www.bseindia.com/xml-data/corpfiling/AttachLive/a.pdf"
    assert attachment_url("a.pdf", "1") == "https://www.bseindia.com/xml-data/corpfiling/AttachHis/a.pdf"
    assert attachment_url("", 0) == ""


def test_parse_announcement_maps_live_fields():
    row = parse_announcement(RAW, "TCS", "Tata Consultancy Services Ltd.")
    assert row["id"] == RAW["NEWSID"]
    assert row["scrip_code"] == "532540"
    assert row["symbol"] == "TCS"
    assert row["headline"] == "Tata Consultancy Services Limited has informed the Exchange about the Acquisition"
    assert row["category"] == "Company Update"
    assert row["subcategory"] == "Acquisition"
    assert row["published_at"].isoformat().startswith("2026-10-01T18:41:45")
    assert row["pdf_url"].endswith("/AttachLive/b9aa9da2-26fd-47a3-b7fc-c4960b515818.pdf")
    assert row["is_critical"] is True
    assert row["is_routine"] is False


def test_parse_announcement_handles_nulls():
    raw = dict(RAW, CATEGORYNAME=None, ATTACHMENTNAME="", CRITICALNEWS=0, PDFFLAG=None)
    row = parse_announcement(raw)
    assert row["category"] == ""
    assert row["pdf_url"] == ""
    assert row["is_critical"] is False
    assert row["company_name"] == "Tata Consultancy Services Ltd"
