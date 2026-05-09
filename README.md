# embase-skills

[English](#embase-skills) | [中文](#embase-skills-中文说明)

---

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

---

# embase-skills (中文说明)

`embase-skills` 提供了基于浏览器的 Embase 文献检索技能，通过 Chrome DevTools MCP 实现。其设计遵循了 `cookjohn/wos-skills` 使用的会话模型：用户在 Chrome 中登录数据库，技能复用该活跃的浏览器会话进行搜索、解析、导出和全文获取。

## 前置条件

- Claude Code 或其他可以加载 `agents/` 和 `skills/` 的 Agent 运行时。
- Chrome DevTools MCP。
- 具有机构 Embase 访问权限的 Chrome 浏览器。
- Zotero 桌面版（可选），用于通过本地 Connector API 导入 RIS。

## 推荐的 Chrome DevTools MCP 配置

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

## 登录模型

1. 打开 Chrome。
2. 访问 `https://www.embase.com`。
3. 在 Chrome 中自行完成机构登录、OpenAthens、Shibboleth、MFA 或验证码验证。
4. 仅在页面显示活跃的 Embase 检索界面后运行 Embase 技能。

Agent 不得处理密码、Cookie、令牌、MFA 代码或验证码答案。

## Agent 角色

`embase-researcher` 协调整个工作流：

- `embase-session`
- `embase-search`
- `embase-advanced-search`
- `embase-parse-results`
- `embase-navigate-pages`
- `embase-paper-detail`
- `embase-export`
- `embase-download`

## 技能列表

| 技能 | 用途 |
|---|---|
| `embase-session` | 检查活跃的 Embase 登录/会话状态。 |
| `embase-search` | 运行简单的快速检索或提交已构建的命令行检索。 |
| `embase-advanced-search` | 构建并运行可重复的多概念高级检索，支持 Emtree、字段代码、年份、限制条件、来源和出版类型。 |
| `embase-parse-results` | 从可见结果中提取结构化元数据。 |
| `embase-navigate-pages` | 翻页并重新解析。 |
| `embase-paper-detail` | 提取完整记录元数据、摘要、DOI、PMID、PUI/LUI、Emtree 术语和链接。 |
| `embase-export` | 导出 RIS, CSV, Excel, XML, text, Word, PDF 或 Zotero 就绪的 RIS。 |
| `embase-download` | 访问合法的全文、DOI、出版商、开放获取或链接解析器链接。 |

## 使用示例

```text
/embase-session
/embase-search "sepsis hydrocortisone" --mode command --limit humans,english,randomized-controlled-trial --years 2020-2025
/embase-advanced-search "sepsis AND hydrocortisone" --fields tiab,exp --limits humans,english,rct --years 2020-2025
/embase-paper-detail 1
/embase-export ris --range 1-500 --output full-record --include-query
/embase-download current
```

## 综述级查询模式

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

## Zotero 导入

从 Embase 导出 RIS 后，可以将已知的 RIS 文件推送到 Zotero Connector：

```bash
python skills/embase-export/scripts/push_to_zotero.py path/to/export.ris
```

Zotero 桌面版必须正在运行，并且已在 Zotero 中选中目标分类。

## 设计理念

- **会话优先**：每个工作流都从确认已登录的 Embase 页面开始。
- **UI 优先**：Embase 未提供稳定的公开 API，因此默认路径是通过结构化 DOM 提取进行经过身份验证的 UI 操作。
- **网络感知**：如果活跃的 Embase 会话暴露了稳定的同源 JSON 响应，则优先使用结构化数据而非 DOM 文本。
- **可重复性**：系统综述检索应保留精确的 Embase 语法，包括字段代码和限制条件。

License
MIT
