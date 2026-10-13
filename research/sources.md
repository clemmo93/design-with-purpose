# Job sources for Robyn: Product Designer, purpose-driven, UK

Researched and URL-checked on 2026-10-13. Full data: `data/sources.json` (84 entries: 69 active, plus 15 that were checked and found to be dead, not a job board, or without a portfolio board, kept so nobody re-researches them).

Each entry has `relevance` (1–5), `has_uk_coverage`, `access_method`, `search_url`, `api_endpoint`, `status`, `http_check` and `notes`.

## Key findings

- **Purpose-specific boards are low volume.** Most have fewer than 10 product-design roles at any time. Even the best climate boards surfaced only a handful of UK product-design roles. The best results will come from three things combined:
  - a few high-signal boards;
  - LinkedIn and Welcome to the Jungle alerts;
  - polling the ATS feeds of target companies directly (Greenhouse, Lever, Ashby, Workable, Personio, JobTrain). Climate and VC lists such as ClimateTechList, BGV and the B Corp directory work best as company discovery for that register.
- **Climatebase, the biggest climate board, can't be automated.** It's behind a Cloudflare challenge (403 on every path). Use its email alerts and don't try to bypass the challenge.
- **Getro boards have a clean public API.** Use `POST https://api.getro.com/api/v2/collections/{network_id}/search/jobs` with the header `Accept: application/json` and a body of `{"query":"product designer","hitsPerPage":50,"page":0,"filters":{}}`. Alternatively, server-side `?q=` pages embed results in `__NEXT_DATA__`. Verified network ids:
  - Octopus Ventures: 4580
  - Planet A: 1426
  - Norrsken: 4217
  - 2150: 1287
  - Energy Impact Partners: 253
  - All Hands: 634
  - Atomico: 36986
  - Kindred: 221
- **Consider boards (e.g. Balderton) need a CSRF session.** They're fragile and low priority.
- **Most of the named climate VCs have no portfolio jobs board.** This covers Extantia, World Fund, Giant, Zero Carbon Capital, Kiko, EIF, Pale Blue Dot, Systemiq and Bethnal Green Ventures. Climate Draft's board is offline (404) since Lowercarbon bought it. Use these VCs' portfolios as company lists instead.
- **Several boards on the brief don't exist or aren't job boards:**
  - "Work for Good" is a fundraising platform.
  - B Corp UK has no jobs board, and B Work is gone.
  - uxjobsboard.com is defunct.
  - Jobs for Good UK is a holding page.
  - techforgood.global is now spam.
  - Do Something Good, Ethical Jobs UK and Good Jobs could not be found.
- **Civil Service office attendance may rule roles out.** Many departments now require about 60% office attendance (3 days). That conflicts with Robyn's limit of 2 days, so check each advert.

## Top 10 sources (best signal for Robyn)

| # | Source | Why | How |
|---|---|---|---|
| 1 | **CharityJob** | Largest UK charity board; 8 'product designer' matches today | Email alerts (no RSS; scraping is likely against the ToS) |
| 2 | **Escape the City** | UK, B Corp, purpose-led start-ups and social enterprises | Email alerts plus the weekly Top 10 (Bubble app, no feed) |
| 3 | **Climatebase** | Biggest climate board; UK and Remote filters; also hosts the Climate Designers board | Email alerts (Cloudflare blocks automation) |
| 4 | **LinkedIn** | Volume; Remote/Hybrid filters | Daily alert on the [filtered search](https://www.linkedin.com/jobs/search/?keywords=product%20designer&geoId=101165590&f_WT=2%2C3&f_E=3%2C4&sortBy=DD) (don't scrape) |
| 5 | **Welcome to the Jungle (Otta)** | Best UK start-up board; mission and remote-policy tags | Profile matches and alerts |
| 6 | **Octopus Ventures talent board** (plus other Getro climate/impact VCs) | 826 jobs; 10 UK/remote product-design hits today | **Automate** via the Getro API |
| 7 | **Civil Service Jobs** (GDS/DDaT) | Junior-to-mid Product and Interaction Designer roles with public-good impact | Email alerts (has a bot check); watch the 60% office rule |
| 8 | **Design Gigs for Good** (Slack and Google Group) | Ranked #1 for impact UX/product roles in the 2024 sustainableux review | Join the Slack and turn on #jobs notifications |
| 9 | **Climate Designers** | Weekly jobs newsletter, London chapter, networking | Subscribe and join |
| 10 | **inClimate** | About 25k European climate jobs including UK remote and hybrid; weekly newsletter | Newsletter plus manual check (view-limited) |

Honourable mentions:
- **Guardian Jobs** and **Charity Digital jobs**, for charity digital roles.
- **NHS Jobs**, which has a free XML API.
- **dxw** and other public-good agencies (Torchbox, TPXimpact, Made Tech, Snook).
- **designjobs.co.uk**, whose RSS honours `?q=`.
- **ClimateTechList**, best used for company discovery.

## Automate vs. set alerts

**Automate (stable, ToS-friendly feeds or APIs):**
- Getro VC boards via `api.getro.com` (8 networks above). Filter `searchable_locations` for UK, London or Remote.
- NHS Jobs: `https://www.jobs.nhs.uk/api/v1/search_xml?keyword=product%20designer`
- designjobs.co.uk RSS: `https://designjobs.co.uk/jobs.rss?q=product+designer`
- Dribbble Jobs RSS: `https://dribbble.com/jobs.rss` (filter UK/Remote locally)
- dxw RSS: `https://www.dxw.com/jobs/feed/`
- Environmentjob RSS: `https://environmentjob.co.uk/jobs.rss` (filter locally)
- Adzuna API and Reed API (free keys) for broad UK coverage
- Guardian Jobs `searchjobs` HTML (server-rendered Madgex; its RSS ignores keywords)
- Sustainable Ventures board (embedded JSON)
- uiuxjobsboard UK/remote pages
- JobTrain charity pages (e.g. Citizens Advice)
- Workable, Personio and other ATS feeds for target companies (e.g. Public Digital: `apply.workable.com/api/v1/widget/accounts/public-digital-1`)

**Set email alerts or check manually (bot-protected, JS-only, or scraping against the ToS):**
- Boards: CharityJob, Escape the City, Climatebase, LinkedIn, Indeed, Welcome to the Jungle, Civil Service Jobs, Third Sector Jobs, Charity Digital, Work In Startups, 80,000 Hours, Terra.do, ClimateTechList and inClimate.
- Communities (join): Design Gigs for Good, Climate Designers, Work on Climate, ClimateAction.tech and Women and Climate.

**Skip or low priority:** Idealist (US-centric), Impactpool (UN/NGO), Green Jobs Board (US), Women Who Design jobs (US, 7 listings), Remote OK and We Work Remotely (global remote), Hiring Without Whiteboards (engineering company list), Goodmoves (Scotland), and Creative Boom (brand/graphic roles).
