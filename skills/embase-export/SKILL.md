---
name: embase-export
description: Export Embase search results to RIS, CSV, Excel, XML, text, Word, PDF, or Zotero-ready RIS through the active logged-in browser session.
argument-hint: "[ris|csv|excel|xml|txt|word|pdf|zotero] [--range all|page|1-500] [--output titles|citations|abstracts|full-record] [--include-query]"
user-invocable: true
disable-model-invocation: false
---

# Embase Export

Export records from the active Embase result page using the logged-in Chrome session. This follows the same session-first model as WoS skills: the browser owns authentication, and the skill only operates the authenticated UI.

## Mandatory Session Check

Run `embase-session` first unless the active page is already a visible Embase result page.

## Rules

- Do not request or copy credentials, cookies, tokens, or download URLs that contain secrets.
- Use `evaluate_script` for selection and export UI actions.
- Do not use screenshots for data.
- Do not use `wait_for`.
- Keep batches within Embase limits. Registered sessions may export up to the institution/agreement limit, commonly 10,000 records per batch; anonymous sessions are limited to 500 records per batch.
- For Zotero, export RIS first. If a local RIS file path is available, `scripts/push_to_zotero.py` can push it to Zotero Connector.

## Formats

| User asks | Embase export option |
|---|---|
| `ris`, Zotero, EndNote, Mendeley | RIS |
| `csv` | CSV fields by row or column |
| `excel`, `xlsx` | MS Excel fields by row or column |
| `xml` | XML |
| `txt`, text | Plain text |
| `word`, doc | MS Word |
| `pdf` | PDF |

## Output Depth

| User asks | Embase output |
|---|---|
| titles | Titles Only |
| citations | Citations Only |
| abstracts | Citations and Abstracts |
| index terms | Abstract and Index terms |
| full, full-record | Full Record |
| custom fields | Specify the fields to be exported |

Default for review work: RIS + Full Record + Include search query.

## Step 1: Select Records

Use one `evaluate_script` call. Replace `RANGE_SPEC` with `page`, `all`, or a range such as `1-500`.

```javascript
async () => {
  const rangeSpec = `RANGE_SPEC`;
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const textOf = (el) => clean(el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '');
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };
  const click = async (el) => {
    el.scrollIntoView({ block: 'center', inline: 'center' });
    await sleep(150);
    el.click();
    await sleep(500);
  };

  if (!location.hostname.includes('embase.com')) {
    return { status: 'wrong_site', url: location.href };
  }

  const controls = () => [...document.querySelectorAll('button,a,input,[role="button"],label')]
    .filter(visible);

  if (/^all$/i.test(rangeSpec) || /^page$/i.test(rangeSpec)) {
    const selectAll = controls().find(el =>
      /select all|all results|results/i.test(textOf(el)) &&
      /checkbox|select|results/i.test(`${el.getAttribute('role') || ''} ${el.type || ''} ${textOf(el)}`)
    );
    if (selectAll) await click(selectAll);
  } else if (/^\d+\s*-\s*\d+$/.test(rangeSpec)) {
    const [start, end] = rangeSpec.split('-').map(s => Number(s.trim()));
    const records = [...document.querySelectorAll('article,[class*="result" i],[class*="record" i],li')]
      .filter(visible)
      .filter(el => textOf(el).length > 80);
    for (let i = start - 1; i < Math.min(end, records.length); i++) {
      const box = records[i].querySelector('input[type="checkbox"],button[role="checkbox"],[role="checkbox"],label');
      if (box) await click(box);
    }
  }

  const exportButton = controls().find(el => /^export$/i.test(textOf(el)) || /export/i.test(textOf(el)));
  if (!exportButton) {
    return {
      status: 'export_button_not_found',
      url: location.href,
      controls: controls().map(textOf).filter(Boolean).slice(0, 80)
    };
  }

  await click(exportButton);
  return {
    status: 'export_opened',
    rangeSpec,
    url: location.href,
    message: 'Export UI opened. Choose format and output next.'
  };
}
```

## Step 2: Choose Format And Output

Use one `evaluate_script` call. Replace values with the requested options.

```javascript
async () => {
  const format = `FORMAT_LABEL`;
  const output = `OUTPUT_LABEL`;
  const includeQuery = Boolean(`INCLUDE_QUERY_TRUE_OR_FALSE` === 'true');
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const textOf = (el) => clean(el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '');
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
  };
  const click = async (el) => {
    el.scrollIntoView({ block: 'center', inline: 'center' });
    await sleep(150);
    el.click();
    await sleep(400);
  };
  const allControls = () => [...document.querySelectorAll('button,a,input,label,select,option,[role="button"],[role="option"],[role="radio"],[role="checkbox"]')]
    .filter(visible);
  const chooseByText = async (patterns) => {
    const found = allControls().find(el => patterns.some(re => re.test(textOf(el))));
    if (found) {
      await click(found);
      return true;
    }
    return false;
  };

  const formatPatterns = {
    ris: [/^RIS\b/i, /Mendeley|EndNote|reference software/i],
    csv: [/CSV.*row/i, /^CSV\b/i],
    excel: [/Excel/i, /XLSX/i],
    xml: [/^XML$/i],
    txt: [/plain text/i, /^text$/i],
    word: [/Word/i],
    pdf: [/^PDF$/i]
  }[format.toLowerCase()] || [new RegExp(format, 'i')];

  const outputPatterns = {
    titles: [/titles only/i],
    citations: [/citations only/i],
    abstracts: [/citations and abstracts/i],
    index: [/abstract and index terms/i],
    full: [/full record/i],
    custom: [/specify.*fields/i]
  }[output.toLowerCase()] || [new RegExp(output, 'i')];

  const formatChosen = await chooseByText(formatPatterns);
  const outputChosen = await chooseByText(outputPatterns);

  if (includeQuery) {
    await chooseByText([/include search query/i]);
  }

  const submit = allControls().find(el =>
    /^export$/i.test(textOf(el)) ||
    /download|start export|create export/i.test(textOf(el))
  );

  if (!submit) {
    return {
      status: 'export_submit_not_found',
      format,
      output,
      formatChosen,
      outputChosen,
      controls: allControls().map(textOf).filter(Boolean).slice(0, 100)
    };
  }

  await click(submit);

  for (let attempt = 0; attempt < 60; attempt++) {
    await sleep(1000);
    const controls = allControls();
    const download = controls.find(el => /download/i.test(textOf(el)));
    if (download) {
      await click(download);
      return {
        status: 'download_clicked',
        format,
        output,
        includeQuery,
        url: location.href
      };
    }
    if (/progress|preparing|exporting|please wait/i.test(clean(document.body.innerText))) continue;
  }

  return {
    status: 'submitted',
    format,
    output,
    includeQuery,
    url: location.href,
    message: 'Export was submitted. If Embase opened a progress tab, click Download there when ready.'
  };
}
```

## Zotero Push

If the downloaded RIS file path is known and Zotero Connector is running locally:

```bash
python skills/embase-export/scripts/push_to_zotero.py path/to/export.ris
```

The script uses deterministic item keys from DOI, PMID, accession/PUI/LUI, or title to reduce duplicate imports.

## Reporting

After export, report:

- Format and output depth.
- Range selected.
- Whether search query was included.
- Any Embase limit or anonymous-session warning.
- Whether Zotero push was attempted and its result.
