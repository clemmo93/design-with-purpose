#!/usr/bin/env python3
"""Pull live design roles from every company in data/companies.json that uses an
ATS with a public job-board API, and write them to data/jobs_ats.json.

Usage: python3 scripts/fetch_ats.py [--all-titles]
"""
import concurrent.futures as cf
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = {"User-Agent": "Mozilla/5.0 (job-search helper; personal use)"}
TODAY = date.today().isoformat()

DESIGN_RE = re.compile(
    r"\b(product design|ux|ui|user experience|interaction design|service design|"
    r"experience design|digital design|designer)\b", re.I)
EXCLUDE_RE = re.compile(
    r"\b(graphic|motion|brand designer|marketing designer|packaging|interior|fashion|"
    r"engineer|architect|mechanical|electrical|instructional|game|print|retail design|"
    r"landscape|hardware|industrial|solutions design|system design|clothing|footwear|garment|textile|content design(?:er)?|researcher|3d|multimedia|web design and|website design|copywriter)\b", re.I)


def get(url, as_json=True, timeout=45, retries=3):
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            return json.loads(body) if as_json else body
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == retries:
                raise
            time.sleep(5 * (attempt + 1))  # Workable rate-limits bursts


def strip_html(s):
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# --- per-provider fetchers: each returns list of dicts {title, url, location, text, posted, salary}

def greenhouse(slug):
    d = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    return [{"title": j["title"], "url": j["absolute_url"],
             "location": (j.get("location") or {}).get("name", ""),
             "text": strip_html(j.get("content", "")),
             "posted": (j.get("updated_at") or "")[:10]} for j in d.get("jobs", [])]


def lever(slug):
    d = get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    out = []
    for j in d:
        cats = j.get("categories") or {}
        sal = j.get("salaryRange") or {}
        out.append({"title": j["text"], "url": j["hostedUrl"],
                    "location": cats.get("location", "") + (" " + j.get("workplaceType", "") if j.get("workplaceType") else ""),
                    "text": j.get("descriptionPlain", "") + " " + strip_html(" ".join(l.get("content", "") for l in j.get("lists", []))),
                    "posted": date.fromtimestamp(j["createdAt"] / 1000).isoformat() if j.get("createdAt") else None,
                    "salary": f"{sal.get('currency','')} {sal.get('min')}–{sal.get('max')}" if sal.get("min") else None})
    return out


def ashby(slug):
    d = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
    out = []
    for j in d.get("jobs", []):
        comp = (j.get("compensation") or {}).get("compensationTierSummary")
        loc = j.get("location", "")
        if j.get("isRemote"):
            loc += " (Remote)"
        if j.get("workplaceType"):
            loc += f" {j['workplaceType']}"
        out.append({"title": j["title"], "url": j.get("jobUrl"), "location": loc,
                    "text": j.get("descriptionPlain") or strip_html(j.get("descriptionHtml", "")),
                    "posted": (j.get("publishedAt") or "")[:10], "salary": comp})
    return out


def workable(slug):
    d = get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true")
    out = []
    for j in d.get("jobs", []):
        loc = ", ".join(x for x in [j.get("city"), j.get("country")] if x)
        if j.get("telecommuting"):
            loc += " (Remote)"
        out.append({"title": j["title"], "url": j.get("url") or j.get("shortlink"), "location": loc,
                    "text": strip_html(j.get("description", "")), "posted": (j.get("published_on") or "")[:10]})
    return out


def smartrecruiters(slug):
    d = get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100")
    out = []
    for j in d.get("content", []):
        l = j.get("location") or {}
        loc = ", ".join(x for x in [l.get("city"), l.get("country")] if x)
        if l.get("remote"):
            loc += " (Remote)"
        out.append({"title": j["name"], "url": f"https://jobs.smartrecruiters.com/{slug}/{j['id']}",
                    "location": loc, "text": "", "posted": (j.get("releasedDate") or "")[:10]})
    return out


def recruitee(slug):
    d = get(f"https://{slug}.recruitee.com/api/offers/")
    return [{"title": j["title"], "url": j.get("careers_url"), "location": j.get("location", "") + (" (Remote)" if j.get("remote") else ""),
             "text": strip_html(j.get("description", "") + " " + j.get("requirements", "")),
             "posted": (j.get("published_at") or "")[:10]} for j in d.get("offers", [])]


def personio(slug):
    root = ET.fromstring(get(f"https://{slug}.jobs.personio.de/xml", as_json=False))
    out = []
    for p in root.findall("position"):
        desc = " ".join(strip_html(v.findtext("value", "")) for v in p.findall("jobDescriptions/jobDescription"))
        out.append({"title": p.findtext("name", ""), "url": f"https://{slug}.jobs.personio.de/job/{p.findtext('id')}",
                    "location": p.findtext("office", ""), "text": desc, "posted": (p.findtext("createdAt") or "")[:10]})
    return out


def pinpoint(slug):
    d = get(f"https://{slug}.pinpointhq.com/postings.json")
    out = []
    for j in d.get("data", []):
        loc = (j.get("location") or {}).get("name", "")
        if j.get("workplace_type"):
            loc += f" {j['workplace_type']}"
        out.append({"title": j["title"], "url": j.get("url"), "location": loc,
                    "text": strip_html(j.get("description", "")), "salary": j.get("compensation"),
                    "posted": None})
    return out


def teamtailor(slug):
    host = slug if "." in slug else f"{slug}.teamtailor.com"  # some use a custom careers domain
    root = ET.fromstring(get(f"https://{host}/jobs.rss", as_json=False))
    out = []
    for it in root.iter("item"):
        locs = [e.text for e in it.iter() if e.tag.endswith("location") and e.text]
        out.append({"title": it.findtext("title", ""), "url": it.findtext("link", ""),
                    "location": ", ".join(locs), "text": strip_html(it.findtext("description", "")),
                    "posted": None})
    return out


FETCHERS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby, "workable": workable,
            "smartrecruiters": smartrecruiters, "recruitee": recruitee, "personio": personio,
            "pinpoint": pinpoint, "teamtailor": teamtailor}


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def fetch_company(c):
    ats = c.get("ats") or {}
    fn = FETCHERS.get((ats.get("provider") or "").lower())
    if not fn or not ats.get("slug"):
        return c["id"], None, "no-api"
    try:
        return c["id"], fn(ats["slug"]), "ok"
    except Exception as e:  # noqa: BLE001 — one bad board shouldn't kill the run
        return c["id"], None, f"error: {e}"


def main():
    all_titles = "--all-titles" in sys.argv
    companies = json.loads((DATA / "companies.json").read_text())
    by_id = {c["id"]: c for c in companies}
    jobs, status = [], {}
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        for cid, postings, st in ex.map(fetch_company, companies):
            status[cid] = {"status": st, "total": len(postings or []), "design": 0}
            for p in postings or []:
                if not all_titles and (not DESIGN_RE.search(p["title"]) or EXCLUDE_RE.search(p["title"])):
                    continue
                c = by_id[cid]
                status[cid]["design"] += 1
                jobs.append({
                    "id": f"{cid}-{slugify(p['title'])}",
                    "title": p["title"].strip(), "company_id": cid, "company_name": c["name"],
                    "apply_url": p["url"], "source": f"{c['ats']['provider']}-api", "source_url": c.get("careers_url"),
                    "location": (p.get("location") or "").strip(), "salary": p.get("salary"),
                    "posted": p.get("posted") or None, "closes": None,
                    "description": p.get("text", "")[:6000],
                    "sectors": c.get("sectors", []), "purpose_score": c.get("purpose_score"),
                    "people": [], "verified_open": True, "checked": TODAY,
                })
    (DATA / "jobs_ats.json").write_text(json.dumps(jobs, indent=1, ensure_ascii=False))
    (DATA / "ats_status.json").write_text(json.dumps(status, indent=1))
    ok = sum(1 for s in status.values() if s["status"] == "ok")
    errs = {k: v["status"] for k, v in status.items() if v["status"].startswith("error")}
    print(f"boards fetched ok: {ok}/{len(companies)}; design roles: {len(jobs)}")
    for k, v in errs.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
