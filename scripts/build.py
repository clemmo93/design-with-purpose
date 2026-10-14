#!/usr/bin/env python3
"""Merge every job source, normalise + score each role, and write
data/dashboard.json (consumed by dashboard/index.html).

Usage: python3 scripts/build.py
"""
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_ats import EXCLUDE_RE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
JOB_FILES = ["jobs_top_product.json", "jobs_ats.json", "jobs_boards.json", "jobs_aggregators.json", "jobs_linkedin.json", "jobs_junior.json", "jobs_linkedin_auth.json", "jobs_manual.json"]
SOURCE_PRIORITY = {"api": 0, "aggregator": 1, "linkedin": 2}  # lower wins on dedupe

# Rough region map: towns within ~2h of London grouped by region.
REGIONS = {
    "London": ["london", "shoreditch", "kings cross", "king's cross", "camden", "islington", "hackney", "southwark", "westminster", "croydon", "stratford", "greenwich"],
    "South East": ["brighton", "hove", "oxford", "reading", "guildford", "milton keynes", "southampton", "portsmouth", "canterbury", "maidstone", "crawley", "slough", "woking", "farnborough", "basingstoke", "winchester", "chichester", "horsham", "tunbridge", "sevenoaks", "high wycombe", "bracknell", "newbury", "didcot", "abingdon", "harwell", "kent", "surrey", "sussex", "hampshire", "berkshire", "buckinghamshire"],
    "South West": ["bristol", "bath", "swindon", "exeter", "cheltenham", "gloucester", "plymouth", "bournemouth", "poole", "taunton", "cornwall", "devon", "somerset", "wiltshire", "dorset", "salisbury", "stroud", "falmouth", "truro", "totnes"],
    "East / ≤2h": ["cambridge", "chelmsford", "colchester", "norwich", "ipswich", "st albans", "watford", "luton", "hertford", "stevenage", "letchworth", "bedford", "peterborough", "hertfordshire", "essex"],
    "Midlands / ≤2h": ["birmingham", "coventry", "leamington", "warwick", "northampton", "leicester", "nottingham", "derby"],
    "North / Far": ["manchester", "leeds", "sheffield", "liverpool", "newcastle", "york", "edinburgh", "glasgow", "cardiff", "belfast", "aberdeen", "dundee", "lancaster", "preston", "hull"],
}
NON_UK = re.compile(r"\b(usa|united states|new york|san francisco|california|berlin|germany|paris|france|amsterdam|netherlands|spain|madrid|barcelona|valencia|lisbon|portugal|dublin|ireland|india|philippines|manila|south africa|new zealand|japan|korea|china|hong kong|italy|milan|rome|belgium|brussels|switzerland|austria|sweden|norway|denmark|finland|estonia|czech|prague|romania|bucharest|greece|athens|turkey|istanbul|israel|tel aviv|egypt|cairo|argentina|colombia|chile|bangalore|singapore|sydney|australia|toronto|canada|austin|seattle|boston|chicago|denver|stockholm|copenhagen|oslo|helsinki|warsaw|poland|munich|zurich|vienna|tallinn|remote - us|us remote|latam|brazil|mexico|nairobi|kenya|lagos|cape town|tokyo|dubai)\b", re.I)
UK = re.compile(r"\b(uk|united kingdom|england|britain|gb|scotland|wales)\b", re.I)
WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


def text_of(j):
    return " ".join(str(j.get(k) or "") for k in ("title", "location", "work_model", "description", "role_summary"))


def region_for(loc):
    l = (loc or "").lower()
    for region, towns in REGIONS.items():
        if any(t in l for t in towns):
            return region
    if (NON_UK.search(l) or re.search(r"\((?:es|it|de|fr|us|nl|pt|pl|ie|se|dk|in|au|ca|jp|be|ch|at)\)", l)) and not UK.search(l):
        return "Non-UK"
    if re.search(r"remote", l):
        return "Remote UK"
    if UK.search(l):
        return "UK (unspecified)"
    return "Unknown"


def infer_office_days(t):
    m = re.search(r"\b(\d|one|two|three|four|five)\s*(?:\(\d\)\s*)?(?:days?|x)\s*(?:a|per|each|/)?\s*week", t, re.I) \
        or re.search(r"\b(\d|one|two|three|four|five)\s*days?\s*(?:in|at|from)\s*(?:the|our)?\s*(?:office|studio|hq)", t, re.I)
    if not m:
        return None
    v = m.group(1).lower()
    n = WORDNUM.get(v, int(v) if v.isdigit() else None)
    return n if n is not None and 0 < n <= 5 else None


def infer_work_model(j, t):
    wm = (j.get("work_model") or "").lower()
    if wm in ("remote", "hybrid", "office"):
        return wm
    tl = t.lower()
    loc = (j.get("location") or "").lower()
    if "hybrid" in loc or "hybrid" in tl:
        return "hybrid"
    if "remote" in loc or re.search(r"fully remote|remote[- ]first|remote working|work remotely|100% remote", tl):
        return "remote"
    if re.search(r"on[- ]?site|in[- ]office|office[- ]based", loc + " " + tl):
        return "office"
    return "unknown"


def infer_seniority(j, t):
    s = (j.get("seniority") or "").lower()
    title = j.get("title", "").lower()
    if re.search(r"\b(head of|director|vp|principal|staff)\b", title):
        return "lead"
    if re.search(r"\b(lead)\b", title):
        return "lead"
    if re.search(r"\b(senior|sr\.?)\b", title):
        return "senior"
    if re.search(r"\b(junior|jr\.?|graduate|entry|associate|apprentice|intern)\b", title):
        return "junior"
    if s in ("junior", "mid", "senior", "lead"):
        return s
    if re.search(r"\b(mid[- ]?(level|weight)?|intermediate)\b", title):
        return "mid"
    return "mid" if re.search(r"\bproduct designer\b|\bux designer\b|\bui designer\b|\bdesigner\b", title) else "unknown"


def infer_years(j, t):
    if j.get("years_experience"):
        return str(j["years_experience"])
    m = re.search(r"(\d+)\s*(?:-|–|to)\s*(\d+)\+?\s*years", t) or re.search(r"(\d+)\+?\s*years", t)
    if not m:
        return None
    return "-".join(m.groups()) if m.lastindex == 2 else f"{m.group(1)}+"


def min_years(y):
    m = re.match(r"(\d+)", y or "")
    return int(m.group(1)) if m else None


# --- Scoring rules: one source of truth, also exported to the page's "Scoring" tab ---
PURPOSE_PTS = {5: 40, 4: 32, 3: 20, 2: 10, 1: 0}
PURPOSE_MEANING = {
    5: "Positive change is the mission itself: charities, climate and nature organisations, public-good services.",
    4: "Purpose-led business where the product drives the change: energy transition, climate tech, health for good, B Corps.",
    3: "Purpose-adjacent: some positive impact, but commercial goals lead.",
    2: "No clear purpose, or not yet assessed.",
    1: "No positive-change angle.",
}
IN_AREA = ["London", "South East", "South West", "East / ≤2h", "Midlands / ≤2h", "Remote UK", "UK (unspecified)"]
WORK_RULES = [  # (key, label, points) in the order they're checked
    ("remote", "Fully remote (UK)", 30),
    ("hybrid_le2", "Hybrid, 2 or fewer office days, within ~2h of London", 30),
    ("hybrid_unstated", "Hybrid, office days not stated, within ~2h of London", 22),
    ("unstated", "Work pattern not stated, within ~2h of London", 15),
    ("hybrid_3plus", "Hybrid, 3+ office days, within ~2h of London", 12),
    ("hybrid_far", "Hybrid, office further than ~2h from London", 6),
    ("office", "Office-based, within ~2h of London", 5),
    ("far", "Office-based or not stated, further than ~2h from London", 5),
]
WORK_PTS = {k: v for k, _, v in WORK_RULES}
LEVEL_PTS = {"junior": 30, "mid": 30, "senior": 15, "lead": 4, "unknown": 20}
LEVEL_MEANING = {
    "junior": "Junior, associate or graduate in the title",
    "mid": "Product/UX Designer with no level, or mid-weight",
    "senior": "Senior in the title",
    "lead": "Lead, principal, staff, head of, director",
    "unknown": "Couldn't tell from the posting",
}
YEARS_CAP = [(3, 30, "Asks for 3 years or fewer: no cap"), (5, 22, "Asks for 4–5 years: level points capped at 22"), (99, 8, "Asks for 6+ years: capped at 8")]
TIERS = [("strong", 80, "Strong"), ("good", 62, "Good"), ("stretch", 0, "Stretch")]


def work_key(wm, days, reg):
    in_area = reg in IN_AREA
    if wm == "remote":
        return "remote"
    if wm == "hybrid":
        if not in_area:
            return "hybrid_far"
        if days is None:
            return "hybrid_unstated"
        return "hybrid_le2" if days <= 2 else "hybrid_3plus"
    if wm == "office":
        return "office" if in_area else "far"
    return "unstated" if in_area else "far"


def score(job, company):
    purpose = job.get("purpose_score") or (company or {}).get("purpose_score") or 2
    p = PURPOSE_PTS.get(int(purpose), 10)
    if job.get("top_product"):
        p = max(p, PURPOSE_PTS[3])  # a top product company earns purpose-3 points without inflating its leaves
    loc = WORK_PTS[work_key(job["work_model"], job["office_days"], job["region"])]
    sen = LEVEL_PTS[job["seniority"]]
    my = min_years(job.get("years_experience"))
    if my is not None:
        sen = min(sen, next(cap for limit, cap, _ in YEARS_CAP if my <= limit))
    return p + loc + sen, {"purpose": p, "location": loc, "seniority": sen}


def score_rules():
    return {
        "purpose": [{"score": k, "points": v, "meaning": PURPOSE_MEANING[k]} for k, v in PURPOSE_PTS.items()],
        "work": [{"key": k, "label": l, "points": v} for k, l, v in WORK_RULES],
        "level": [{"key": k, "points": v, "meaning": LEVEL_MEANING[k]} for k, v in LEVEL_PTS.items()],
        "years_cap": [{"up_to": u, "cap": c, "label": l} for u, c, l in YEARS_CAP],
        "tiers": [{"key": k, "min": m, "label": l} for k, m, l in TIERS],
        "top_product": {"points": PURPOSE_PTS[3], "companies": json.loads((DATA / "top_product.json").read_text())["companies"] if (DATA / "top_product.json").exists() else []},
        "regions": {k: v for k, v in REGIONS.items()},
        "in_area": IN_AREA,
    }


def load_top_product():
    p = DATA / "top_product.json"
    names = [c["name"] for c in json.loads(p.read_text())["companies"]] if p.exists() else []
    return [norm_company(n) for n in names]


TOP_PRODUCT = []  # filled in main()


def is_top_product(name):
    k = norm_company(name)
    return any(k == t or k.startswith(t + " ") for t in TOP_PRODUCT)


def norm_title(t):
    t = re.sub(r"\(.*?\)|[-–|,].*$", "", t.lower())
    t = re.sub(r"\bdesigner\b", "design", t)
    return re.sub(r"[^a-z]+", " ", t).strip()


NOISE = {"ltd", "limited", "plc", "group", "uk", "the", "inc", "care", "ai", "co", "company", "and", "london", "quadrant"}


ALIASES = {  # variant spellings across sources -> one display name
    "hm revenue customs": "HMRC", "hm revenue customs hmrc": "HMRC", "hmrc": "HMRC",
    "incubator for artificial intelligence": "Incubator for AI (i.AI)", "incubator for i": "Incubator for AI (i.AI)",
    "uk dept for science innovation tech": "Incubator for AI (i.AI)",
    "parliamentary digital service": "UK Parliament (Parliamentary Digital Service)",
    "wwt wildfowl wetlands trust": "WWT (Wildfowl & Wetlands Trust)", "wildfowl wetlands trust": "WWT (Wildfowl & Wetlands Trust)",
}


def canonical_name(name):
    raw = re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()
    return ALIASES.get(raw) or ALIASES.get(norm_company(name)) or name


def norm_company(name):
    toks = [t for t in re.sub(r"[^a-z0-9]+", " ", (name or "").lower().replace(".ai", " ai")).split() if t not in NOISE]
    return " ".join(toks)


def source_kind(src):
    s = (src or "").lower()
    return "api" if s.endswith("-api") else "linkedin" if "linkedin" in s else "aggregator"


def attach_company_linkedin(jobs, cmap):
    """Exact LinkedIn company pages for employers outside the register (data/company_linkedin.json)."""
    p = DATA / "company_linkedin.json"
    found = {norm_company(canonical_name(k)): v for k, v in (json.loads(p.read_text()).items() if p.exists() else [])}
    for j in jobs:
        if (cmap.get(j.get("company_id")) or {}).get("linkedin") or j.get("company_linkedin"):
            continue
        e = found.get(norm_company(canonical_name(j.get("company_name"))))
        if e and e.get("linkedin"):
            j["company_linkedin"] = e["linkedin"]
        elif e and "not named" in (e.get("note") or ""):
            j["client_unnamed"] = True


def attach_people(jobs, companies):
    """Merge data/people_linkedin.json into roles (and register companies)."""
    p = DATA / "people_linkedin.json"
    if not p.exists():
        return
    found = {norm_company(canonical_name(k)): v for k, v in json.loads(p.read_text()).items()}

    def lookup(name):
        k = norm_company(canonical_name(name))
        if k in found:
            return found[k]
        for fk, v in found.items():
            if fk and (fk.startswith(k + " ") or k.startswith(fk + " ")):
                return v
        return None

    for c in companies:
        e = lookup(c["name"])
        if e:
            known = {x.get("linkedin") for x in c.get("people", [])}
            c["people"] = c.get("people", []) + [x for x in e.get("people", []) if x.get("linkedin") not in known and not x.get("for_job")]
            c["linkedin"] = c.get("linkedin") or e.get("linkedin_company")
    for j in jobs:
        e = lookup(j.get("company_name"))
        if not e:
            continue
        j["company_linkedin"] = j.get("company_linkedin") or e.get("linkedin_company")
        have = {(x.get("linkedin") or x.get("name")) for x in j.get("people") or []}
        for person in e.get("people", []):
            if person.get("for_job") and norm_title(person["for_job"]) != norm_title(j["title"]):
                continue  # a hiring-team poster belongs to their own role only
            key = person.get("linkedin") or person.get("name")
            if key not in have:
                j.setdefault("people", []).append(person)
                have.add(key)


SOURCE_TYPES = {
    "climate-board": "Climate & sustainability boards", "charity-board": "Charity & non-profit boards",
    "impact-aggregator": "Impact & tech-for-good boards", "design-board": "Design job boards",
    "general-board": "General job boards", "vc-portfolio-board": "Investor portfolio boards",
    "public-sector": "Public sector", "community/newsletter": "Communities & newsletters",
    "company-careers": "Company careers sites",
}
SOURCE_HOW = {  # key -> (label, plain explanation shown on the Sources tab)
    "auto": ("Automatic", "Read from its public feed every time the board refreshes. Nothing for Robyn to do."),
    "sweep": ("Claude sweep", "No feed, but its public pages can be read. Claude searches it when you ask for a sweep. It isn't automatic."),
    "feed": ("Feed available", "Has a public feed (RSS or API) that could be made automatic. Until then it's only checked in Claude sweeps."),
    "alert": ("Email alert", "Blocks automated reading or needs a login, so nothing here reads it. Robyn saves a search and turns on email alerts. Many of these roles also appear on the employer's own careers site, LinkedIn or Hard Problems, which are read."),
    "join": ("Join / subscribe", "A Slack group, newsletter or community that shares jobs with members. Robyn joins and keeps an eye on it."),
    "retired": ("Not useful", "Closed, has no jobs board, or isn't relevant. Kept so nobody researches it again."),
}
CONNECTED = {"octopus ventures", "planet a", "norrsken", "2150", "energy impact partners", "all hands", "atomico", "kindred", "nhs jobs"}
READ_IN_SWEEPS = {"linkedin jobs", "charityjob", "escape the city"}  # login-gated for full use, but public pages were readable


def host(u):
    m = re.match(r"https?://([^/]+)", u or "")
    return m.group(1).lower().removeprefix("www.") if m else ""


def enrich_sources(sources, jobs):
    extra = [
        {"id": "company-careers", "name": "Company careers sites (the register)", "url": "", "category": "company-careers", "relevance": 5,
         "has_uk_coverage": True, "status": "active", "how": "auto",
         "notes": "Each register company's own job board (Greenhouse, Lever, Ashby, Workable, Teamtailor, Personio, Pinpoint and others). The most reliable source; about 75 of the 130 companies have a readable feed."},
        {"id": "hard-problems", "name": "Hard Problems", "url": "https://www.hardproblems.com/jobs", "category": "impact-aggregator", "relevance": 5,
         "has_uk_coverage": True, "status": "active", "how": "auto", "search_url": "https://www.hardproblems.com/jobs",
         "notes": "London non-profit board for designers working on climate, health, education and public services. Public RSS feed of ~550 roles."},
    ]
    out = [x for x in sources if x.get("id") not in {e["id"] for e in extra}] + extra
    job_strings = []
    for j in jobs:
        hosts = {host(u) for u in [j.get("apply_url"), j.get("source_url")] + [x.get("url") for x in j.get("sources", [])]}
        names = " ".join(str(x.get("name") or "") for x in j.get("sources", [])).lower()
        job_strings.append((hosts, names, j.get("source_kind")))
    for src in out:
        n = (src.get("name") or "").lower()
        key = next((c for c in CONNECTED if n.startswith(c)), None)
        if not src.get("how"):
            am = (src.get("access_method") or "").lower()
            if src.get("status") != "active":
                src["how"] = "retired"
            elif key:
                src["how"] = "auto"
            elif src.get("category") == "community/newsletter":
                src["how"] = "join"
            elif any(n.startswith(r) for r in READ_IN_SWEEPS) or "html" in am:
                src["how"] = "sweep"
            elif any(t in am for t in ("rss", "api", "getro")):
                src["how"] = "feed"
            else:
                src["how"] = "alert"
        src["type_label"] = SOURCE_TYPES.get(src.get("category"), "Other")
        src["how_label"] = SOURCE_HOW[src["how"]][0]
        h = host(src.get("url"))
        cnt = 0
        for hosts, names, kind in job_strings:
            if src["id"] == "company-careers":
                cnt += kind == "api"
            elif key and key != "nhs jobs":
                cnt += f"getro:{key}" in names
            elif h and any(x == h or (h != "gov.uk" and x.endswith("." + h)) for x in hosts if x):  # gov.uk is shared by every department
                cnt += 1
        src["roles_on_board"] = cnt
    return out


def write_site(out):
    """docs/ = the same board as a standalone web page, for GitHub Pages."""
    site = ROOT / "docs"
    site.mkdir(exist_ok=True)
    page = (ROOT / "dashboard" / "index.html").read_text()
    (site / "index.html").write_text(
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        "<style>body{margin:0;font:14px/1.5 system-ui,sans-serif}img{max-width:100%}</style></head><body>\n"
        + page + "\n</body></html>\n")
    (site / "data.json").write_text(json.dumps(out, ensure_ascii=False))
    (site / ".nojekyll").write_text("")


# --- "Passed on": everything a sweep skipped, grouped by company, for a human second look ---
AGENCY_RE = re.compile(r"recruit|talent|resourc|search and selection|\bhays\b|harvey nash|experis|sanderson|oliver bernard|burns sheehan|"
                       r"better placed|brio digital|corecom|cps group|ecs resource|es recruit|exalto|identify solutions|jobgether|jobright|"
                       r"morson|mthree|oxbow|pontoon|propel|pulse group|rmg digital|\bsalt\b|stealth it|stott and may|switch tech|synapri|"
                       r"synergize|tiptopjob|totally tech|\btrg\b|trust in soda|zachary daniels|aquent|haystack|career moves|futureheads|"
                       r"adlib|bentley|eleniak|undisclosed", re.I)
CONSULT_RE = re.compile(r"version 1|\bibm\b|kainos|capgemini|tata consultancy|netcompany|\bcgi\b|accenture|wipro|grid dynamics|synechron|"
                        r"capco|sahaj|nec software|designit|akqa|native design|parallax|evoke|principle", re.I)
PASS_GROUPS = {  # key -> (label, why it was passed, priority for review: lower = look first)
    "recruiter": ("Recruiter, client not named", "Posted by a recruitment agency. The search card doesn't show who the client is, so the mission is unknown.", 1),
    "consultancy": ("Consultancy or agency", "Builds services for clients. Many work on government and public services, so this is a judgement call.", 2),
    "commercial": ("Commercial company", "Judged an ordinary commercial employer (purpose 2 or lower) from the company name.", 3),
    "not-design": ("Not a product design role", "Physical product, games UI, graphic or IT service management roles.", 4),
    "outside-uk": ("Outside the UK", "The role is based abroad.", 5),
    "scheme": ("Student or graduate scheme", "Internships, placements and graduate schemes below Robyn's level.", 6),
}


def pass_group(reason, company):
    r = (reason or "").lower()
    if "not design" in r:
        return "not-design"
    if "non-uk" in r or "outside" in r:
        return "outside-uk"
    if "student" in r or "graduate" in r or "intern" in r:
        return "scheme"
    if AGENCY_RE.search(company or ""):
        return "recruiter"
    if CONSULT_RE.search(company or ""):
        return "consultancy"
    return "commercial"


def passed_on(jobs):
    on_board_ids, on_board_keys = set(), set()
    for j in jobs:
        for u in [j.get("apply_url"), j.get("source_url")] + [x.get("url") for x in j.get("sources", [])]:
            m = re.search(r"/jobs/view/(?:[^/]*-)?(\d{6,})", u or "")
            if m:
                on_board_ids.add(m.group(1))
        on_board_keys.add((norm_company(j.get("company_name")), norm_title(j.get("title", ""))))
    by_co = {}
    for f in sorted(DATA.glob("*skipped*.json")):
        for x in json.loads(f.read_text()):
            co = x.get("company") or "Unknown"
            if str(x.get("id")) in on_board_ids or (norm_company(co), norm_title(x.get("title", ""))) in on_board_keys:
                continue  # it made it onto the board after all
            g = pass_group(x.get("reason"), co)
            if is_top_product(co) and g in ("commercial", "consultancy"):
                continue  # top product companies go on the Roles tab, not here
            e = by_co.setdefault(norm_company(co) or co.lower(), {"company": co, "group": g, "roles": [], "reasons": set()})
            if PASS_GROUPS[g][2] < PASS_GROUPS[e["group"]][2]:
                e["group"] = g
            e["reasons"].add(x.get("reason") or "")
            e["roles"].append({"title": x.get("title"), "location": x.get("location"),
                               "url": f"https://www.linkedin.com/jobs/view/{x['id']}/" if str(x.get("id", "")).isdigit() else x.get("url")})
    out = []
    for key, e in by_co.items():
        detail = "; ".join(sorted(r for r in e["reasons"] if r and r != "purpose<=2"))
        out.append({"key": re.sub(r"[^a-z0-9]+", "-", key).strip("-")[:120], "company": e["company"], "group": e["group"],
                    "detail": detail, "roles": e["roles"]})
    out.sort(key=lambda e: (PASS_GROUPS[e["group"]][2], -len(e["roles"]), e["company"].lower()))
    return out


def main():
    TOP_PRODUCT.extend(load_top_product())
    companies = json.loads((DATA / "companies.json").read_text()) if (DATA / "companies.json").exists() else []
    cmap = {c["id"]: c for c in companies}
    name_map = {c["name"].lower(): c for c in companies}

    raw = []
    for f in JOB_FILES:
        p = DATA / f
        if p.exists():
            try:
                raw += json.loads(p.read_text())
            except json.JSONDecodeError as e:
                print(f"skip {f}: {e}")

    merged, company_keys = {}, set()
    for j in raw:
        if EXCLUDE_RE.search(j.get("title", "")) or (j.get("closes") and j["closes"] < date.today().isoformat()):
            continue
        j["unconfirmed"] = j.get("verified_open") is False  # listed somewhere, but the live posting couldn't be opened
        j["company_name"] = canonical_name(j.get("company_name"))
        c = cmap.get(j.get("company_id")) or name_map.get((j.get("company_name") or "").lower())
        if c:
            j["company_id"] = c["id"]
        t = text_of(j)
        j["work_model"] = infer_work_model(j, t)
        j["office_days"] = j.get("office_days") if isinstance(j.get("office_days"), int) else infer_office_days(t)
        if j["work_model"] == "unknown" and j["office_days"]:
            j["work_model"] = "hybrid" if j["office_days"] < 5 else "office"
        j["seniority"] = infer_seniority(j, t)
        j["years_experience"] = infer_years(j, t)
        j["region"] = region_for(j.get("location"))
        if j["region"] in ("Unknown", "UK (unspecified)") and j["work_model"] == "remote":
            j["region"] = "Remote UK"
        if j["region"] == "Non-UK" and not (j["work_model"] == "remote" and re.search(r"europe|emea|global|anywhere|worldwide", (j.get("location") or ""), re.I)):
            continue  # abroad, unless remote and open to UK/Europe
        if c:  # the curated register is the authority on purpose + sector
            j["sectors"] = sorted(set(c.get("sectors", [])) | set(j.get("sectors") or []))
            j["purpose_score"] = c.get("purpose_score") or j.get("purpose_score")
        j["top_product"] = is_top_product(j.get("company_name"))
        j["company_kind"] = "top" if j["top_product"] else "purpose" if (j.get("purpose_score") or (c or {}).get("purpose_score") or 0) >= 3 else "other"
        j["match"], j["score_parts"] = score(j, c)
        j["tier"] = next(k for k, m, _ in TIERS if j["match"] >= m)
        j["work_rule"] = work_key(j["work_model"], j["office_days"], j["region"])
        j["source_kind"] = source_kind(j.get("source"))
        if not j.get("role_summary") and j.get("description"):
            j["role_summary"] = j["description"][:420].rsplit(" ", 1)[0] + "…"

        ck = norm_company(c["name"] if c else j.get("company_name"))
        for existing in company_keys:  # "Nourish" vs "Nourish Care", "L&Q" vs "L&Q (London & Quadrant)"
            if existing == ck or existing.startswith(ck + " ") or ck.startswith(existing + " "):
                ck = existing
                break
        company_keys.add(ck)
        key = (ck, norm_title(j.get("title", "")))
        prev = merged.get(key)
        if not prev:
            j["sources"] = [{"name": j.get("source"), "url": j.get("source_url") or j.get("apply_url")}]
            merged[key] = j
        else:
            prev["sources"].append({"name": j.get("source"), "url": j.get("source_url") or j.get("apply_url")})
            # keep the most authoritative record but fill gaps from the other
            winner, loser = (j, prev) if SOURCE_PRIORITY[j["source_kind"]] < SOURCE_PRIORITY[prev["source_kind"]] else (prev, j)
            for k, v in loser.items():
                if not winner.get(k) and v:
                    winner[k] = v
            winner["sources"] = prev["sources"]
            winner["people"] = (winner.get("people") or []) + [p for p in (loser.get("people") or []) if p not in (winner.get("people") or [])]
            merged[key] = winner

    attach_company_linkedin(merged.values(), cmap)  # verified pages win over ones picked up during the people search
    attach_people(merged.values(), companies)
    missing = sorted({j["company_name"] for j in merged.values()
                      if not ((cmap.get(j.get("company_id")) or {}).get("linkedin") or j.get("company_linkedin") or j.get("client_unnamed"))})
    if missing:
        print(f"no LinkedIn page yet for {len(missing)} employers: {', '.join(missing)}")
    jobs = sorted(merged.values(), key=lambda x: -x["match"])
    seen_path = DATA / "first_seen.json"
    seen = json.loads(seen_path.read_text()) if seen_path.exists() else {}
    today = date.today().isoformat()
    for j in jobs:
        j.pop("description", None)  # keep the page light; summary + link is enough
        j["first_seen"] = seen.setdefault(j["id"], today)
    seen_path.write_text(json.dumps(seen, indent=0))

    used = {j.get("company_id") for j in jobs}
    sources = json.loads((DATA / "sources.json").read_text()) if (DATA / "sources.json").exists() else []
    out = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "baseline": min(seen.values()) if seen else today,
        "jobs": jobs,
        "companies": companies,
        "sources": enrich_sources(sources, jobs),
        "source_how": {k: {"label": v[0], "explain": v[1]} for k, v in SOURCE_HOW.items()},
        "score_rules": score_rules(),
        "passed": passed_on(jobs),
        "pass_groups": {k: {"label": v[0], "explain": v[1], "order": v[2]} for k, v in PASS_GROUPS.items()},
        "stats": {"jobs": len(jobs), "companies": len(companies), "companies_hiring": len(used & set(cmap)),
                  "strong": sum(j["tier"] == "strong" for j in jobs)},
    }
    (DATA / "dashboard.json").write_text(json.dumps(out, ensure_ascii=False))
    write_site(out)
    print(json.dumps(out["stats"]))


if __name__ == "__main__":
    main()
