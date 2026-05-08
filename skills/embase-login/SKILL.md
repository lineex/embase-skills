---
name: embase-login
description: Guide the user to log in to Embase via institution or credentials.
user-invocable: true
disable-model-invocation: false
---

# Embase Login

Guides the authentication process for Embase.

## Steps

### Step 1: Navigate to Login Page

Go to `https://www.embase.com/login`.

### Step 2: Handle Institutional Login

If the page shows "Check access", attempt to click it or wait for the user to complete the login in the browser window.

### Step 3: Verify

Once logged in, the user should be redirected to `https://www.embase.com/search/quick`.
Use `/embase-check-login` to verify success.
