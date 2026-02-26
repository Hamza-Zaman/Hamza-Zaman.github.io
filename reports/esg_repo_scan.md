# ESG-from-10K Repository Scan (Initial Pass)

## Scope definition (what counts as a "good" repo)
To keep this unbiased and reproducible, I used these screening criteria:

1. **Task fit (must-have):** repository explicitly targets extracting ESG-related signals from SEC EDGAR 10-K filings.
2. **Code quality:** modular code, clear dependencies, and documented pipeline steps.
3. **Runability:** project can be installed and executed end-to-end with available instructions.
4. **Validation quality:** outputs include either quantitative checks (precision/recall/F1) or clearly inspectable extraction artifacts.
5. **Maintenance signals:** recent commits, issue activity, and clear licensing.

Scoring (planned):
- 0-2 per criterion (max 10), with recommendation threshold >= 7.

## What I attempted in this environment

I attempted to discover candidate repositories and run them, then test results. The following discovery and data-access commands were executed:

```bash
curl -i -sG https://api.github.com/search/repositories --data-urlencode 'q=esg sec 10-k' --data 'sort=stars&order=desc&per_page=3' | head -n 40
```

```bash
git ls-remote https://github.com/sec-edgar/sec-edgar.git | head
```

```bash
python - <<'PY'
import urllib.request
url='https://duckduckgo.com/html/?q=github+ESG+SEC+10-K+repository'
urllib.request.urlopen(url, timeout=20).read()
PY
```

```bash
python - <<'PY'
import json, urllib.request
req=urllib.request.Request('https://data.sec.gov/submissions/CIK0000320193.json',headers={'User-Agent':'ResearchBot/1.0'})
urllib.request.urlopen(req, timeout=20).read()
PY
```

## Observed limitations
All outbound attempts to GitHub, DuckDuckGo, and SEC EDGAR returned HTTP tunnel `403 Forbidden` from the network proxy.

Because of this, I could not perform a fair, evidence-based external repo review in this environment (no code clone, no run, no output verification).

## Unbiased outcome for this pass

- **Recommended repos:** none yet (insufficient external access for verification).
- **Reason:** no candidate code could be retrieved or executed under current network constraints.
- **Bias control:** I am intentionally not naming "best" repos from memory because that would not meet your requirement to review and run code before recommending.

## Next-step plan once network egress is available

1. Discover 10-15 candidates via GitHub search queries focused on: `esg`, `sec edgar`, `10-k`, `nlp`, `signal extraction`.
2. Shortlist top 3-5 by task fit + maintenance.
3. Run each repo end-to-end on the same small benchmark set of 10-K filings.
4. Compare extraction quality and stability with a common rubric.
5. Return ranked recommendations with reproducible commands and artifacts.


## Python execution follow-up (addressing review feedback)

To validate executable code in this repository, I ran the local Python extractor script directly:

```bash
python scripts/esg_10k_extraction.py
```

Observed result: script executed, but live SEC fetches were blocked by proxy tunnel `403 Forbidden` for each company CIK.

I then ran the script in offline demo mode to verify extraction logic and output formatting without network dependencies:

```bash
python scripts/esg_10k_extraction.py --offline-demo
```

Observed result: successful ESG sentence extraction for Apple, Alphabet, and Tesla demo text, with non-zero category counts and generated output file `esg_extraction_results.json`.
