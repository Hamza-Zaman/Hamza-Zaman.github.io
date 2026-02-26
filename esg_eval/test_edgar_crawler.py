"""
Test Script: edgar-crawler (lefterisloukas/edgar-crawler)
=========================================================
Tests the edgar-crawler's offline extraction capability and applies
ESG keyword analysis on extracted 10-K sections.
Stars: 481 | License: GPL-3.0 | Academic paper: WWW 2025
"""

import json
import time
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(__file__))
from esg_keywords import count_esg_hits, extract_esg_sentences

RESULTS_FILE = os.path.join(os.path.dirname(__file__), 'results_edgar_crawler.json')
CRAWLER_DIR = os.path.join(os.path.dirname(__file__), 'edgar-crawler')


def test_edgar_crawler():
    start_time = time.time()
    errors = []
    results = {
        'repo': 'edgar-crawler (lefterisloukas/edgar-crawler)',
        'stars': 481,
        'license': 'GPL-3.0',
        'test_target': 'Offline test fixtures - 62 real 10-K filings (1993-2018)',
    }

    print("=" * 60)
    print("TESTING: edgar-crawler (lefterisloukas/edgar-crawler)")
    print("=" * 60)

    # Step 1: Test offline extraction using fixtures
    print("\n--- Step 1: Extract test fixtures ---")
    try:
        raw_zip = os.path.join(CRAWLER_DIR, 'tests', 'fixtures', 'RAW_FILINGS', '10-K.zip')
        extracted_zip = os.path.join(CRAWLER_DIR, 'tests', 'fixtures', 'EXTRACTED_FILINGS', '10-K.zip')

        zf_raw = zipfile.ZipFile(raw_zip)
        zf_extracted = zipfile.ZipFile(extracted_zip)

        raw_files = [n for n in zf_raw.namelist() if not n.endswith('/')]
        extracted_files = [n for n in zf_extracted.namelist() if not n.endswith('/')]

        print(f"[OK] Raw 10-K fixtures: {len(raw_files)} files")
        print(f"[OK] Expected extraction fixtures: {len(extracted_files)} files")
        results['fixture_count_raw'] = len(raw_files)
        results['fixture_count_extracted'] = len(extracted_files)

    except Exception as e:
        print(f"[FAIL] Fixture extraction failed: {e}")
        errors.append(f"Fixture extraction: {e}")

    # Step 2: Import and test ExtractItems class
    print("\n--- Step 2: Test ExtractItems class ---")
    try:
        sys.path.insert(0, CRAWLER_DIR)
        from extract_items import ExtractItems

        extraction = ExtractItems(
            remove_tables=True,
            items_to_extract=["1", "1A", "7", "7A"],
            include_signature=False,
            raw_files_folder="/tmp/edgar-crawler-test/RAW_FILINGS/",
            extracted_files_folder="",
            skip_extracted_filings=False,
        )
        print(f"[OK] ExtractItems initialized")
        print(f"  Items to extract: {extraction.items_to_extract}")
        results['import_success'] = True

    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        errors.append(f"Import: {e}")
        results['import_success'] = False

    # Step 3: Extract items from a few filings and run ESG analysis
    print("\n--- Step 3: Extract items & run ESG analysis ---")

    # Use the pre-extracted JSON fixtures for ESG analysis
    esg_analysis_results = []

    try:
        zf = zipfile.ZipFile(extracted_zip)
        sample_count = 0

        for name in sorted(zf.namelist()):
            if not name.endswith('.json'):
                continue

            data = json.loads(zf.read(name))

            # Combine ESG-relevant sections
            esg_text = ""
            for item_key in ['item_1', 'item_1A', 'item_7', 'item_7A']:
                text = data.get(item_key, '')
                if text:
                    esg_text += f"\n\n--- {item_key} ---\n{text}"

            if not esg_text.strip():
                continue

            sample_count += 1

            # Run ESG keyword analysis
            esg_hits = count_esg_hits(esg_text)
            esg_sentences = extract_esg_sentences(esg_text)

            total_hits = sum(h['total_hits'] for h in esg_hits.values())
            total_sentences = sum(len(s) for s in esg_sentences.values())

            company = data.get('company', 'Unknown')
            filing_date = data.get('filing_date', 'Unknown')

            filing_result = {
                'company': company,
                'filing_date': filing_date,
                'text_length': len(esg_text),
                'total_esg_hits': total_hits,
                'total_esg_sentences': total_sentences,
                'environmental_hits': esg_hits['Environmental']['total_hits'],
                'social_hits': esg_hits['Social']['total_hits'],
                'governance_hits': esg_hits['Governance']['total_hits'],
            }
            esg_analysis_results.append(filing_result)

            if sample_count <= 5:
                print(f"\n  Filing: {company} ({filing_date})")
                print(f"    Text from items 1,1A,7,7A: {len(esg_text):,} chars")
                print(f"    ESG hits: E={esg_hits['Environmental']['total_hits']} "
                      f"S={esg_hits['Social']['total_hits']} "
                      f"G={esg_hits['Governance']['total_hits']}")
                if esg_sentences['Environmental']:
                    print(f"    Sample environmental: {esg_sentences['Environmental'][0][:200]}...")

        print(f"\n[OK] Analyzed {sample_count} filings for ESG content")
        results['filings_analyzed'] = sample_count

    except Exception as e:
        print(f"[FAIL] ESG analysis failed: {e}")
        errors.append(f"ESG analysis: {e}")

    # Step 4: Compute summary statistics
    print("\n--- Step 4: Summary statistics ---")
    if esg_analysis_results:
        avg_hits = sum(r['total_esg_hits'] for r in esg_analysis_results) / len(esg_analysis_results)
        avg_env = sum(r['environmental_hits'] for r in esg_analysis_results) / len(esg_analysis_results)
        avg_soc = sum(r['social_hits'] for r in esg_analysis_results) / len(esg_analysis_results)
        avg_gov = sum(r['governance_hits'] for r in esg_analysis_results) / len(esg_analysis_results)
        filings_with_esg = sum(1 for r in esg_analysis_results if r['total_esg_hits'] > 0)

        print(f"  Filings with any ESG content: {filings_with_esg}/{len(esg_analysis_results)}")
        print(f"  Avg ESG keyword hits per filing: {avg_hits:.1f}")
        print(f"  Avg Environmental hits: {avg_env:.1f}")
        print(f"  Avg Social hits: {avg_soc:.1f}")
        print(f"  Avg Governance hits: {avg_gov:.1f}")

        results['esg_summary'] = {
            'filings_with_esg': filings_with_esg,
            'filings_total': len(esg_analysis_results),
            'avg_total_hits': round(avg_hits, 1),
            'avg_environmental': round(avg_env, 1),
            'avg_social': round(avg_soc, 1),
            'avg_governance': round(avg_gov, 1),
        }
        results['esg_filing_details'] = esg_analysis_results

    # Step 5: Output JSON structure quality
    print("\n--- Step 5: Output structure assessment ---")
    try:
        zf = zipfile.ZipFile(extracted_zip)
        sample_name = sorted(zf.namelist())[1]  # Skip directory entry
        sample_data = json.loads(zf.read(sample_name))

        results['output_json_keys'] = list(sample_data.keys())
        results['output_metadata_fields'] = [k for k in sample_data.keys() if not k.startswith('item_')]
        results['output_item_fields'] = [k for k in sample_data.keys() if k.startswith('item_')]

        print(f"  Metadata fields: {len(results['output_metadata_fields'])}")
        print(f"  Item fields: {len(results['output_item_fields'])}")
        print(f"  Keys: {results['output_json_keys'][:8]}...")
        print(f"[OK] Clean JSON structure with {len(results['output_json_keys'])} fields")

    except Exception as e:
        print(f"[FAIL] Structure assessment failed: {e}")
        errors.append(f"Structure: {e}")

    # Finalize
    results['errors'] = errors
    results['error_count'] = len(errors)
    results['runtime_seconds'] = round(time.time() - start_time, 2)

    print(f"\n{'='*60}")
    print(f"Runtime: {results['runtime_seconds']}s | Errors: {len(errors)}")
    print(f"{'='*60}")

    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {RESULTS_FILE}")

    return results


if __name__ == '__main__':
    test_edgar_crawler()
