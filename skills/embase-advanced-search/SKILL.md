---
name: embase-advanced-search
description: Build and run reproducible Embase advanced searches with concept blocks, field codes, Emtree terms, mapping controls, limits, sources, publication types, languages, years, age/gender/animal filters, and exact command-line strategies.
argument-hint: "[topic|PICO|exact strategy] [--concepts P,I,C,O] [--fields tiab|de|exp|all] [--years 2020-2025] [--limits humans,english,article,rct] [--source embase,medline] [--map on|off] [--count 25]"
user-invocable: true
disable-model-invocation: false
---

# Embase Advanced Search

Use this skill for systematic-review, scoping-review, evidence-map, pharmacovigilance, drug/disease/device, or any multi-concept Embase search that should be reproducible. It builds an explicit Embase strategy, runs it through the active logged-in Chrome session, then hands off to `embase-parse-results`.

## Mandatory Session Check

Run `embase-session` first. Continue only if it returns `status: "ok"`.

If it returns `login_required`, navigate to `https://www.embase.com` and ask the user to complete institutional login in Chrome. Never request passwords, cookies, tokens, MFA codes, or CAPTCHA answers.

## Browser Rules

- Every `navigate_page` call must include:

```json
{
  "initScript": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
}
```

- Use the active logged-in Chrome session.
- Use `evaluate_script` for interaction, polling, and extraction.
- Do not use screenshots for data extraction.
- Do not use `wait_for`; use internal polling loops.
- Return a typed status such as `submitted`, `results_visible`, `login_required`, `search_box_not_found`, or `submit_not_found`.

## When To Use This Skill

Use `embase-advanced-search` instead of `embase-search` when the user asks for:

- PICO/PICOS/PECO search strategies.
- Systematic review or meta-analysis searches.
- Emtree explosion or descriptor-only searching.
- Exact field-code searches such as `:ti`, `:ab`, `/exp`, `/de`, `/lim`, `/py`.
- Date, language, source, publication type, age, gender, animal, EBM, or quick-limit filters.
- A search strategy that must be reported in a methods section or appendix.

For a one-word exploratory search, use `embase-search`.

## Input Normalization

Turn the user request into this plan:

```json
{
  "mode": "command",
  "concepts": [
    {
      "label": "population",
      "terms": ["sepsis", "septic shock"],
      "fields": ["ti", "ab", "exp"],
      "operator": "OR"
    },
    {
      "label": "intervention",
      "terms": ["hydrocortisone", "corticosteroid"],
      "fields": ["ti", "ab", "exp"],
      "operator": "OR"
    }
  ],
  "betweenConcepts": "AND",
  "limits": ["humans", "english", "randomized controlled trial"],
  "sources": ["embase", "medline"],
  "years": "2020-2025",
  "mapping": "off",
  "resultCount": 25
}
```

If the user provides an exact Embase strategy, set:

```json
{
  "mode": "exact",
  "query": "USER_QUERY_EXACTLY_AS_GIVEN"
}
```

## Query Construction

### Term Quoting

- Quote phrases: `"septic shock":ti`.
- Prefer single quotes for Emtree descriptors: `'sepsis'/exp`.
- Do not translate exact user-provided Embase syntax.
- If the user provides Chinese biomedical concepts, translate terms to English and state the final English strategy.

### Field Expansion

| Requested field | Embase expression |
|---|---|
| `ti` | `"term":ti` |
| `ab` | `"term":ab` |
| `tiab` | `("term":ti OR "term":ab)` |
| `de` | `'term'/de` |
| `exp` | `'term'/exp` |
| `all` | `"term"` |
| `doi` | `'10.xxxx/yyyy':do` |
| `author` | `smith:au` |

For a concept block with `ti`, `ab`, and `exp`:

```text
("sepsis":ti OR "sepsis":ab OR 'sepsis'/exp OR "septic shock":ti OR "septic shock":ab OR 'septic shock'/exp)
```

### Limits

Append limits with `AND`:

```text
[humans]/lim
[animals]/lim
[english]/lim
[abstracts]/lim
[article]/lim
[conference abstract]/lim
[clinical trial]/lim
[randomized controlled trial]/lim
[controlled clinical trial]/lim
[meta analysis]/lim
[systematic review]/lim
[review]/lim
[embase]/lim
[medline]/lim
[embase classic]/lim
```

### Years

Use:

```text
AND [2020-2025]/py
```

For a single year:

```text
AND [2025]/py
```

### Proximity

Use proximity only when the user requests it or when it materially improves specificity:

```text
("acute" NEXT/1 "kidney injury":ti,ab)
("mechanical" NEAR/3 "ventilation":ti,ab)
```

If uncertain about institution-specific Embase syntax support, keep standard Boolean blocks instead.

## Example Strategies

### RCT Search

```text
("sepsis":ti OR "sepsis":ab OR 'sepsis'/exp OR "septic shock":ti OR "septic shock":ab OR 'septic shock'/exp)
AND
("hydrocortisone":ti OR "hydrocortisone":ab OR 'hydrocortisone'/exp OR "corticosteroid":ti OR "corticosteroid":ab OR 'corticosteroid'/exp)
AND
([randomized controlled trial]/lim OR [clinical trial]/lim)
AND [humans]/lim
AND [english]/lim
AND [2020-2025]/py
```

### Diagnostic Search

```text
("sepsis":ti OR "sepsis":ab OR 'sepsis'/exp)
AND
("procalcitonin":ti OR "procalcitonin":ab OR 'procalcitonin'/exp)
AND
("diagnosis":ti OR "diagnosis":ab OR 'diagnosis'/exp OR "sensitivity and specificity"/exp)
AND [humans]/lim
```

### Source-Specific Search

```text
("acute respiratory distress syndrome":ti OR "acute respiratory distress syndrome":ab OR 'acute respiratory distress syndrome'/exp)
AND [embase]/lim
AND [medline]/lim
```

## Preferred Execution

### Step 1: Navigate To Advanced Search

Navigate to:

```text
https://www.embase.com/search/advanced
```

Use the required `initScript`.

### Step 2: Submit The Advanced Strategy

Replace `FINAL_QUERY` with the final Embase query. Set `DISABLE_MAPPING` to `true` when the final query already contains Embase field codes or exact command syntax. This script is deliberately label-driven because Embase UI class names vary.

```javascript
async () => {
  const query = `FINAL_QUERY`;
  const disableMapping = Boolean(`DISABLE_MAPPING_TRUE_OR_FALSE` === 'true');
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const textOf = (el) => clean(el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('title') || '');
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
    const controls = [...document.querySelectorAll('button,a,[role="button"],span,li')]
      .filter(visible);
    const found = controls.find(el => patterns.some(re => re.test(textOf(el))));
    if (found) {
      found.click();
      await sleep(700);
      return true;
    }
    return false;
  };
  const setCheckbox = async (labelPattern, wanted) => {
    const labels = [...document.querySelectorAll('label')]
      .filter(visible);
    const label = labels.find(el =>
      labelPattern.test(textOf(el)) ||
      labelPattern.test(el.getAttribute('title') || '')
    );
    const checkbox =
      (label?.htmlFor ? document.getElementById(label.htmlFor) : null) ||
      label?.querySelector?.('input[type="checkbox"],[role="checkbox"]') ||
      (label?.previousElementSibling?.matches?.('input[type="checkbox"],[role="checkbox"]') ? label.previousElementSibling : null) ||
      label?.parentElement?.querySelector?.('input[type="checkbox"],[role="checkbox"]') ||
      [...document.querySelectorAll('input[type="checkbox"],[role="checkbox"]')]
        .find(el => labelPattern.test(`${el.getAttribute('aria-label') || ''} ${el.getAttribute('title') || ''}`));
    if (!checkbox) return false;
    const checked = checkbox.checked || checkbox.getAttribute('aria-checked') === 'true';
    if (checked !== wanted) {
      if (label && visible(label)) {
        label.click();
      } else {
        checkbox.click();
      }
      await sleep(250);
      if ((checkbox.checked || checkbox.getAttribute('aria-checked') === 'true') !== wanted) {
        checkbox.checked = wanted;
        checkbox.dispatchEvent(new Event('input', { bubbles: true }));
        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
    return true;
  };

  if (!location.hostname.includes('embase.com')) {
    return { status: 'wrong_site', url: location.href };
  }

  if (/sign in|log in|OpenAthens|Shibboleth|access through your institution/i.test(document.body?.innerText || '') &&
      !/Advanced|Search|Emtree/i.test(document.body?.innerText || '')) {
    return { status: 'login_required', url: location.href };
  }

  if (!/\/search\/advanced|advancedSearch/i.test(location.href)) {
    await clickByText([/^Search$/i, /Search/i]);
    await clickByText([/^Advanced$/i, /Advanced/i]);
  }

  if (disableMapping) {
    await clickByText([/^Mapping\b/i, /Mapping/i]);
    await setCheckbox(/Map to preferred term in Emtree/i, false);
    await setCheckbox(/Search also as free text in all fields/i, false);
    await setCheckbox(/Explode using narrower Emtree terms/i, false);
    await setCheckbox(/Search as broadly as possible/i, false);
    await setCheckbox(/Limit to terms indexed in article as 'major focus'/i, false);
  }

  for (let attempt = 0; attempt < 20; attempt++) {
    const inputs = [...document.querySelectorAll('textarea,input[type="search"],input[type="text"],[contenteditable="true"]')]
      .filter(visible);

    const preferred =
      inputs.find(el => /advanced|query|search|term|command|strategy/i.test(
        `${el.getAttribute('aria-label') || ''} ${el.getAttribute('placeholder') || ''} ${el.id || ''} ${el.name || ''}`
      )) ||
      inputs.sort((a, b) => (b.getBoundingClientRect().width * b.getBoundingClientRect().height) - (a.getBoundingClientRect().width * a.getBoundingClientRect().height))[0];

    if (!preferred) {
      await sleep(500);
      continue;
    }

    preferred.focus();
    setNativeValue(preferred, query);
    await sleep(800);

    let submit = null;
    for (let wait = 0; wait < 24; wait++) {
      const controls = [...document.querySelectorAll('button,input[type="submit"],[role="button"]')]
        .filter(visible);
      submit =
        controls.find(el => /^Show\s+[\d,]+\s+results$/i.test(textOf(el)) && !disabled(el)) ||
        controls.find(el => /^Show results$/i.test(textOf(el)) && !disabled(el)) ||
        controls.find(el => /^Search\s*>?$/i.test(textOf(el)) && !disabled(el)) ||
        controls.find(el => /^(Search|Run|Submit|Find)$/i.test(textOf(el)) && !disabled(el));
      if (submit) break;
      await sleep(500);
    }

    if (submit) {
      const clicked = textOf(submit);
      setTimeout(() => submit.click(), 0);
      return {
        status: 'submitted',
        mode: 'advanced',
        mappingDisabled: disableMapping,
        query,
        clicked,
        url: location.href,
        message: 'Advanced search click scheduled. Poll for the results page, then run embase-parse-results.'
      };
    }

    setTimeout(() => preferred.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })), 0);
    return {
      status: 'submitted_enter',
      mode: 'advanced',
      mappingDisabled: disableMapping,
      query,
      url: location.href,
      message: 'Advanced search submitted with Enter. Poll for the results page, then run embase-parse-results.'
    };
  }

  return {
    status: 'search_box_not_found',
    url: location.href,
    query,
    controls: [...document.querySelectorAll('button,a,input,textarea,[role="button"]')]
      .filter(visible)
      .map(el => ({
        tag: el.tagName,
        text: textOf(el),
        label: el.getAttribute('aria-label') || '',
        placeholder: el.getAttribute('placeholder') || ''
      }))
      .slice(0, 120),
    textSample: (document.body?.innerText || '').slice(0, 1500)
  };
}
```

### Step 3: Poll For Results

Run:

```javascript
async () => {
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  for (let attempt = 0; attempt < 90; attempt++) {
    const text = document.body?.innerText || '';
    const total = (text.match(/([\d,]+)\s+results?\s+for\s+search/i) || [,''])[1] ||
      (text.match(/Show\s+([\d,]+)\s+results/i) || [,''])[1];

    if (/results?|history|export|refine|filters/i.test(text) &&
        /result|advancedSearch|history/i.test(location.href)) {
      return {
        status: 'results_visible',
        url: location.href,
        title: document.title,
        totalResults: total || null
      };
    }

    if (/no results|0 results|no records/i.test(text)) {
      return {
        status: 'no_results',
        url: location.href,
        title: document.title
      };
    }

    if (/sign in|log in|OpenAthens|Shibboleth|access through your institution/i.test(text) &&
        !/results?|history|export/i.test(text)) {
      return {
        status: 'login_required',
        url: location.href,
        title: document.title
      };
    }

    await sleep(1000);
  }

  return {
    status: 'timeout',
    url: location.href,
    title: document.title,
    textSample: (document.body?.innerText || '').slice(0, 1500)
  };
}
```

### Step 4: Parse Results

If polling returns `results_visible`, run `embase-parse-results`.

## Advanced UI Panels

Prefer explicit command-line syntax over clicking panels when the goal is reproducibility. Use panels only when the user explicitly needs Embase mapping suggestions or visible UI filters.

Panel labels commonly include:

- Search Mapping
- Date
- Sources
- Fields
- Quick limits
- EBM
- Pub. types
- Languages
- Gender
- Age
- Animal

If panel interaction is required, click the panel by label, select visible controls, then click `Apply`. Always report the final full query shown by Embase if available.

## Output Format

Always report:

```text
Advanced Embase query:
{final_query}

Search status: {status}
Results: {totalResults if available}
```

Then show the parsed result table from `embase-parse-results`.

## Quality Checks

Before submitting:

- Each concept block is wrapped in parentheses.
- Synonyms within a concept are joined by `OR`.
- Separate concepts are joined by `AND`, unless the user specifies otherwise.
- Limits are appended at the end.
- Date range uses `/py`.
- Emtree explosion `/exp` is used only for biomedical terms that plausibly map to Emtree.
- Exact user-provided Embase syntax is not silently rewritten.
- Mapping is disabled when the query already uses exact field codes, `/exp`, `/de`, `/lim`, or `/py`.

## Fallbacks

- If Advanced page selectors change, use the largest visible search input/textarea and the exact `Show results` button.
- If the Advanced UI rejects command syntax, run the same query from the Quick search surface or the visible command/search box and clearly report the route used.
- If no submit button appears, return `search_box_not_found` or `submit_not_found` with visible controls so the skill can be updated.
