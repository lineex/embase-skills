---
name: embase-check-login
description: Check if the current browser session is logged into Embase.
user-invocable: true
disable-model-invocation: false
---

# Embase Check Login

Checks the authentication status of the current Embase session.

## Steps

### Step 1: Check Cookies and URL

Use `evaluate_script` to check for signs of a valid session.

```javascript
() => {
  const isLoggedIn = !document.body.innerText.includes("Sign in") && 
                     !document.location.href.includes("/landing");
  const hasEntitlements = !!document.cookie.match(/optout|ELS_AUTH|ELS_USER/);
  
  return {
    isLoggedIn,
    url: document.location.href,
    cookiesFound: hasEntitlements
  };
}
```

### Step 2: Report Status

If not logged in, suggest running `/embase-login`.
