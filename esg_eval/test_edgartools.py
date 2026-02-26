"""
Test Script: edgartools (dgunning/edgartools)
=============================================
Tests the edgartools library for ESG signal extraction from Apple's 10-K.
Stars: 1,700 | License: MIT | pip install edgartools
"""

import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from esg_keywords import count_esg_hits, extract_esg_sentences

RESULTS_FILE = os.path.join(os.path.dirname(__file__), 'results_edgartools.json')


def test_edgartools():
    start_time = time.time()
    errors = []
    results = {
        'repo': 'edgartools (dgunning/edgartools)',
        'stars': 1700,
        'license': 'MIT',
        'test_target': 'Apple Inc. (AAPL) - Most recent 10-K',
    }

    # Step 1: Setup
    print("=" * 60)
    print("TESTING: edgartools (dgunning/edgartools)")
    print("=" * 60)

    try:
        from edgar import Company, set_identity
        print("[OK] Import successful")
        results['import_success'] = True
    except ImportError as e:
        print(f"[FAIL] Import failed: {e}")
        results['import_success'] = False
        errors.append(f"Import failed: {e}")
        results['errors'] = errors
        results['runtime_seconds'] = time.time() - start_time
        with open(RESULTS_FILE, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        return results

    # Step 2: Set identity (SEC requirement)
    try:
        set_identity("ESG Evaluation Test eval@test.com")
        print("[OK] Identity set for SEC compliance")
    except Exception as e:
        print(f"[WARN] Identity set issue: {e}")
        errors.append(f"Identity issue: {e}")

    # Step 3: Get Apple company and filings
    try:
        print("\nFetching Apple company data...")
        company = Company("AAPL")
        print(f"[OK] Company: {company.name}")
        results['company_name'] = str(company.name)

        print("Fetching 10-K filings...")
        filings = company.get_filings(form="10-K")
        latest_10k = filings[0]
        print(f"[OK] Latest 10-K: {latest_10k.filing_date}")
        results['filing_date'] = str(latest_10k.filing_date)
        results['accession_number'] = str(latest_10k.accession_no)

    except Exception as e:
        print(f"[FAIL] Could not fetch filings: {e}")
        errors.append(f"Filings fetch failed: {e}")
        results['errors'] = errors
        results['runtime_seconds'] = time.time() - start_time
        with open(RESULTS_FILE, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        return results

    # Step 4: Get the filing document and extract text
    try:
        print("\nDownloading filing document...")
        time.sleep(0.5)  # Rate limit
        filing_obj = latest_10k.obj()
        print(f"[OK] Filing object type: {type(filing_obj).__name__}")

        # Try to extract text from the filing
        full_text = ""
        sections_extracted = {}

        # Try to get specific items/sections
        try:
            # edgartools TenK object has items
            for item_name in ['item1', 'item1a', 'item1A', 'item7', 'Item1', 'Item1A', 'Item7']:
                try:
                    section = getattr(filing_obj, item_name, None)
                    if section:
                        section_text = str(section)
                        if len(section_text) > 100:
                            sections_extracted[item_name] = section_text
                            full_text += f"\n\n--- {item_name} ---\n" + section_text
                            print(f"  [OK] Extracted {item_name}: {len(section_text):,} chars")
                except Exception:
                    pass
        except Exception as e:
            print(f"  [WARN] Section extraction issue: {e}")

        # Fallback: try to get full text
        if not full_text:
            try:
                full_text = str(filing_obj)
                print(f"  [OK] Full text (str conversion): {len(full_text):,} chars")
            except Exception:
                pass

        if not full_text:
            try:
                # Try html or text method
                for method in ['text', 'html', 'markdown']:
                    m = getattr(filing_obj, method, None)
                    if callable(m):
                        full_text = m()
                        if full_text and len(full_text) > 100:
                            print(f"  [OK] Text via .{method}(): {len(full_text):,} chars")
                            break
            except Exception:
                pass

        results['text_extracted_chars'] = len(full_text)
        results['sections_extracted'] = list(sections_extracted.keys())
        print(f"\nTotal text extracted: {len(full_text):,} characters")

    except Exception as e:
        print(f"[FAIL] Filing download/extraction failed: {e}")
        errors.append(f"Filing extraction failed: {e}")
        full_text = ""

    # Step 5: ESG keyword analysis
    if full_text:
        print("\n--- ESG Keyword Analysis ---")
        esg_hits = count_esg_hits(full_text)
        esg_sentences = extract_esg_sentences(full_text)

        for category in ['Environmental', 'Social', 'Governance']:
            hits = esg_hits[category]
            sents = esg_sentences[category]
            print(f"\n{category}:")
            print(f"  Total keyword hits: {hits['total_hits']}")
            print(f"  Unique keywords matched: {hits['unique_keywords_matched']}")
            if sents:
                print(f"  Sample sentence: {sents[0][:200]}...")
            else:
                print(f"  No sentences extracted")

        results['esg_hits'] = esg_hits
        results['esg_sentences_count'] = {
            cat: len(sents) for cat, sents in esg_sentences.items()
        }
        results['esg_sample_sentences'] = {
            cat: sents[:2] for cat, sents in esg_sentences.items()
        }
    else:
        print("\n[FAIL] No text available for ESG analysis")
        errors.append("No text extracted from filing")

    # Finalize
    results['errors'] = errors
    results['runtime_seconds'] = round(time.time() - start_time, 2)
    results['error_count'] = len(errors)

    print(f"\n{'='*60}")
    print(f"Runtime: {results['runtime_seconds']}s | Errors: {len(errors)}")
    print(f"{'='*60}")

    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {RESULTS_FILE}")

    return results


if __name__ == '__main__':
    test_edgartools()
