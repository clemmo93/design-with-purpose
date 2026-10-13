# Design with Purpose

Product design roles at organisations making real change (energy transition, climate, nature, charities and tech for good), ranked for Robyn by purpose, office days and level.

**Open the board: https://clemmo93.github.io/design-with-purpose/**

## What's on the board

- **Roles**: every open product, UX, UI, service and interaction design role we found, each with a match score, apply link, the company's LinkedIn page and the people worth knowing there (Head of Design, design leads, Head of Product, designers, recruiters). Filter by match, remote/hybrid, office days, sector, purpose, level, region and source.
- **Companies**: a register of 130 purpose-led organisations, grouped by sector, with their careers pages and LinkedIn pages.
- **Sources**: every job board, feed and community we use, and how roles from each one reach the board.
- **How scoring works**: the scoring rules, with worked examples.

Your statuses and notes (Shortlisted, Applied, Not for me…) save in your own browser on this site.

## How the score works

Match = Purpose (up to 40) + Work pattern (up to 30) + Level (up to 30).

- **Purpose:** is positive change the organisation's mission?
- **Work pattern:** fully remote, or 2 or fewer office days within about 2 hours of London, scores highest.
- **Level:** junior and mid-level roles score highest.

Strong is 80 or more, Good is 62–79, and anything lower is Stretch. Nothing is hidden because of its score. The board's "How scoring works" tab has the full tables.

## How it's built

```
data/companies.json        Company register (130 orgs, each with its careers system and LinkedIn page)
scripts/fetch_ats.py   ─►  data/jobs_ats.json        roles from each company's own careers feed
scripts/fetch_boards.py ─► data/jobs_boards.json     Hard Problems, VC portfolio boards, NHS Jobs
research sweeps        ─►  data/jobs_aggregators.json, jobs_linkedin.json, jobs_junior.json
data/people_linkedin.json  current staff found on each company's LinkedIn People tab
data/company_linkedin.json exact LinkedIn company pages for employers outside the register
scripts/build.py       ─►  data/dashboard.json + docs/ (this website)
```

`dashboard/index.html` is the page source. `scripts/build.py` merges the sources, removes duplicates, scores each role and writes the site into `docs/`, which GitHub Pages serves.

### Refresh

```bash
python3 scripts/fetch_ats.py && python3 scripts/fetch_boards.py && python3 scripts/build.py
```

The research sweeps (job boards, LinkedIn, people) are run on request with Claude.

## Notes

- Everything here links to publicly available information: job adverts, company sites and public LinkedIn pages.
- Roles marked **Unconfirmed** were seen on a job board, but the live posting couldn't be opened because of a bot check or login wall. Check the advert before applying.
- People marked **unverified** have a LinkedIn headline that doesn't clearly name the company.
