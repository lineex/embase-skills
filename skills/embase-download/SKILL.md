---
name: embase-download
description: Follow Embase full-text, DOI, publisher, open-access, or link-resolver links for a selected record and report PDF availability.
argument-hint: "[result # | DOI | PMID | title | current]"
user-invocable: true
disable-model-invocation: false
---

# Embase Download

Use Embase full-text links to reach publisher, DOI, open-access, or institutional link-resolver pages. This skill reports what is available and clicks legitimate full-text/PDF links when the active session has access.

## Rules

- Use the user's logged-in Chrome session.
- Do not bypass paywalls, CAPTCHA, DRM, or access controls.
- Do not request credentials, cookies, or tokens.
- Use `evaluate_script` to find and click links.
- Do not use screenshots for link discovery.
- If a publisher page opens, the Embase session may be lost from performance history. Return to `https://www.embase.com` before more Embase actions.

## Step 1: Ensure Record Context

- If the active page is an Embase full-record page, continue.
- If the user gives a result number or identifier, run `embase-paper-detail` first.
- If full-text links were extracted by `embase-paper-detail`, prefer those links.

## Step 2: Find Full-Text Links

Run:

```javascript
async () => {
  const target = `TARGET_OR_CURRENT`;
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

  const links = [...document.querySelectorAll('a[href],button,[role="button"]')]
    .filter(visible)
    .map(el => ({
      text: textOf(el),
      href: el.href || el.getAttribute('data-href') || '',
      element: el
    }))
    .filter(x => /full text|pdf|publisher|doi|open access|find it|link resolver|view at publisher|article/i.test(`${x.text} ${x.href}`));

  const ranked = links
    .map(x => ({
      text: x.text,
      href: x.href,
      score:
        (/pdf/i.test(`${x.text} ${x.href}`) ? 5 : 0) +
        (/full text|open access/i.test(x.text) ? 4 : 0) +
        (/doi\.org|publisher/i.test(`${x.text} ${x.href}`) ? 2 : 0)
    }))
    .sort((a, b) => b.score - a.score);

  return {
    status: ranked.length ? 'ok' : 'no_links_found',
    url: location.href,
    links: ranked.slice(0, 20),
    target
  };
}
```

## Step 3: Follow The Best Link

If the user asked to download/open full text and the link list contains a likely PDF or full-text link, click the best link:

```javascript
async () => {
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const textOf = (el) => clean(el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('title') || '');
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };

  const candidates = [...document.querySelectorAll('a[href],button,[role="button"]')]
    .filter(visible)
    .map(el => ({
      text: textOf(el),
      href: el.href || el.getAttribute('data-href') || '',
      element: el
    }))
    .filter(x => /full text|pdf|publisher|doi|open access|find it|link resolver|view at publisher|article/i.test(`${x.text} ${x.href}`))
    .map(x => ({
      ...x,
      score:
        (/pdf/i.test(`${x.text} ${x.href}`) ? 5 : 0) +
        (/full text|open access/i.test(x.text) ? 4 : 0) +
        (/doi\.org|publisher/i.test(`${x.text} ${x.href}`) ? 2 : 0)
    }))
    .sort((a, b) => b.score - a.score);

  const best = candidates[0];
  if (!best) return { status: 'no_links_found', url: location.href };

  best.element.scrollIntoView({ block: 'center', inline: 'center' });
  await sleep(200);
  best.element.click();
  await sleep(2000);

  return {
    status: 'clicked',
    clicked: { text: best.text, href: best.href },
    url: location.href,
    message: 'A full-text link was opened. Inspect the new page for PDF availability.'
  };
}
```

## Step 4: Inspect Publisher Page

If a new page opens, inspect it:

```javascript
async () => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const text = clean(document.body?.innerText || '');
  const links = [...document.querySelectorAll('a[href],button,[role="button"]')]
    .map(el => ({
      text: clean(el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('title') || ''),
      href: el.href || el.getAttribute('data-href') || ''
    }))
    .filter(x => /pdf|download|full text|view article|open access/i.test(`${x.text} ${x.href}`))
    .slice(0, 30);

  const access =
    /purchase|rent|subscribe|login|sign in|institution/i.test(text) && !/open access|download pdf/i.test(text)
      ? 'restricted_or_login_required'
      : links.some(x => /pdf|download/i.test(`${x.text} ${x.href}`))
        ? 'pdf_link_available'
        : 'landing_page_available';

  return {
    status: 'ok',
    url: location.href,
    access,
    links,
    title: document.title
  };
}
```

## Reporting

Report:

- Which link was followed.
- Whether a PDF link is available.
- Whether the publisher page requires additional institutional login.
- The final page URL.

Do not claim that a PDF was downloaded unless the browser or filesystem confirms it.
