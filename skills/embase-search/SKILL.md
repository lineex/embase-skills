---
name: embase-search
description: Search Embase through the active logged-in Chrome session. Supports quick, advanced, command-line, field-code, Emtree, date, source, publication-type, and language limits.
argument-hint: "[query] [--mode quick|advanced|command] [--field ti|ab|tiab|de|exp|do|au] [--years 2020-2025] [--limit humans,english,article] [--source embase|medline|classic] [--count 25]"
user-invocable: true
disable-model-invocation: false
---

# Embase Search

Search Embase using the current Chrome session. The user must already have access through Embase, an institutional proxy, OpenAthens, Shibboleth, or a similar sign-in route.

For systematic-review, PICO, multi-concept, field-code-heavy, Emtree, date/source/publication-type, or methods-reportable searches, use `embase-advanced-search` instead.

## Mandatory Session Check

Run `embase-session` first. Continue only if it returns `status: "ok"`.

If it returns `login_required`, navigate to `https://www.embase.com` and ask the user to complete institutional login in Chrome. Do not continue until the user confirms or reruns the workflow.

## Browser Rules

- Every `navigate_page` call must include:

```json
{
  "initScript": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
}
```

- Use `evaluate_script` for polling and extraction.
- Do not use `wait_for`.
- Do not use screenshots for data.
- Prefer one script that performs the UI action and returns structured status.

## Query Strategy

### Default Mode

- For systematic review or reproducible medical search requests, use `command` mode.
- For a simple exploratory topic, use Embase quick or advanced search and allow Embase broad mapping.
- If the user gives an exact Embase strategy, preserve it exactly.

### Field Mapping

| User intent | Embase syntax |
|---|---|
| title | `term:ti` |
| abstract | `term:ab` |
| title or abstract | `(term:ti OR term:ab)` |
| author | `smith:au` or `smith/au` |
| DOI | `'10.xxxx/yyyy':do` |
| publication year | `2024:py` or `[2020-2025]/py` |
| index term / descriptor | `'aspirin':de` or `'aspirin'/de` |
| exploded Emtree term | `'aspirin'/exp` |
| language | `english:la` or `[english]/lim` |
| publication type | `article:it` or `[article]/lim` |
| affiliation | `university:ff` |

### Common Limits

Append limits with `AND`:

```text
[humans]/lim
[animals]/lim
[english]/lim
[article]/lim
[conference abstract]/lim
[clinical trial]/lim
[randomized controlled trial]/lim
[meta analysis]/lim
[systematic review]/lim
[medline]/lim
[embase]/lim
[embase classic]/lim
[abstracts]/lim
```

### Query Construction Examples

Simple topic with title/abstract emphasis:

```text
("acute kidney injury":ti OR "acute kidney injury":ab OR "acute kidney injury"/exp)
```

Review-style PICO block:

```text
("sepsis":ti OR "sepsis":ab OR "sepsis"/exp)
AND
("hydrocortisone":ti OR "hydrocortisone":ab OR "hydrocortisone"/exp)
AND
([randomized controlled trial]/lim OR [clinical trial]/lim)
AND [humans]/lim
AND [english]/lim
```

Year range:

```text
AND [2020-2025]/py
```

## Preferred Execution: Command-Line Or Advanced Search UI

Embase does not provide a stable public browser API for this skill. Use the logged-in UI first, while opportunistically reading structured network data if Embase exposes it in the active session.

### Step 1: Open Embase

If the active page is not on Embase, navigate to:

```text
https://www.embase.com
```

### Step 2: Find A Search Box And Submit

Use one `evaluate_script` call. Replace `QUERY_TEXT` with the final Embase query, and choose `mode` as `quick`, `advanced`, or `command`.

```javascript
async () => {
  const query = `QUERY_TEXT`;
  const mode = `command`;
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const textOf = (el) => (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim();
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const disabled = (el) => el.disabled || el.hasAttribute('disabled') || el.getAttribute('aria-disabled') === 'true';
  const setNativeValue = (el, value) => {
    if (el.isContentEditable) {
      el.textContent = value;
      el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: value }));
      return;
    }
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
    if (setter) setter.call(el, value);
    else el.value = value;
    el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: value }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  const clickByText = async (patterns) => {
    const elements = [...document.querySelectorAll('button,a,[role="button"],li,span,div')]
      .filter(visible);
    const found = elements.find(el => patterns.some(re => re.test(textOf(el))));
    if (found) {
      found.click();
      await sleep(700);
      return true;
    }
    return false;
  };

  if (!location.hostname.includes('embase.com')) {
    return { status: 'wrong_site', url: location.href };
  }

  // Try to open the Search menu and the most reproducible search surface.
  await clickByText([/^Search$/i, /Search/i]);
  if (mode === 'command') {
    await clickByText([/Command/i, /Advanced/i]);
  } else if (mode === 'advanced') {
    await clickByText([/Advanced/i]);
  } else {
    await clickByText([/Quick/i]);
  }

  for (let attempt = 0; attempt < 20; attempt++) {
    const inputs = [...document.querySelectorAll('textarea,input[type="search"],input[type="text"],[contenteditable="true"]')]
      .filter(visible);
    const preferred = inputs.find(el => /search|query|command|term|advanced/i.test(
      `${el.getAttribute('aria-label') || ''} ${el.getAttribute('placeholder') || ''} ${el.id || ''} ${el.name || ''}`
    )) || inputs[0];

    if (preferred) {
      preferred.focus();
      setNativeValue(preferred, query);

      await sleep(500);

      let submit = null;
      for (let wait = 0; wait < 20; wait++) {
        const controls = [...document.querySelectorAll('button,input[type="submit"],[role="button"]')]
          .filter(visible);
        submit =
          controls.find(el => /^Show\s+[\d,]+\s+results$/i.test(textOf(el)) && !disabled(el)) ||
          controls.find(el => /^Show results$/i.test(textOf(el)) && !disabled(el)) ||
          controls.find(el => /^(Search|Run|Submit|Find)$/i.test(textOf(el)) && !disabled(el));
        if (submit) break;
        await sleep(500);
      }

      if (submit) {
        const clickedLabel = textOf(submit);
        setTimeout(() => submit.click(), 0);
        return {
          status: 'submitted',
          query,
          mode,
          url: location.href,
          clicked: clickedLabel,
          message: 'Search click scheduled. Poll for the results page, then run embase-parse-results.'
        };
      }

      setTimeout(() => preferred.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })), 0);
      return {
        status: 'submitted_enter',
        query,
        mode,
        url: location.href,
        message: 'Enter submit scheduled. Poll for the results page, then run embase-parse-results.'
      };
    }

    await sleep(500);
  }

  return {
    status: 'search_box_not_found',
    query,
    mode,
    url: location.href,
    bodyTextSample: (document.body?.innerText || '').slice(0, 1000)
  };
}
```

### Step 3: Parse Results

After submission, run `embase-parse-results`.

## Opportunistic Network Extraction

If the UI triggers JSON or XHR responses containing result records, prefer those over DOM parsing:

```javascript
async () => {
  return performance.getEntriesByType('resource')
    .filter(r => /embase|search|result|record|api/i.test(r.name))
    .map(r => ({ name: r.name, initiatorType: r.initiatorType, duration: Math.round(r.duration) }))
    .slice(-50);
}
```

Only call discovered endpoints with same-origin `fetch` and the active browser session. Do not copy cookies or tokens out of the browser.

## Result Presentation

Display:

```text
Found {total} Embase results for:
{final_query}

| # | Title | Authors | Source | Year | DOI | ID |
|---|---|---|---|---|---|---|
```

Then offer:

- `embase-paper-detail` for a selected result.
- `embase-export` for RIS/CSV/Excel/XML export.
- `embase-navigate-pages` for more results.

## Notes

- Embase Broad search maps terms to Emtree and free text. Explain when you use it.
- For review-grade strategies, prefer explicit `:ti`, `:ab`, `/exp`, `/de`, `/lim`, and `/py` syntax.
- If Chinese terms are supplied for biomedical topics, translate to English query terms and tell the user which terms were used.
