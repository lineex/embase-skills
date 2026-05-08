# Embase DOM, Login, And Search Reference

This reference supports the Embase skills. Prefer current page inspection over hard-coded selectors because Embase UI labels can vary by institution and release.

## Base URL And Login Model

- Base URL: `https://www.embase.com`
- Authentication: user completes institutional login in Chrome.
- The agent reuses the active Chrome session through Chrome DevTools MCP.
- Never copy cookies, tokens, MFA codes, CAPTCHA answers, or passwords into chat.
- After visiting a publisher or DOI page, return to `https://www.embase.com` before running Embase search/export skills.

## Anti-Detection Navigation

Every Embase `navigate_page` call should include:

```json
{
  "initScript": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
}
```

Use `evaluate_script` with polling loops. Avoid `wait_for` and screenshot-based extraction.

## Search Modes

Embase offers several search routes:

- Quick search: broad mapping with Emtree and free-text behavior.
- Advanced search: fielded strategy builder, mapping controls, date/source/type/language/age/gender limits.
- Advanced command strategy: preferred for reproducible multi-concept review searches; use `embase-advanced-search`.
- Command-line style search: best for reproducible systematic-review strategies.
- Drug, Disease, Device, PICO, PV Wizard, and Citation Information forms: use only when the user's task explicitly needs that specialized form.

## Common Field Codes

| Code | Meaning | Example |
|---|---|---|
| `:ti` | Title | `sepsis:ti` |
| `:ab` | Abstract | `sepsis:ab` |
| `:au` or `/au` | Author | `smith:au` |
| `:de` or `/de` | Index term / descriptor | `'aspirin':de` |
| `/exp` | Exploded Emtree term | `'aspirin'/exp` |
| `:do` | DOI | `'10.1000/example':do` |
| `:py` or `/py` | Publication year | `2024:py`, `[2020-2025]/py` |
| `:la` | Language | `english:la` |
| `:it` or `/it` | Publication type | `article:it` |
| `:ff` or `/ff` | Affiliation | `university:ff` |
| `:is` | ISSN | `18771173:is` |
| `:cn` | Clinical trial number | `'2006-005504-1':cn` |
| `:id` | Luwak unique ID | `L2002324214:id` |

## Common Limits

| Limit | Syntax |
|---|---|
| Humans | `[humans]/lim` |
| Animals | `[animals]/lim` |
| English | `[english]/lim` |
| With abstract | `[abstracts]/lim` |
| Article | `[article]/lim` |
| Conference abstract | `[conference abstract]/lim` |
| Clinical trial | `[clinical trial]/lim` |
| Randomized controlled trial | `[randomized controlled trial]/lim` |
| Meta-analysis | `[meta analysis]/lim` |
| Systematic review | `[systematic review]/lim` |
| MEDLINE source | `[medline]/lim` |
| Embase source | `[embase]/lim` |
| Embase Classic source | `[embase classic]/lim` |

## Search Strategy Patterns

### Broad Embase Mapping

Use when the user wants exploratory recall:

```text
"heart failure"
```

Embase broad search maps to Emtree and free text.

### Reproducible Review Block

Use for systematic, scoping, or meta-analysis work:

```text
("heart failure":ti OR "heart failure":ab OR "heart failure"/exp)
AND
("sodium glucose cotransporter 2 inhibitor":ti OR "sglt2 inhibitor":ti OR "sglt2 inhibitor":ab OR "sodium glucose cotransporter 2 inhibitor"/exp)
AND [humans]/lim
AND [english]/lim
AND [article]/lim
```

### Date Range

```text
AND [2020-2025]/py
```

## Result Extraction Hints

Prefer these semantic patterns over exact classes:

- Record containers: `article`, list items, or elements whose class/data-testid contains `result` or `record`.
- Title: first long heading or result link.
- DOI: regex `10.\d{4,9}/...`.
- PMID: visible `PMID`.
- Embase IDs: visible labels such as `PUI`, `LUI`, `Accession number`, `Embase ID`, or Luwak IDs starting with `L`.
- Source/year: text containing journal/conference metadata and a four-digit year.
- Authors: visible author class/link text or semicolon/comma-separated author line.

## Full Record Extraction Hints

Look for labels:

- Title
- Authors
- Source
- Journal
- Abstract
- Index terms
- Emtree terms
- DOI
- PMID
- Publication type
- Language
- Full text

If the record opens in a modal, extract from the modal rather than requiring page navigation.

## Export Reference

Embase export formats include:

- RIS
- RefWorks Direct Export
- CSV fields by row
- CSV fields by column
- Plain text
- XML
- MS Word
- MS Excel fields by row
- MS Excel fields by column
- PDF

Output options include:

- Titles Only
- Citations Only
- Citations and Abstracts
- Citations
- Abstract and Index terms
- Full Record
- Specify the fields to be exported

For Zotero and review screening, prefer `RIS` plus `Full Record` or `Citations and Abstracts`, and include the search query in export when available.
