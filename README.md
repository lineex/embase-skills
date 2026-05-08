# embase-skills

`embase-skills` provides browser-based Embase literature-search skills through Chrome DevTools MCP. The design follows the session model used by `cookjohn/wos-skills`: the user logs in to the database in Chrome, and the skills reuse that active browser session for search, parsing, export, and full-text handoff.

## Prerequisites

- Claude Code or another agent runtime that can load `agents/` and `skills/`.
- Chrome DevTools MCP.
- Chrome browser with institutional Embase access.
- Zotero desktop app, optional, for RIS import through the local Connector API.

## Recommended Chrome DevTools MCP Configuration

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "-y",
        "chrome-devtools-mcp@latest",
        "--ignoreDefaultChromeArg=--enable-automation",
        "--ignoreDefaultChromeArg=--disable-infobars",
        "--chromeArg=--disable-blink-features=AutomationControlled"
      ]
    }
  }
}
```

## Login Model

1. Open Chrome.
2. Go to `https://www.embase.com`.
3. Complete institutional login, OpenAthens, Shibboleth, MFA, or CAPTCHA yourself in Chrome.
4. Run the Embase skills only after the page shows an active Embase search surface.

The agent must not handle passwords, cookies, tokens, MFA codes, or CAPTCHA answers.

## Agent

`embase-researcher` coordinates the whole workflow:

- `embase-session`
- `embase-search`
- `embase-advanced-search`
- `embase-parse-results`
- `embase-navigate-pages`
- `embase-paper-detail`
- `embase-export`
- `embase-download`

## Skills

| Skill | Purpose |
|---|---|
| `embase-session` | Check active Embase login/session state. |
| `embase-search` | Run simple quick searches or submit already-built command-line searches. |
| `embase-advanced-search` | Build and run reproducible multi-concept advanced searches with Emtree, field codes, years, limits, sources, and publication types. |
| `embase-parse-results` | Extract structured metadata from visible results. |
| `embase-navigate-pages` | Navigate result pages and re-parse. |
| `embase-paper-detail` | Extract full-record metadata, abstract, DOI, PMID, PUI/LUI, Emtree terms, and links. |
| `embase-export` | Export RIS, CSV, Excel, XML, text, Word, PDF, or Zotero-ready RIS. |
| `embase-download` | Follow legitimate full-text, DOI, publisher, open-access, or link-resolver links. |

## Usage Examples

```text
/embase-session
/embase-search "sepsis hydrocortisone" --mode command --limit humans,english,randomized-controlled-trial --years 2020-2025
/embase-advanced-search "sepsis AND hydrocortisone" --fields tiab,exp --limits humans,english,rct --years 2020-2025
/embase-paper-detail 1
/embase-export ris --range 1-500 --output full-record --include-query
/embase-download current
```

## Review-Grade Query Pattern

```text
("sepsis":ti OR "sepsis":ab OR "sepsis"/exp)
AND
("hydrocortisone":ti OR "hydrocortisone":ab OR "hydrocortisone"/exp)
AND
([randomized controlled trial]/lim OR [clinical trial]/lim)
AND [humans]/lim
AND [english]/lim
AND [2020-2025]/py
```

## Zotero

After exporting RIS from Embase, push a known RIS file to Zotero Connector:

```bash
python skills/embase-export/scripts/push_to_zotero.py path/to/export.ris
```

Zotero desktop must be running, and the target collection should be selected in Zotero.

## Design Notes

- Session-first: every workflow starts by confirming the logged-in Embase page.
- UI-first: Embase does not expose a stable public browser API for these skills, so the default path is authenticated UI operation with structured DOM extraction.
- Network-aware: if the active Embase session exposes stable same-origin JSON responses, prefer structured data over DOM text.
- Reproducible: systematic-review searches should preserve exact Embase syntax, including field codes and limits.
