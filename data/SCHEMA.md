# Data schema (v1)

## data/companies.json  — the Company Register
Array of:
{
  "id": "octopus-energy",                 // kebab-case slug, unique
  "name": "Octopus Energy",
  "website": "https://octopus.energy",
  "careers_url": "https://...",           // human careers page
  "ats": { "provider": "greenhouse|lever|ashby|workable|teamtailor|personio|smartrecruiters|recruitee|pinpoint|workday|other|none",
           "slug": "board-token-or-subdomain", "api_url": "public JSON endpoint if known" },
  "linkedin": "https://www.linkedin.com/company/...",
  "sectors": ["energy-transition","climate","nature-rewilding","circular-economy","sustainable-food","charity","health","education","civic-tech","ethical-finance","social-impact","purpose-ecommerce","other"],
  "org_type": "charity|social-enterprise|b-corp|startup|scaleup|public-sector|corporate",
  "hq": "London",
  "uk_presence": "London office; remote-first UK",
  "size": "51-200",
  "mission": "One sentence on what they do and the change they make.",
  "purpose_score": 1-5,                   // 5 = core mission is positive change (charity, climate tech); 3 = purpose-led but commercial; 1 = no clear purpose
  "purpose_rationale": "short",
  "design_team_notes": "size/maturity of design team if known",
  "people": [ { "name": "", "title": "", "linkedin": "", "role": "head-of-design|design-lead|hiring-manager|product-designer|recruiter|head-of-product", "source": "url where found", "verified": true|false } ]
}

## data/jobs.json — Live roles
Array of:
{
  "id": "source-company-slug-title-hash",
  "title": "Product Designer",
  "company_id": "octopus-energy",         // matches register id if present
  "company_name": "Octopus Energy",
  "apply_url": "https://...",             // direct posting
  "source": "greenhouse-api|climatebase|charityjob|...",
  "source_url": "where we found it",
  "location": "London, UK",
  "work_model": "remote|hybrid|office|unknown",
  "office_days": 0-5 or null,
  "salary": "£45k–£55k" or null,
  "seniority": "junior|mid|senior|lead|unknown",
  "years_experience": "e.g. 2-4" or null,
  "posted": "YYYY-MM-DD" or null,
  "closes": "YYYY-MM-DD" or null,
  "role_summary": "2-3 sentences",
  "sectors": [...],
  "purpose_score": 1-5,
  "people": [ same shape as company.people, role-specific e.g. hiring manager ]
}
