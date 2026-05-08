---
name: embase-session
description: Check and recover an active Embase browser session before running Embase searches, exports, or full-record extraction.
argument-hint: "[optional target URL]"
user-invocable: true
disable-model-invocation: false
---

# Embase Session

Use this skill before any Embase operation. It mirrors the WoS login model: the user logs in through Chrome, and the agent reuses that active browser session through Chrome DevTools MCP.

## Rules

- Never request or handle credentials, cookies, access tokens, MFA codes, or CAPTCHA answers.
- If login is needed, navigate to Embase and pause with a clear instruction for the user to complete institutional login in Chrome.
- Every `navigate_page` call must include:

```json
{
  "initScript": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
}
```

- Do not use `wait_for`. Poll with `evaluate_script`.
- Do not use screenshots for session detection.

## Step 1: Navigate To Embase If Needed

If the active page is not on `embase.com`, run:

```json
{
  "url": "https://www.embase.com",
  "initScript": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
}
```

If the user supplied a target URL, use that URL only if it is on `embase.com`.

## Step 2: Inspect Session State

Run one `evaluate_script` call:

```javascript
async () => {
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  for (let attempt = 0; attempt < 30; attempt++) {
    const href = location.href;
    const host = location.hostname;
    const text = document.body?.innerText || '';
    const buttons = [...document.querySelectorAll('button,a,input')]
      .map(el => ({
        text: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim(),
        href: el.href || ''
      }))
      .filter(x => x.text || x.href)
      .slice(0, 80);

    const hasSearchSurface =
      /Search/i.test(text) &&
      (/Advanced/i.test(text) || /Quick search/i.test(text) || /Emtree/i.test(text) || /Results/i.test(text));

    const loginSignals = [
      /sign in/i,
      /log in/i,
      /institution/i,
      /OpenAthens/i,
      /Shibboleth/i,
      /remote access/i,
      /choose your organization/i,
      /access through your institution/i
    ];
    const loginRequired = loginSignals.some(re => re.test(text)) && !hasSearchSurface;

    const blockedSignals = [
      /captcha/i,
      /verify you are human/i,
      /unusual traffic/i,
      /access denied/i,
      /too many requests/i
    ];
    const blocked = blockedSignals.some(re => re.test(text));

    if (host.includes('embase.com') && hasSearchSurface && !loginRequired) {
      return {
        status: 'ok',
        url: href,
        message: 'Active Embase session detected.',
        buttons
      };
    }

    if (blocked) {
      return {
        status: 'blocked',
        url: href,
        message: 'Browser is showing a verification or access block. User action is required.',
        buttons
      };
    }

    if (loginRequired || !host.includes('embase.com')) {
      return {
        status: 'login_required',
        url: href,
        message: 'Complete Embase institutional login in Chrome, then rerun the skill.',
        buttons
      };
    }

    await sleep(500);
  }

  return {
    status: 'timeout',
    url: location.href,
    message: 'Could not confirm Embase readiness after polling.'
  };
}
```

## Step 3: Report State

- `ok`: Continue to the requested Embase skill.
- `login_required`: Tell the user to complete login in Chrome, then rerun the requested workflow.
- `blocked`: Stop automation and ask the user to resolve the browser prompt.
- `timeout`: Explain that the page did not settle and provide the current URL.

## Recovery Notes

- If the browser has just followed a DOI or publisher link, navigate back to `https://www.embase.com` before continuing.
- If the session is anonymous, searches may still work, but large exports are limited. Prefer a registered institutional login for systematic review exports.
