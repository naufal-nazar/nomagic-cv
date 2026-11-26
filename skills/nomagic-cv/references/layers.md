# The six layers

Each layer clears one gate. Fix them in order: a CV that fails to parse is never searched, and one never searched is never scanned.

**Rule strength.** Each rule carries the grade of its strongest source. A/B-backed rules are defaults. Rules backed only by grade C or practice (the fast scan, verb-first bullets, contact details outside the header) are starting points to test with `/nomagic-stats`, not hard rules. Rule ids refer to `rules/rules.yaml`. Paths like `rules/` and `scripts/` are relative to the skill folder (siblings of `references/`).

## 1. Parse: the machine reads every word
- Single column, built in a word processor or RenderCV. No tables, text boxes, sidebars, icons, images or skill bars. (R-PARSE-01)
- Standard headings: Summary, Experience, Education, Certifications, Skills. (R-PARSE-02)
- Contact details in the body, not the page header or footer. (R-PARSE-03)
- .docx or text-based PDF, whichever the portal asks for. Test: the extracted text should keep the CV's content and order. `scripts/parse_check.py` checks this heuristically (the opening words of each line; reordering is only a warning), so also open the file and read it. (R-PARSE-04)

## 2. Match: the CV appears in the recruiter's search
- Headline uses the posting's exact title, where it truthfully describes the candidate. (R-MATCH-01)
- Every true must-have appears in the posting's own words. (R-MATCH-02)
- Terms in full and as an acronym once. (R-MATCH-03)
- Degrees and certifications in full. (R-MATCH-04)
- One master per role family; tailor headline, skills order and 2-3 bullets per posting. (R-MATCH-05)

## 3. Scan: the top third wins the first look
The "7-second scan" comes from one vendor eye-tracking study (Ladders, grade C). Treat it as direction: design the top third for a fast scan.
- Name, target title, location, work authorization where relevant. (R-SCAN-01)
- 2-3 line summary: years, domain, strongest employers, one number. (R-SCAN-02)
- Optional highlights block (3-4 bullets) when the best results sit in older roles.
- Title and employer bold, dates on the same line, white space. (R-SCAN-03)
- One page early-career, two once experience fills it. (R-SCAN-04)

## 4. Prove: every bullet shows scope or a result
- Verb + what + scale + outcome. (R-PROVE-03)
- 3-5 bullets for recent roles, 1-3 for older ones. (R-PROVE-04)
- Plain words; no "passionate", "results-driven". (R-PROVE-02)
- Zero spelling or grammar errors. (R-PROVE-01)

## 5. Signal: evidence beyond the CV
- Apply in the first days after posting. (R-SIGNAL-01)
- Complete LinkedIn, linked and consistent. (R-SIGNAL-02)
- Tailored cover letter for priority roles. (R-SIGNAL-03)
- Referral or hiring-manager note where possible. (R-SIGNAL-04)

## 6. Knockouts: screening answers match the CV
- Read every screening question first: some are knockout questions that can reject an application automatically. (R-KNOCK-01; grade C, vendor analysis)
- Answer from the same fact sheet: years, titles, credentials, location, authorization, travel, licences.
- Never stretch an answer to pass. (R-KNOCK-02)
