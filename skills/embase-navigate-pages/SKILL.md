---
name: embase-navigate-pages
description: Navigate Embase search result pages and parse the new page through the active browser session.
argument-hint: "[next|prev|previous|page number]"
user-invocable: true
disable-model-invocation: false
---

# Embase Navigate Pages

Move through Embase result pages after `embase-search`. Preserve the current search context and parse records after navigation.

## Mandatory Session Check

Run `embase-session` first if the current browser page is not clearly an Embase result page. Continue only when the active page is on `embase.com`.

## Rules

- Do not navigate away from Embase for pagination.
- Use `evaluate_script` for page interaction and polling.
- Do not use screenshots.
- Do not use `wait_for`.
- If direct URL pagination is not obvious, click the visible pagination control.

## Step 1: Navigate

Use one `evaluate_script` call. Replace `TARGET_PAGE_OR_ACTION` with `next`, `previous`, or a number.

```javascript
async () => {
  const target = `TARGET_PAGE_OR_ACTION`;
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const textOf = (el) => clean(el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '');
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };

  if (!location.hostname.includes('embase.com')) {
    return { status: 'wrong_site', url: location.href };
  }

  const before = location.href + '|' + clean(document.body.innerText).slice(0, 500);

  const clickControl = async () => {
    const controls = [...document.querySelectorAll('button,a,input,[role="button"],[role="spinbutton"]')]
      .filter(visible);

    if (/^\d+$/.test(target)) {
      const targetNumber = Number(target);
      const exact = controls.find(el => textOf(el) === String(targetNumber));
      if (exact) {
        exact.click();
        return true;
      }

      const pageInput = controls.find(el =>
        /page/i.test(`${el.getAttribute('aria-label') || ''} ${el.getAttribute('placeholder') || ''} ${el.name || ''}`) &&
        ('value' in el)
      );
      if (pageInput) {
        pageInput.focus();
        pageInput.value = String(targetNumber);
        pageInput.dispatchEvent(new Event('input', { bubbles: true }));
        pageInput.dispatchEvent(new Event('change', { bubbles: true }));
        pageInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
        return true;
      }
    }

    const patterns = /^(next|n)$/i.test(target)
      ? [/next/i, /older/i, /›|»/]
      : [/prev/i, /previous/i, /back/i, /‹|«/];

    const control = controls.find(el => patterns.some(re => re.test(textOf(el))));
    if (control) {
      control.click();
      return true;
    }

    return false;
  };

  const clicked = await clickControl();
  if (!clicked) {
    return {
      status: 'pagination_control_not_found',
      target,
      url: location.href,
      controls: [...document.querySelectorAll('button,a,input,[role="button"]')]
        .filter(visible)
        .map(textOf)
        .filter(Boolean)
        .slice(0, 80)
    };
  }

  for (let attempt = 0; attempt < 30; attempt++) {
    await sleep(500);
    const now = location.href + '|' + clean(document.body.innerText).slice(0, 500);
    if (now !== before && /result|record|article|abstract|doi/i.test(clean(document.body.innerText))) {
      return {
        status: 'ok',
        target,
        url: location.href,
        message: 'Navigation completed. Run embase-parse-results next.'
      };
    }
  }

  return {
    status: 'timeout',
    target,
    url: location.href,
    message: 'Pagination click was sent, but the page did not visibly change.'
  };
}
```

## Step 2: Parse Results

Run `embase-parse-results` immediately after `status: "ok"`.

## Notes

- If the user asks for a page number and Embase only exposes infinite scroll, scroll with `evaluate_script`, then parse newly visible records.
- Keep the original query and export range in memory for later `embase-export`.
