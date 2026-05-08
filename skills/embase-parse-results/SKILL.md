---
name: embase-parse-results
description: Parse the active Embase result page into structured records. Intended for internal use after embase-search or embase-navigate-pages.
argument-hint: "[optional count]"
user-invocable: false
disable-model-invocation: false
---

# Embase Parse Results

Extract structured records from the current Embase result page. Use this after search submission, pagination, or returning from a detail page.

## Rules

- The active page must be on `embase.com`.
- Use `evaluate_script`, not screenshots.
- Do not use `wait_for`.
- Return a typed status and structured JSON.
- Prefer structured network/page state if available; otherwise parse visible result cards.

## Step 1: Poll And Extract

Run one `evaluate_script` call:

```javascript
async () => {
  const maxRecords = Number(`COUNT_OR_25`) || 25;
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };
  const textOf = (el) => clean(el?.innerText || el?.textContent || '');
  const attr = (el, name) => el?.getAttribute(name) || '';

  const parseTotal = () => {
    const text = textOf(document.body);
    const patterns = [
      /([\d,]+)\s+results?/i,
      /results?\s*[:(]?\s*([\d,]+)/i,
      /found\s+([\d,]+)/i,
      /([\d,]+)\s+records?/i
    ];
    for (const re of patterns) {
      const m = text.match(re);
      if (m) return Number(m[1].replace(/,/g, ''));
    }
    return null;
  };

  const parseRecordFromText = (container, idx) => {
    const text = textOf(container);
    const links = [...container.querySelectorAll('a')].filter(visible);
    const titleLink =
      links.find(a => /record|article|details|result|view/i.test(`${a.href} ${attr(a, 'aria-label')}`) && textOf(a).length > 20) ||
      links.find(a => textOf(a).length > 20);
    const title = clean(textOf(titleLink) || [...container.querySelectorAll('h1,h2,h3,h4,[role="heading"]')]
      .map(textOf)
      .find(t => t.length > 20) || '');

    const doi = (text.match(/\b10\.\d{4,9}\/[-._;()/:A-Z0-9]+/i) || [''])[0];
    const pmid = (text.match(/\bPMID[:\s]+(\d{5,})/i) || [,''])[1];
    const pui =
      (text.match(/\b(?:PUI|LUI|Accession(?: number)?|Embase ID)[:\s#-]+([A-Z]?\d{6,}|L\d{6,})/i) || [,''])[1] ||
      (titleLink?.href.match(/[?&]id=([^&]+)/i) || [,''])[1];
    const year = (text.match(/\b(19|20)\d{2}\b/) || [''])[0];

    const journalTitle = textOf(container.querySelector('.journal-title,[class*="journal-title" i]'));
    const journalYear = textOf(container.querySelector('.journal-publication-year,[class*="publication-year" i]'));
    const journalVolume = textOf(container.querySelector('.journal-volume,[class*="journal-volume" i]'));
    const journalIssue = textOf(container.querySelector('.journal-issue,[class*="journal-issue" i]'));
    const journalPages = textOf(container.querySelector('.journal-pages,[class*="journal-pages" i]'));
    const structuredSource = [journalTitle, journalYear, journalVolume + journalIssue, journalPages]
      .map(clean)
      .filter(Boolean)
      .join(' ');

    const sourceCandidates = [...container.querySelectorAll('a,span,div,p')]
      .map(textOf)
      .filter(t => t && t.length < 220)
      .filter(t => /\b(19|20)\d{2}\b|vol\.?|volume|issue|pages?|pp\.|journal|conference/i.test(t));
    const source =
      structuredSource ||
      sourceCandidates.find(t => /[A-Za-z]{3,}/.test(t) && /\b(19|20)\d{2}\b/.test(t)) ||
      sourceCandidates.find(t => /[A-Za-z]{3,}/.test(t) && !/^\d{4}$/.test(t)) ||
      sourceCandidates[0] ||
      '';

    const structuredAuthors = [...container.querySelectorAll('[class*="author" i]')]
      .map(textOf)
      .filter(t => t && !/family-name|given-name/i.test(t))
      .filter((t, i, arr) => arr.indexOf(t) === i)
      .join(', ');
    const authors = structuredAuthors || [...container.querySelectorAll('[class*="author" i], a[href*="author" i], span')]
      .map(textOf)
      .filter(t => t && t.length > 2 && t.length < 260)
      .find(t => /[,;]/.test(t) || /\b[A-Z][a-z]+ [A-Z]/.test(t)) || '';

    return {
      index: idx + 1,
      title,
      authors,
      source,
      year,
      doi,
      pmid,
      id: pui,
      href: titleLink?.href || '',
      textSample: text.slice(0, 500)
    };
  };

  for (let attempt = 0; attempt < 30; attempt++) {
    if (!location.hostname.includes('embase.com')) {
      return { status: 'wrong_site', url: location.href };
    }

    const bodyText = textOf(document.body);
    if (/sign in|log in|OpenAthens|Shibboleth|access through your institution/i.test(bodyText) &&
        !/results?|records?|Emtree|Advanced search/i.test(bodyText)) {
      return { status: 'login_required', url: location.href };
    }

    const selectors = [
      '[data-testid*="result" i]',
      '[class*="result" i]',
      '[class*="record" i]',
      'article',
      'li'
    ];
    const containers = selectors
      .flatMap(sel => [...document.querySelectorAll(sel)])
      .filter(visible)
      .filter(el => {
        const t = textOf(el);
        return t.length > 80 &&
          /\b(19|20)\d{2}\b|doi|abstract|authors?|source|journal|conference|record|article/i.test(t);
      });

    const unique = [];
    const seen = new Set();
    for (const el of containers) {
      const t = textOf(el).slice(0, 200);
      if (!seen.has(t)) {
        seen.add(t);
        unique.push(el);
      }
      if (unique.length >= maxRecords) break;
    }

    const records = [];
    const recordSeen = new Set();
    for (const parsed of unique.map(parseRecordFromText)) {
      if (!(parsed.title || parsed.doi || parsed.id)) continue;
      const key = parsed.id || parsed.href || parsed.doi || parsed.title;
      if (recordSeen.has(key)) continue;
      recordSeen.add(key);
      parsed.index = records.length + 1;
      records.push(parsed);
    }

    if (records.length) {
      return {
        status: 'ok',
        url: location.href,
        totalResults: parseTotal(),
        count: records.length,
        records
      };
    }

    if (/no results|0 results|no records/i.test(bodyText)) {
      return {
        status: 'no_results',
        url: location.href,
        totalResults: 0,
        records: []
      };
    }

    await sleep(700);
  }

  return {
    status: 'timeout',
    url: location.href,
    totalResults: parseTotal(),
    textSample: textOf(document.body).slice(0, 1500),
    records: []
  };
}
```

## Step 2: Present Records

Show a compact table:

```text
| # | Title | Authors | Source | Year | DOI | ID |
|---|---|---|---|---|---|---|
```

Keep long titles and author lists short in the table. Mention that more fields are available via `embase-paper-detail`.

## Fallbacks

- If records are not extracted but the page looks like a result page, rerun with a smaller count and include `textSample` in your reasoning.
- If the page is still loading, rerun once after a short pause using the same polling script.
- If Embase UI changed, inspect semantic labels and visible text with `evaluate_script`; do not switch to screenshot extraction.
