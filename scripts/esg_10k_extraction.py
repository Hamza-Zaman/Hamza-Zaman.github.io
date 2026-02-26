"""
ESG 10-K Report Extraction from SEC EDGAR
==========================================
Extract Environmental, Social, and Governance (ESG) disclosures
from 10-K filings for Apple, Google (Alphabet), and Tesla.

Author: Hamza Zaman
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from html import unescape
from typing import Dict, List
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

# SEC EDGAR requires a User-Agent header
HEADERS = {
    'User-Agent': 'Hamza Zaman hamzazaman04@gmail.com',
    'Accept-Encoding': 'gzip, deflate',
}

# Company CIKs (Central Index Key)
COMPANIES = {
    'Apple': '0000320193',
    'Alphabet (Google)': '0001652044',
    'Tesla': '0001318605'
}

# ESG-related keywords to search for
ESG_KEYWORDS = {
    'Environmental': [
        'climate change', 'carbon emissions', 'greenhouse gas', 'renewable energy',
        'environmental impact', 'sustainability', 'carbon footprint', 'net zero',
        'clean energy', 'environmental matters', 'climate risk', 'emissions reduction'
    ],
    'Social': [
        'human capital', 'employee', 'workforce', 'diversity', 'inclusion',
        'health and safety', 'labor practices', 'community', 'human rights',
        'employee benefits', 'talent', 'workplace'
    ],
    'Governance': [
        'board of directors', 'corporate governance', 'ethics', 'compliance',
        'risk management', 'audit committee', 'executive compensation',
        'shareholder rights', 'anti-corruption', 'code of conduct'
    ]
}

OFFLINE_DEMO_TEXT = {
    'Apple': (
        "Our environmental impact strategy includes climate change resilience and emissions reduction. "
        "We continue investing in renewable energy and carbon footprint transparency. "
        "Our workforce and human capital programs prioritize diversity, inclusion, and employee benefits. "
        "The board of directors oversees risk management, corporate governance, and ethics compliance."
    ),
    'Alphabet (Google)': (
        "Sustainability and clean energy investments support our long-term environmental matters strategy. "
        "Human rights and health and safety standards are reinforced through workplace training. "
        "The audit committee reviews executive compensation and code of conduct controls."
    ),
    'Tesla': (
        "We monitor climate risk and greenhouse gas factors while scaling renewable energy products. "
        "Talent development and community engagement are central to our social strategy. "
        "Shareholder rights and anti-corruption expectations are part of governance oversight."
    )
}


def fetch_json(url: str) -> Dict:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode('utf-8'))


def fetch_text(url: str) -> str:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=20) as response:
        return response.read().decode('utf-8', errors='ignore')


def get_company_filings(cik: str, filing_type: str = '10-K', count: int = 5) -> List[Dict]:
    """Fetch recent filings for a company from SEC EDGAR."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    try:
        data = fetch_json(url)
    except (URLError, HTTPError, TimeoutError, ValueError) as exc:
        print(f"Error fetching data for CIK {cik}: {exc}")
        return []

    filings = data.get('filings', {}).get('recent', {})

    results = []
    forms = filings.get('form', [])
    accessions = filings.get('accessionNumber', [])
    dates = filings.get('filingDate', [])
    docs = filings.get('primaryDocument', [])

    for i, form in enumerate(forms):
        if form == filing_type and len(results) < count:
            results.append({
                'form': form,
                'accession': accessions[i].replace('-', ''),
                'date': dates[i],
                'document': docs[i],
                'cik': cik
            })

    return results


def get_filing_content(cik: str, accession: str, document: str) -> str | None:
    """Download and parse the 10-K filing content."""
    url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{document}"

    try:
        return fetch_text(url)
    except (URLError, HTTPError, TimeoutError) as exc:
        print(f"Error fetching filing: {exc}")
        return None


def html_to_text(html_content: str) -> str:
    text = re.sub(r'<script.*?>.*?</script>', ' ', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style.*?>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_esg_sections(text_content: str) -> Dict[str, List[str]]:
    """Extract ESG-related content from filing text."""
    text = html_to_text(text_content)

    results = {'Environmental': [], 'Social': [], 'Governance': []}

    for category, keywords in ESG_KEYWORDS.items():
        for keyword in keywords:
            pattern = r'[^.]*\b' + re.escape(keyword) + r'\b[^.]*\.'
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:3]:
                cleaned = match.strip()
                if 50 < len(cleaned) < 500 and cleaned not in results[category]:
                    results[category].append(cleaned)

    return results


def analyze_esg_disclosure(esg_data: Dict[str, List[str]]) -> Dict:
    metrics = {}
    for category in ['Environmental', 'Social', 'Governance']:
        items = esg_data.get(category, [])
        metrics[category] = {
            'disclosure_count': len(items),
            'avg_length': round(sum(len(s) for s in items) / len(items), 2) if items else 0,
            'sample': items[0][:200] + '...' if items else 'No disclosure found'
        }
    return metrics


def print_summary(all_results: Dict) -> None:
    print("\n" + "=" * 70)
    print("ESG DISCLOSURE SUMMARY COMPARISON")
    print("=" * 70)
    headers = ["Company", "Filing Date", "Environmental", "Social", "Governance", "Total ESG"]
    print(" | ".join(headers))
    print("-" * 70)
    for company, data in all_results.items():
        env = data['metrics']['Environmental']['disclosure_count']
        soc = data['metrics']['Social']['disclosure_count']
        gov = data['metrics']['Governance']['disclosure_count']
        total = env + soc + gov
        print(f"{company} | {data['filing_date']} | {env} | {soc} | {gov} | {total}")


def main(use_offline_demo: bool = False) -> Dict:
    print("=" * 70)
    print("ESG 10-K REPORT EXTRACTION FROM SEC EDGAR")
    mode = "OFFLINE DEMO MODE" if use_offline_demo else "LIVE SEC MODE"
    print(f"Mode: {mode}")
    print(f"Extraction Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("Companies: Apple, Alphabet (Google), Tesla")
    print("=" * 70)

    all_results = {}

    for company, cik in COMPANIES.items():
        print(f"\n{'=' * 50}")
        print(f"Processing: {company} (CIK: {cik})")
        print('=' * 50)

        if use_offline_demo:
            content = OFFLINE_DEMO_TEXT[company]
            filing_date = 'offline-demo'
        else:
            filings = get_company_filings(cik, '10-K', count=1)
            if not filings:
                print(f"No 10-K filings found for {company}")
                continue
            filing = filings[0]
            filing_date = filing['date']
            print(f"Filing Date: {filing['date']}")
            print(f"Accession: {filing['accession']}")
            time.sleep(0.5)
            print("Downloading 10-K filing...")
            content = get_filing_content(cik, filing['accession'], filing['document'])
            if not content:
                print(f"Could not download filing for {company}")
                continue
            print(f"Filing size: {len(content):,} characters")

        print("Extracting ESG disclosures...")
        esg_data = extract_esg_sections(content)
        metrics = analyze_esg_disclosure(esg_data)

        all_results[company] = {
            'filing_date': filing_date,
            'esg_data': esg_data,
            'metrics': metrics,
        }

        for category in ['Environmental', 'Social', 'Governance']:
            print(f"\n--- {category} ---")
            print(f"Disclosures found: {metrics[category]['disclosure_count']}")
            if esg_data[category]:
                print(f"Sample: {esg_data[category][0][:220]}...")

        time.sleep(0.2)

    print_summary(all_results)

    output = {'extraction_date': datetime.now().isoformat(), 'mode': mode, 'companies': all_results}
    with open('esg_extraction_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    print("\nResults saved to esg_extraction_results.json")

    return all_results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract ESG disclosures from 10-K filings.')
    parser.add_argument('--offline-demo', action='store_true', help='Run extraction on bundled sample text.')
    args = parser.parse_args()
    main(use_offline_demo=args.offline_demo)
