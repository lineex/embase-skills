---
name: embase-paper-detail
description: Open an Embase result or identifier and extract full-record metadata, abstract, source fields, DOI, PMID, PUI/LUI, Emtree terms, and full-text links.
argument-hint: "[result # | DOI | PMID | PUI/LUI | title]"
user-invocable: true
disable-model-invocation: false
---

# Embase Paper Detail

Open a selected Embase record and extract full metadata from the active logged-in Embase session.

## Mandatory Session Check

Run `embase-session` first unless the active page is already an Embase result or full-record page.

## Rules

- Use Embase pages through the logged-in Chrome session.
- Use `evaluate_script` for interaction and extraction.
- Do not use screenshots for data.
- Do not use `wait_for`.
- Do not request cookies, tokens, or credentials.

## Step 1: Open The Record

If the user gives a result number, click the matching visible record. If the user gives a DOI, PMID, PUI/LUI, or title and no result page is active, run `embase-search` first with a specific query:

```text
'10.xxxx/yyyy':do
12345678:pm
L123456789:id
"exact title":ti
```

Then use one `evaluate_script` call:

```javascript
async () => {
  const target = `TARGET`;
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const textOf = (el) => clean(el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('title') || '');
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };

  if (!location.hostname.includes('embase.com')) {
    return { status: 'wrong_site', url: location.href };
  }

  const before = location.href;
  const numeric = /^\d+$/.test(target) ? Number(target) : null;
  const candidates = [...document.querySelectorAll('article,[class*="result" i],[class*="record" i],li')]
    .filter(visible)
    .filter(el => textOf(el).length > 80);

  let container = null;
  if (numeric) {
    container = candidates[numeric - 1] || null;
  } else {
    const lowerTarget = target.toLowerCase();
    container = candidates.find(el => textOf(el).toLowerCase().includes(lowerTarget)) || null;
  }

  const link =
    container?.querySelector('a[href]') ||
    [...document.querySelectorAll('a[href]')]
      .filter(visible)
      .find(a => {
        const t = `${textOf(a)} ${a.href}`.toLowerCase();
        return numeric ? /record|detail|article|view|result/.test(t) : t.includes(target.toLowerCase());
      });

  if (!link) {
    return {
      status: 'record_link_not_found',
      target,
      url: location.href,
      candidates: candidates.slice(0, 10).map((el, i) => ({ index: i + 1, text: textOf(el).slice(0, 300) }))
    };
  }

  link.click();

  for (let attempt = 0; attempt < 30; attempt++) {
    await sleep(600);
    const body = textOf(document.body);
    if ((location.href !== before || /abstract|index terms|Emtree|authors?|DOI|source|full text/i.test(body)) &&
        !/loading/i.test(body.slice(0, 300))) {
      return {
        status: 'opened',
        target,
        url: location.href,
        message: 'Record opened. Run the extraction script next.'
      };
    }
  }

  return { status: 'timeout', target, url: location.href };
}
```

## Step 2: Extract Full Record

Run:

```javascript
async () => {
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const textOf = (el) => clean(el?.innerText || el?.textContent || '');
  const visible = (el) => {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };
  const labelValue = (labels) => {
    const all = [...document.querySelectorAll('dt,th,strong,b,h2,h3,h4,label,div,span')]
      .filter(visible);
    for (const label of labels) {
      const node = all.find(el => new RegExp(`^${label}\\b`, 'i').test(textOf(el)));
      if (!node) continue;
      const direct =
        node.nextElementSibling ||
        node.parentElement?.querySelector('dd,td,p,div,span:not(:first-child)');
      const value = clean(textOf(direct).replace(new RegExp(`^${label}\\b[:\\s-]*`, 'i'), ''));
      if (value && value.toLowerCase() !== label.toLowerCase()) return value;
      const parentText = textOf(node.parentElement);
      const m = parentText.match(new RegExp(`${label}\\s*[:\\-]?\\s*(.+)`, 'i'));
      if (m) return clean(m[1]);
    }
    return '';
  };
  const pageTexts = () => {
    const root = document.querySelector('main') || document.body;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        const text = clean(node.textContent);
        if (!parent || !text || !visible(parent)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    const texts = [];
    let node;
    while ((node = walker.nextNode())) texts.push(clean(node.textContent));
    return texts;
  };
  const valueAfter = (label) => {
    const texts = pageTexts();
    const idx = texts.findIndex(t => new RegExp(`^${label}$`, 'i').test(t));
    return idx >= 0 ? texts[idx + 1] || '' : '';
  };
  const valuesBetween = (startLabel, stopLabels) => {
    const texts = pageTexts();
    const start = texts.findIndex(t => new RegExp(`^${startLabel}$`, 'i').test(t));
    if (start < 0) return [];
    let end = texts.length;
    for (const label of stopLabels) {
      const idx = texts.findIndex((t, i) => i > start && new RegExp(`^${label}$`, 'i').test(t));
      if (idx >= 0) end = Math.min(end, idx);
    }
    return texts.slice(start + 1, end)
      .filter(t => !/^(Find term in Emtree|Show all subheadings|Show|all subheadings|View author addresses)$/i.test(t))
      .filter(t => t.length > 1 && t.length < 160);
  };

  for (let attempt = 0; attempt < 25; attempt++) {
    const body = textOf(document.body);
    if (/abstract|index terms|Emtree|DOI|authors?|source|publication/i.test(body)) break;
    await sleep(500);
  }

  const body = textOf(document.body);
  const headings = [...document.querySelectorAll('h1,h2,h3,[role="heading"]')]
    .filter(visible)
    .map(textOf)
    .filter(Boolean);

  const title =
    headings.find(t => t.length > 20 && !/embase|search|results?|abstract|index terms/i.test(t)) ||
    labelValue(['Title']) ||
    '';

  const doi = valueAfter('Digital Object Identifier \\(DOI\\)') ||
    (body.match(/\b10\.\d{4,9}\/[-._;()/:A-Z0-9]+/i) || [''])[0];
  const pmid = valueAfter('MEDLINE PMID') ||
    (body.match(/\bPMID[:\s]+(\d{5,})/i) || [,''])[1];
  const id = valueAfter('Embase identification number \\(PUI\\)') ||
    (location.href.match(/[?&]id=([^&]+)/i) || [,''])[1] ||
    (body.match(/\b(?:PUI|LUI|Accession(?: number)?|Embase ID)[:\s#-]+([A-Z]?\d{6,}|L\d{6,})/i) || [,''])[1];
  const year = (body.match(/\b(19|20)\d{2}\b/) || [''])[0];

  const abstract = valueAfter('Abstract') ||
    labelValue(['Abstract']) ||
    '';

  const texts = pageTexts();
  const titleIndex = texts.findIndex(t => t === title);
  const authors = titleIndex >= 0
    ? texts.slice(titleIndex + 1, texts.findIndex((t, i) => i > titleIndex && /^View author addresses$|^Abstract$/i.test(t)))
        .filter(t => t !== ',' && !/^Search by /i.test(t))
        .join('; ')
    : '';

  let source = '';
  for (let i = 0; i < titleIndex - 1; i++) {
    if (/^(19|20)\d{2}$/.test(texts[i + 1]) && !/^(Back to Results|Previous|Next|of|Entry date|Updated date)$/i.test(texts[i])) {
      source = texts[i];
      break;
    }
  }
  source = source ||
    labelValue(['Source', 'Journal', 'Publication', 'Conference']) ||
    '';
  const publicationType = valueAfter('Publication type') ||
    labelValue(['Publication type', 'Document type', 'Type']) ||
    '';
  const language = valueAfter('Language of article') ||
    labelValue(['Language']) ||
    '';

  const indexTerms = [
    ...valuesBetween('Drug terms', ['Disease terms', 'Other terms', 'Additional information']),
    ...valuesBetween('Disease terms', ['Other terms', 'Additional information']),
    ...valuesBetween('Other terms', ['Additional information'])
  ].slice(0, 80);

  const fullTextLinks = [...document.querySelectorAll('a[href]')]
    .filter(visible)
    .map(a => ({ text: textOf(a), href: a.href }))
    .filter(x => /full text|pdf|doi|publisher|find it|link resolver|open access/i.test(`${x.text} ${x.href}`))
    .slice(0, 20);

  return {
    status: title || doi || abstract ? 'ok' : 'partial',
    url: location.href,
    title,
    authors,
    source,
    year,
    doi,
    pmid,
    id,
    publicationType,
    language,
    abstract,
    indexTerms,
    fullTextLinks,
    textSample: title || doi || abstract ? undefined : body.slice(0, 1500)
  };
}
```

## Step 3: Present Detail

Report:

- Title
- Authors
- Source/year
- DOI, PMID, PUI/LUI/accession if found
- Abstract
- Emtree/index terms if found
- Full-text links and whether `embase-download` can follow them

## Notes

- Embase can show different identifiers depending on the institution and UI route. Do not rely on a single ID.
- If a record link opens a modal instead of a page, run the extraction script against the modal content.
