#!/usr/bin/env python3
"""Pull design roles from job boards that expose a usable feed, and write
data/jobs_boards.json. Currently: Getro-powered VC portfolio boards and NHS Jobs.

Usage: python3 scripts/fetch_boards.py
"""
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_ats import DESIGN_RE, EXCLUDE_RE, UA, get, slugify, strip_html  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
TODAY = date.today().isoformat()

# id -> (name, default purpose score for portfolio companies not in the register, sectors)
GETRO_BOARDS = {
    1426: ("Planet A", 4, ["climate"]),
    1287: ("2150", 4, ["climate"]),
    253: ("Energy Impact Partners", 4, ["energy-transition"]),
    4217: ("Norrsken", 4, ["social-impact"]),
    634: ("All Hands", 4, ["social-impact"]),
    4580: ("Octopus Ventures", 2, []),
    221: ("Kindred", 2, []),
    36986: ("Atomico", 2, []),
}
QUERIES = ["product designer", "ux designer", "ui designer", "ux/ui designer", "junior designer", "associate designer", "digital designer", "service designer", "interaction designer"]
UK_RE = re.compile(r"united kingdom|, uk\b|england|london|remote", re.I)


def post_json(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={**UA, "Accept": "application/json", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def getro():
    out, seen = [], set()
    for bid, (board, purpose, sectors) in GETRO_BOARDS.items():
        for q in QUERIES:
            try:
                d = post_json(f"https://api.getro.com/api/v2/collections/{bid}/search/jobs",
                              {"hitsPerPage": 50, "page": 0, "filters": "", "query": q})
            except Exception as e:  # noqa: BLE001
                print(f"getro {board} '{q}': {e}")
                continue
            for j in d.get("results", {}).get("jobs", []):
                locs = j.get("searchable_locations") or []
                remote = j.get("work_mode") == "remote"
                if not any("United Kingdom" in l for l in locs) and not (remote and any("Europe" in l for l in locs)):
                    continue
                if not DESIGN_RE.search(j["title"]) or EXCLUDE_RE.search(j["title"]):
                    continue
                org = j.get("organization") or {}
                key = (org.get("name"), j["title"])
                if key in seen:
                    continue
                seen.add(key)
                uk_locs = [l for l in locs if "UK" in l and "," in l][:1] or ["United Kingdom"]
                wm = {"remote": "remote", "hybrid": "hybrid", "on_site": "unknown"}.get(j.get("work_mode"), "unknown")
                lo, hi = j.get("compensation_amount_min_cents"), j.get("compensation_amount_max_cents")
                cur = j.get("compensation_currency") or ""
                out.append({
                    "id": f"{slugify(org.get('name',''))}-{slugify(j['title'])}",
                    "title": j["title"], "company_id": slugify(org.get("name", "")), "company_name": org.get("name", ""),
                    "apply_url": j.get("url"), "source": f"getro:{board}", "source_url": j.get("url"),
                    "location": uk_locs[0] + (" (Remote)" if remote else ""), "work_model": wm,
                    "salary": f"{cur} {lo // 100:,}–{hi // 100:,}" if lo and hi else None,
                    "posted": datetime.fromtimestamp(j["created_at"], timezone.utc).date().isoformat() if j.get("created_at") else None,
                    "sectors": sectors, "purpose_score": purpose, "people": [],
                    "verified_open": True, "checked": TODAY,
                })
    return out


def nhs():
    out = []
    for q in ["product designer", "user experience designer", "ux designer", "ui designer", "interaction designer", "junior designer"]:
        url = "https://www.jobs.nhs.uk/api/v1/search_xml?" + urllib.parse.urlencode({"keyword": q})
        try:
            root = ET.fromstring(get(url, as_json=False))
        except Exception as e:  # noqa: BLE001
            print(f"nhs '{q}': {e}")
            continue
        for v in root.iter("vacancyDetails"):
            title = v.findtext("title", "")
            if not DESIGN_RE.search(title) or EXCLUDE_RE.search(title):
                continue
            emp = v.findtext("employer", "NHS")
            out.append({
                "id": f"{slugify(emp)}-{slugify(title)}", "title": title, "company_id": slugify(emp), "company_name": emp,
                "apply_url": v.findtext("url"), "source": "nhs-jobs-api", "source_url": v.findtext("url"),
                "location": ", ".join(filter(None, [v.findtext("locations/location"), v.findtext("location")])) or "",
                "salary": v.findtext("salary"), "posted": (v.findtext("postDate") or "")[:10] or None,
                "closes": (v.findtext("closeDate") or "")[:10] or None,
                "description": strip_html(v.findtext("description", "")),
                "sectors": ["health"], "purpose_score": 4, "people": [], "verified_open": True, "checked": TODAY,
            })
    return out


HP_SECTORS = {  # Hard Problems category -> (our sectors, purpose score)
    "climate": (["climate"], 5), "energy": (["energy-transition"], 5), "nature": (["nature-rewilding"], 5),
    "health": (["health"], 4), "education": (["education"], 4), "public services": (["civic-tech"], 4),
    "good government": (["civic-tech"], 4), "social impact": (["social-impact"], 4), "nonprofit": (["charity"], 5),
    "charity": (["charity"], 5), "economic opportunity": (["social-impact"], 4), "food": (["sustainable-food"], 4),
    "other": ([], 2),
}
HP_DESIGN = {"product design", "service design", "interaction design", "ux design", "ui design", "ux/ui design", "content design", "design"}
HP_LEVEL = {"junior": "junior", "entry": "junior", "mid": "mid", "mid-level": "mid", "senior": "senior", "staff": "lead", "lead": "lead", "principal": "lead", "director": "lead", "head": "lead"}


def hard_problems():
    """Hard Problems: nonprofit board for designers on climate, health, education, public services."""
    req = urllib.request.Request("https://www.hardproblems.com/jobs/feed.xml", headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        root = ET.fromstring(r.read())
    out = []
    for it in root.iter("item"):
        cats = [(c.text or "").strip() for c in it.findall("category")]
        lc = [c.lower() for c in cats]
        title_full = it.findtext("title", "")
        title, _, org = title_full.rpartition(" at ")
        title = title or title_full
        if not (any(c in HP_DESIGN for c in lc) or DESIGN_RE.search(title)) or EXCLUDE_RE.search(title):
            continue
        paras = [strip_html(x) for x in re.findall(r"<p>(.*?)</p>", it.findtext("description", ""), re.S)]
        desc = " ".join(paras)
        tail = paras[-1] if paras and "·" in paras[-1] else ""
        parts = [p.strip() for p in tail.split("·")] if tail else []
        loc = parts[0] if parts else ""
        if not re.search(r"\b(UK|United Kingdom|England|London|Scotland|Wales|Remote)\b", loc):
            continue
        if re.search(r"\bRemote\b", loc) and not re.search(r"UK|United Kingdom|England|London|Europe", loc):
            continue
        sectors, purpose = [], 3
        for c in lc:
            if c in HP_SECTORS:
                s, p = HP_SECTORS[c]
                sectors += s
                purpose = max(purpose, p) if c != "other" else purpose
        if "other" in lc and not sectors:
            purpose = 2
        wm = next((p.lower().split(" (")[0] for p in parts if p.lower().split(" (")[0] in ("hybrid", "remote", "on-site", "onsite", "in office", "in-person")), None)
        wm = {"on-site": "office", "onsite": "office", "in office": "office", "in-person": "office"}.get(wm, wm)
        salary = next((p for p in parts if "£" in p or "$" in p or "€" in p), None)
        closes = next((p.replace("Apply by ", "") for p in parts if p.startswith("Apply by")), None)
        if closes:
            try:
                closes = datetime.strptime(closes, "%d %b %Y").date().isoformat()
            except ValueError:
                pass
        pub = it.findtext("pubDate")
        try:
            posted = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z").date().isoformat() if pub else None
        except ValueError:
            posted = None
        level = next((HP_LEVEL[c] for c in lc if c in HP_LEVEL), None)
        out.append({
            "id": f"{slugify(org)}-{slugify(title)}", "title": title, "company_id": slugify(org), "company_name": org,
            "apply_url": it.findtext("guid") if (it.findtext("guid") or "").startswith("http") else it.findtext("link"),
            "source": "hard-problems-rss", "source_url": it.findtext("link"),
            "location": loc + (" (Remote)" if wm == "remote" and "remote" not in loc.lower() else ""),
            "work_model": wm, "salary": salary, "seniority": level, "posted": posted, "closes": closes,
            "description": desc, "role_summary": paras[1] if len(paras) > 2 else (paras[0] if paras else None),
            "sectors": sorted(set(sectors)), "purpose_score": purpose, "people": [],
            "verified_open": not (closes and closes < TODAY), "checked": TODAY,
        })
    return out


def main():
    jobs = getro() + nhs() + hard_problems()
    (DATA / "jobs_boards.json").write_text(json.dumps(jobs, indent=1, ensure_ascii=False))
    print(f"board roles: {len(jobs)}")


if __name__ == "__main__":
    main()
