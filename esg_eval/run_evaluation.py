"""
ESG Extraction Evaluation — Comparison Report Generator
========================================================
Loads results from all 5 repo evaluations and generates a comparison report.
"""

import json
import os

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))

SCORES = {
    'edgar-crawler': {
        'Setup & Install': 4,
        'Code Quality': 4,
        'ESG Signal Quality': 3,
        'Output Structure': 5,
        'SEC Compliance': 4,
        'Maintainability': 4,
    },
    'edgartools': {
        'Setup & Install': 5,
        'Code Quality': 5,
        'ESG Signal Quality': 3,
        'Output Structure': 5,
        'SEC Compliance': 5,
        'Maintainability': 5,
    },
    'ESG-BERT': {
        'Setup & Install': 2,
        'Code Quality': 1,
        'ESG Signal Quality': 5,
        'Output Structure': 3,
        'SEC Compliance': 0,  # N/A
        'Maintainability': 1,
    },
    '10-K Sentiment': {
        'Setup & Install': 3,
        'Code Quality': 2,
        'ESG Signal Quality': 2,
        'Output Structure': 2,
        'SEC Compliance': 1,
        'Maintainability': 1,
    },
    'py-sec-edgar': {
        'Setup & Install': 2,
        'Code Quality': 4,
        'ESG Signal Quality': 1,
        'Output Structure': 4,
        'SEC Compliance': 4,
        'Maintainability': 4,
    },
}


def load_results():
    """Load all JSON result files."""
    results = {}
    for fname in os.listdir(EVAL_DIR):
        if fname.startswith('results_') and fname.endswith('.json'):
            with open(os.path.join(EVAL_DIR, fname)) as f:
                data = json.load(f)
            key = fname.replace('results_', '').replace('.json', '')
            results[key] = data
    return results


def print_comparison():
    """Print the comparison report."""
    results = load_results()

    print("=" * 80)
    print("ESG EXTRACTION FROM SEC EDGAR 10-K — EVALUATION REPORT")
    print("=" * 80)

    # Scoring matrix
    print("\n## SCORING MATRIX (1-5, higher is better)")
    print("-" * 80)

    header = f"{'Criteria':<22}"
    for repo in SCORES:
        header += f" {repo:>14}"
    print(header)
    print("-" * 80)

    criteria = ['Setup & Install', 'Code Quality', 'ESG Signal Quality',
                'Output Structure', 'SEC Compliance', 'Maintainability']

    for criterion in criteria:
        row = f"{criterion:<22}"
        for repo in SCORES:
            score = SCORES[repo][criterion]
            if score == 0:
                row += f" {'N/A':>14}"
            else:
                row += f" {score:>14}"
        print(row)

    print("-" * 80)
    row = f"{'TOTAL':<22}"
    for repo in SCORES:
        total = sum(v for v in SCORES[repo].values() if v > 0)
        max_possible = sum(5 for v in SCORES[repo].values() if v > 0)
        row += f" {f'{total}/{max_possible}':>14}"
    print(row)

    # Key findings per repo
    print("\n" + "=" * 80)
    print("## KEY FINDINGS PER REPO")
    print("=" * 80)

    for key, data in results.items():
        print(f"\n### {data.get('repo', key)}")
        print(f"  Stars: {data.get('stars', '?')}")
        print(f"  License: {data.get('license', '?')}")

        if 'esg_summary' in data:
            esg = data['esg_summary']
            print(f"  ESG Analysis: {esg.get('filings_with_esg', '?')}/{esg.get('filings_total', '?')} filings had ESG content")
            print(f"  Avg hits: E={esg.get('avg_environmental', '?')} S={esg.get('avg_social', '?')} G={esg.get('avg_governance', '?')}")

        if 'assessment' in data:
            for k, v in data['assessment'].items():
                print(f"  {k}: {v}")

    # Recommendation
    print("\n" + "=" * 80)
    print("## RECOMMENDATION")
    print("=" * 80)
    print("""
BEST OVERALL: edgartools (1,700 stars, MIT, 332 files, 140K LOC)
  - Most complete SEC EDGAR library
  - Best code quality and test coverage
  - pip installable, active development

BEST FOR RESEARCH: edgar-crawler (481 stars, GPL-3.0, published WWW 2025)
  - Academic-grade structured extraction
  - Offline test data included
  - Clean JSON output per section

BEST PIPELINE: edgartools (access) + ESG-BERT (classification)
  - Use edgartools to fetch 10-K and extract sections
  - Apply ESG-BERT for 26-category classification
  - Alternatively, use LLM-based extraction for richer context
""")

    print("=" * 80)
    print("Full details: scripts/esg_evaluation_summary.md")
    print("=" * 80)


if __name__ == '__main__':
    print_comparison()
