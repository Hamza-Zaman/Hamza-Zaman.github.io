"""
ESG 10-K Report Extraction from SEC EDGAR
==========================================
Extract Environmental, Social, and Governance (ESG) disclosures
from 10-K filings for Apple, Google (Alphabet), and Tesla.

Author: Hamza Zaman
"""

import requests
import re
import json
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import warnings
warnings.filterwarnings('ignore')

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


def get_company_filings(cik, filing_type='10-K', count=5):
    """Fetch recent filings for a company from SEC EDGAR."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Error fetching data for CIK {cik}: {response.status_code}")
        return []

    data = response.json()
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


def get_filing_content(cik, accession, document):
    """Download and parse the 10-K filing content."""
    url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{document}"

    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Error fetching filing: {response.status_code}")
        return None

    return response.text


def extract_esg_sections(html_content, company_name):
    """Extract ESG-related content from 10-K filing."""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Get text content
    text = soup.get_text(separator=' ', strip=True)

    # Clean up text
    text = re.sub(r'\s+', ' ', text)

    results = {
        'Environmental': [],
        'Social': [],
        'Governance': []
    }

    # Search for ESG content
    for category, keywords in ESG_KEYWORDS.items():
        for keyword in keywords:
            # Find sentences containing the keyword
            pattern = r'[^.]*\b' + re.escape(keyword) + r'\b[^.]*\.'
            matches = re.findall(pattern, text, re.IGNORECASE)

            for match in matches[:3]:  # Limit to 3 matches per keyword
                cleaned = match.strip()
                if len(cleaned) > 50 and len(cleaned) < 500:  # Filter by length
                    if cleaned not in results[category]:
                        results[category].append(cleaned)

    return results


def analyze_esg_disclosure(esg_data):
    """Analyze ESG disclosure metrics."""
    metrics = {}

    for category in ['Environmental', 'Social', 'Governance']:
        items = esg_data.get(category, [])
        metrics[category] = {
            'disclosure_count': len(items),
            'avg_length': sum(len(s) for s in items) / len(items) if items else 0,
            'sample': items[0][:200] + '...' if items else 'No disclosure found'
        }

    return metrics


def main():
    """Main execution function."""
    print("=" * 70)
    print("ESG 10-K REPORT EXTRACTION FROM SEC EDGAR")
    print("=" * 70)
    print(f"Extraction Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("Companies: Apple, Alphabet (Google), Tesla")
    print("=" * 70)

    all_results = {}

    for company, cik in COMPANIES.items():
        print(f"\n{'='*50}")
        print(f"Processing: {company} (CIK: {cik})")
        print('='*50)

        # Get most recent 10-K filing
        filings = get_company_filings(cik, '10-K', count=1)

        if not filings:
            print(f"No 10-K filings found for {company}")
            continue

        filing = filings[0]
        print(f"Filing Date: {filing['date']}")
        print(f"Accession: {filing['accession']}")

        # Add delay to respect SEC rate limits
        time.sleep(0.5)

        # Get filing content
        print("Downloading 10-K filing...")
        content = get_filing_content(cik, filing['accession'], filing['document'])

        if not content:
            print(f"Could not download filing for {company}")
            continue

        print(f"Filing size: {len(content):,} characters")

        # Extract ESG content
        print("Extracting ESG disclosures...")
        esg_data = extract_esg_sections(content, company)

        # Analyze metrics
        metrics = analyze_esg_disclosure(esg_data)

        all_results[company] = {
            'filing_date': filing['date'],
            'esg_data': esg_data,
            'metrics': metrics
        }

        # Print results
        for category in ['Environmental', 'Social', 'Governance']:
            print(f"\n--- {category} ---")
            print(f"Disclosures found: {metrics[category]['disclosure_count']}")
            if esg_data[category]:
                print(f"Sample: {esg_data[category][0][:300]}...")

        time.sleep(1)  # Rate limiting

    # Summary comparison
    print("\n" + "=" * 70)
    print("ESG DISCLOSURE SUMMARY COMPARISON")
    print("=" * 70)

    summary_data = []
    for company, data in all_results.items():
        row = {
            'Company': company,
            'Filing Date': data['filing_date'],
            'Environmental': data['metrics']['Environmental']['disclosure_count'],
            'Social': data['metrics']['Social']['disclosure_count'],
            'Governance': data['metrics']['Governance']['disclosure_count'],
        }
        row['Total ESG'] = row['Environmental'] + row['Social'] + row['Governance']
        summary_data.append(row)

    df = pd.DataFrame(summary_data)
    print(df.to_string(index=False))

    # Save results
    output = {
        'extraction_date': datetime.now().isoformat(),
        'companies': all_results
    }

    with open('esg_extraction_results.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print("\nResults saved to esg_extraction_results.json")

    return all_results


if __name__ == '__main__':
    results = main()
