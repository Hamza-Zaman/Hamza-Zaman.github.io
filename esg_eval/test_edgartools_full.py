#!/usr/bin/env python3
"""
Comprehensive edgartools Evaluation Script
===========================================
Tests the edgartools library against REAL SEC EDGAR data across multiple
companies and years to evaluate its reliability for ESG signal extraction.

Companies: AAPL, MSFT, TSLA, JPM, XOM
Years:     2015, 2017, 2019, 2021, 2023, 2025, 2026

For each company+year combination, the script attempts to:
  1. Fetch the 10-K filing for that fiscal year
  2. Parse it into a TenK object
  3. Extract financial statements (income statement, balance sheet, cash flow)
  4. Extract filing text and count ESG keywords
  5. Time each operation

Output: Structured JSON results with pass/fail, timing, and details.
"""

import json
import os
import sys
import time
import traceback
import signal
from datetime import datetime
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# Ensure we can import the shared ESG keyword module from the same directory
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from esg_keywords import ESG_KEYWORDS, count_esg_hits, extract_esg_sentences

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
COMPANIES = ["AAPL", "MSFT", "TSLA", "JPM", "XOM"]
YEARS = [2015, 2017, 2019, 2021, 2023, 2025, 2026]

# Timeout per individual filing fetch/parse (seconds)
OPERATION_TIMEOUT = 120

# Delay between SEC requests to respect rate limits (seconds)
REQUEST_DELAY = 0.25

# Output paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_FILE = os.path.join(SCRIPT_DIR, "results_edgartools_full.json")

# SEC identity (required by SEC EDGAR fair-access policy)
SEC_IDENTITY_NAME = "Hamza Zaman"
SEC_IDENTITY_EMAIL = "hamzazaman04@gmail.com"


# ---------------------------------------------------------------------------
# Timeout helper (POSIX only; degrades gracefully on Windows)
# ---------------------------------------------------------------------------
class OperationTimeout(Exception):
    """Raised when a single operation exceeds its time budget."""
    pass


@contextmanager
def time_limit(seconds, label="operation"):
    """Context manager that raises OperationTimeout after *seconds*."""
    if sys.platform == "win32":
        # signal.SIGALRM is not available on Windows; skip timeout enforcement
        yield
        return

    def _handler(signum, frame):
        raise OperationTimeout(
            f"{label} exceeded {seconds}s timeout"
        )

    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def safe_str(obj):
    """Convert arbitrary objects to string, capped at 500 chars for logging."""
    try:
        s = str(obj)
        return s[:500] if len(s) > 500 else s
    except Exception:
        return "<non-serialisable>"


def extract_financial_statements(filing_obj):
    """
    Attempt to extract financial statements from a TenK (or similar) object.

    Returns a dict mapping statement name -> {found, row_count, sample_labels}.
    """
    statements = {}

    # edgartools exposes financials via the Financials object on TenK
    # Typical access patterns:
    #   filing_obj.financials
    #   filing_obj.financials.income_statement
    #   filing_obj.financials.balance_sheet
    #   filing_obj.financials.cash_flow_statement
    financials = None
    try:
        financials = getattr(filing_obj, "financials", None)
    except Exception:
        pass

    statement_map = {
        "income_statement": [
            "income_statement",
            "income",
            "consolidated_statements_of_operations",
        ],
        "balance_sheet": [
            "balance_sheet",
            "consolidated_balance_sheets",
        ],
        "cash_flow_statement": [
            "cash_flow_statement",
            "cash_flow",
            "consolidated_statements_of_cash_flows",
        ],
    }

    for canonical_name, attr_candidates in statement_map.items():
        info = {"found": False, "row_count": 0, "sample_labels": []}

        # First try via the financials object
        if financials is not None:
            for attr in attr_candidates:
                try:
                    stmt = getattr(financials, attr, None)
                    if stmt is not None:
                        info["found"] = True
                        # Try to get a DataFrame or list of rows
                        df = None
                        if hasattr(stmt, "to_dataframe"):
                            df = stmt.to_dataframe()
                        elif hasattr(stmt, "get_dataframe"):
                            df = stmt.get_dataframe()
                        elif hasattr(stmt, "data"):
                            df = stmt.data

                        if df is not None and hasattr(df, "shape"):
                            info["row_count"] = int(df.shape[0])
                            if hasattr(df, "index"):
                                info["sample_labels"] = [
                                    str(lbl) for lbl in list(df.index)[:5]
                                ]
                            elif hasattr(df, "columns"):
                                info["sample_labels"] = [
                                    str(c) for c in list(df.columns)[:5]
                                ]
                        else:
                            # Fallback: convert to string and count lines
                            text_repr = str(stmt)
                            lines = [
                                l.strip()
                                for l in text_repr.split("\n")
                                if l.strip()
                            ]
                            info["row_count"] = len(lines)
                            info["sample_labels"] = lines[:5]
                        break  # found it, no need to try other attr names
                except Exception:
                    continue

        # Fallback: try directly on the filing object
        if not info["found"]:
            for attr in attr_candidates:
                try:
                    stmt = getattr(filing_obj, attr, None)
                    if stmt is not None:
                        info["found"] = True
                        text_repr = str(stmt)
                        lines = [
                            l.strip()
                            for l in text_repr.split("\n")
                            if l.strip()
                        ]
                        info["row_count"] = len(lines)
                        info["sample_labels"] = lines[:5]
                        break
                except Exception:
                    continue

        statements[canonical_name] = info

    return statements


def extract_filing_text(filing_obj):
    """
    Extract as much textual content as possible from a filing object.
    Returns (text: str, method: str) describing how the text was obtained.
    """
    text = ""
    method = "none"

    # Strategy 1: concatenate known 10-K item sections
    section_attrs = [
        "item1", "item1a", "item1A", "Item1", "Item1A",
        "item2", "item3", "item4",
        "item5", "item6", "item7", "item7a", "item7A",
        "Item7", "Item7A",
        "item8", "item9", "item9a", "item9A",
        "item10", "item11", "item12", "item13", "item14", "item15",
    ]
    sections_found = []
    for attr in section_attrs:
        try:
            val = getattr(filing_obj, attr, None)
            if val is not None:
                val_text = str(val)
                if len(val_text) > 100:
                    text += f"\n\n--- {attr} ---\n{val_text}"
                    sections_found.append(attr)
        except Exception:
            continue

    if text and len(text) > 500:
        method = f"sections({','.join(sections_found)})"
        return text, method

    # Strategy 2: full string conversion
    try:
        text = str(filing_obj)
        if len(text) > 500:
            method = "str()"
            return text, method
    except Exception:
        pass

    # Strategy 3: .text() / .html() / .markdown() methods
    for mname in ["text", "html", "markdown"]:
        try:
            m = getattr(filing_obj, mname, None)
            if callable(m):
                text = m()
                if text and len(text) > 500:
                    method = f".{mname}()"
                    return text, method
        except Exception:
            continue

    return text, method


# ---------------------------------------------------------------------------
# Core test for a single company+year
# ---------------------------------------------------------------------------
def test_single_filing(company_obj, ticker, year, Company):
    """
    Test fetching and parsing a 10-K for *ticker* filed in *year*.

    Returns a result dict with pass/fail, timing, and extracted data.
    """
    result = {
        "ticker": ticker,
        "year": year,
        "passed": False,
        "steps": {},
        "errors": [],
        "timings_seconds": {},
    }

    # ------------------------------------------------------------------
    # Step 1: Fetch 10-K filings list for the given year
    # ------------------------------------------------------------------
    step = "fetch_filings"
    t0 = time.time()
    filings = None
    try:
        # edgartools filtering: form="10-K" and date range for the year
        # The filing_date filter uses YYYY-MM-DD strings.
        date_from = f"{year}-01-01"
        date_to = f"{year}-12-31"

        filings = company_obj.get_filings(form="10-K")

        # Filter to the target year by filing_date
        target_filing = None
        for f in filings:
            try:
                fdate = str(f.filing_date)
                if fdate.startswith(str(year)):
                    target_filing = f
                    break
            except Exception:
                continue

        # If exact year match not found, check if the first filing is close
        # (some 10-Ks for fiscal year X are filed early in year X+1)
        if target_filing is None:
            for f in filings:
                try:
                    fdate = str(f.filing_date)
                    fyear = int(fdate[:4])
                    # Accept filings from year+1 Q1 as belonging to fiscal year
                    if fyear == year + 1 and int(fdate[5:7]) <= 3:
                        target_filing = f
                        break
                    # Also accept filings from the target year itself
                    if fyear == year:
                        target_filing = f
                        break
                except Exception:
                    continue

        elapsed = round(time.time() - t0, 3)
        result["timings_seconds"][step] = elapsed

        if target_filing is None:
            result["steps"][step] = {
                "status": "fail",
                "detail": f"No 10-K found for year {year}",
            }
            result["errors"].append(f"No 10-K filing found for {ticker} in {year}")
            return result

        result["steps"][step] = {
            "status": "pass",
            "filing_date": str(target_filing.filing_date),
            "accession_no": str(target_filing.accession_no),
        }

        time.sleep(REQUEST_DELAY)

    except OperationTimeout:
        result["timings_seconds"][step] = round(time.time() - t0, 3)
        result["steps"][step] = {"status": "timeout"}
        result["errors"].append(f"Timeout fetching filings for {ticker} in {year}")
        return result
    except Exception as e:
        elapsed = round(time.time() - t0, 3)
        result["timings_seconds"][step] = elapsed
        result["steps"][step] = {"status": "error", "detail": str(e)[:300]}
        result["errors"].append(f"fetch_filings: {e}")
        return result

    # ------------------------------------------------------------------
    # Step 2: Parse filing into TenK object
    # ------------------------------------------------------------------
    step = "parse_filing"
    t0 = time.time()
    filing_obj = None
    try:
        with time_limit(OPERATION_TIMEOUT, label=f"parse {ticker}/{year}"):
            filing_obj = target_filing.obj()
        elapsed = round(time.time() - t0, 3)
        result["timings_seconds"][step] = elapsed
        result["steps"][step] = {
            "status": "pass",
            "object_type": type(filing_obj).__name__,
        }
        time.sleep(REQUEST_DELAY)
    except OperationTimeout:
        result["timings_seconds"][step] = round(time.time() - t0, 3)
        result["steps"][step] = {"status": "timeout"}
        result["errors"].append(f"Timeout parsing filing for {ticker} in {year}")
        return result
    except Exception as e:
        elapsed = round(time.time() - t0, 3)
        result["timings_seconds"][step] = elapsed
        result["steps"][step] = {"status": "error", "detail": str(e)[:300]}
        result["errors"].append(f"parse_filing: {e}")
        return result

    # ------------------------------------------------------------------
    # Step 3: Extract financial statements
    # ------------------------------------------------------------------
    step = "financial_statements"
    t0 = time.time()
    try:
        with time_limit(OPERATION_TIMEOUT, label=f"financials {ticker}/{year}"):
            fin_data = extract_financial_statements(filing_obj)
        elapsed = round(time.time() - t0, 3)
        result["timings_seconds"][step] = elapsed

        found_count = sum(1 for v in fin_data.values() if v["found"])
        result["steps"][step] = {
            "status": "pass" if found_count > 0 else "fail",
            "statements_found": found_count,
            "details": fin_data,
        }
        if found_count == 0:
            result["errors"].append(
                f"No financial statements extracted for {ticker} in {year}"
            )
    except OperationTimeout:
        result["timings_seconds"][step] = round(time.time() - t0, 3)
        result["steps"][step] = {"status": "timeout"}
        result["errors"].append(
            f"Timeout extracting financial statements for {ticker} in {year}"
        )
    except Exception as e:
        elapsed = round(time.time() - t0, 3)
        result["timings_seconds"][step] = elapsed
        result["steps"][step] = {"status": "error", "detail": str(e)[:300]}
        result["errors"].append(f"financial_statements: {e}")

    # ------------------------------------------------------------------
    # Step 4: Extract text content
    # ------------------------------------------------------------------
    step = "text_extraction"
    t0 = time.time()
    full_text = ""
    try:
        with time_limit(OPERATION_TIMEOUT, label=f"text {ticker}/{year}"):
            full_text, extraction_method = extract_filing_text(filing_obj)
        elapsed = round(time.time() - t0, 3)
        result["timings_seconds"][step] = elapsed
        result["steps"][step] = {
            "status": "pass" if len(full_text) > 500 else "fail",
            "chars_extracted": len(full_text),
            "method": extraction_method,
        }
        if len(full_text) <= 500:
            result["errors"].append(
                f"Insufficient text extracted for {ticker} in {year} "
                f"({len(full_text)} chars)"
            )
    except OperationTimeout:
        result["timings_seconds"][step] = round(time.time() - t0, 3)
        result["steps"][step] = {"status": "timeout"}
        result["errors"].append(
            f"Timeout extracting text for {ticker} in {year}"
        )
    except Exception as e:
        elapsed = round(time.time() - t0, 3)
        result["timings_seconds"][step] = elapsed
        result["steps"][step] = {"status": "error", "detail": str(e)[:300]}
        result["errors"].append(f"text_extraction: {e}")

    # ------------------------------------------------------------------
    # Step 5: ESG keyword analysis
    # ------------------------------------------------------------------
    step = "esg_analysis"
    t0 = time.time()
    if full_text and len(full_text) > 100:
        try:
            esg_hits = count_esg_hits(full_text)
            esg_sentences = extract_esg_sentences(full_text, max_per_keyword=2)

            total_hits = sum(
                esg_hits[cat]["total_hits"] for cat in esg_hits
            )
            total_unique = sum(
                esg_hits[cat]["unique_keywords_matched"] for cat in esg_hits
            )

            elapsed = round(time.time() - t0, 3)
            result["timings_seconds"][step] = elapsed
            result["steps"][step] = {
                "status": "pass" if total_hits > 0 else "fail",
                "total_hits": total_hits,
                "total_unique_keywords": total_unique,
                "by_category": {
                    cat: {
                        "hits": esg_hits[cat]["total_hits"],
                        "unique_keywords": esg_hits[cat]["unique_keywords_matched"],
                        "top_keywords": dict(
                            sorted(
                                esg_hits[cat]["keyword_hits"].items(),
                                key=lambda x: x[1],
                                reverse=True,
                            )[:5]
                        ),
                    }
                    for cat in esg_hits
                },
                "sample_sentences": {
                    cat: sents[:2]
                    for cat, sents in esg_sentences.items()
                },
            }
            if total_hits == 0:
                result["errors"].append(
                    f"No ESG keywords found for {ticker} in {year}"
                )
        except Exception as e:
            elapsed = round(time.time() - t0, 3)
            result["timings_seconds"][step] = elapsed
            result["steps"][step] = {"status": "error", "detail": str(e)[:300]}
            result["errors"].append(f"esg_analysis: {e}")
    else:
        result["timings_seconds"][step] = 0.0
        result["steps"][step] = {
            "status": "skip",
            "detail": "No text available for ESG analysis",
        }

    # ------------------------------------------------------------------
    # Determine overall pass/fail
    # ------------------------------------------------------------------
    critical_steps = ["fetch_filings", "parse_filing"]
    critical_passed = all(
        result["steps"].get(s, {}).get("status") == "pass"
        for s in critical_steps
    )
    result["passed"] = critical_passed
    result["total_time_seconds"] = round(
        sum(result["timings_seconds"].values()), 3
    )

    return result


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------
def run_full_evaluation():
    """Run the complete evaluation matrix and produce JSON output."""
    overall_start = time.time()

    print("=" * 72)
    print("  edgartools COMPREHENSIVE EVALUATION")
    print(f"  Companies: {', '.join(COMPANIES)}")
    print(f"  Years:     {', '.join(str(y) for y in YEARS)}")
    print(f"  Started:   {datetime.now().isoformat()}")
    print("=" * 72)

    # ------------------------------------------------------------------
    # Import and configure edgartools
    # ------------------------------------------------------------------
    try:
        from edgar import Company, set_identity
        set_identity(f"{SEC_IDENTITY_NAME} {SEC_IDENTITY_EMAIL}")
        print(f"\n[OK] edgartools imported, identity set to: {SEC_IDENTITY_NAME}")
    except ImportError as e:
        print(f"\n[FATAL] Cannot import edgartools: {e}")
        print("Install with: pip install edgartools")
        sys.exit(1)
    except Exception as e:
        print(f"\n[WARN] Identity setup issue (continuing): {e}")

    # ------------------------------------------------------------------
    # Iterate over all company+year combinations
    # ------------------------------------------------------------------
    all_results = []
    company_cache = {}  # cache Company objects to avoid redundant lookups

    total_combos = len(COMPANIES) * len(YEARS)
    combo_idx = 0

    for ticker in COMPANIES:
        # Get or create Company object
        if ticker not in company_cache:
            try:
                company_obj = Company(ticker)
                company_cache[ticker] = company_obj
                print(f"\n[OK] Loaded company: {ticker} -> {company_obj.name}")
                time.sleep(REQUEST_DELAY)
            except Exception as e:
                print(f"\n[FAIL] Cannot load company {ticker}: {e}")
                # Record failures for every year
                for year in YEARS:
                    combo_idx += 1
                    all_results.append({
                        "ticker": ticker,
                        "year": year,
                        "passed": False,
                        "steps": {"company_load": {"status": "error", "detail": str(e)[:300]}},
                        "errors": [f"Company load failed: {e}"],
                        "timings_seconds": {},
                        "total_time_seconds": 0,
                    })
                    print(f"  [{combo_idx}/{total_combos}] {ticker}/{year} ... SKIP (company load failed)")
                continue
        else:
            company_obj = company_cache[ticker]

        for year in YEARS:
            combo_idx += 1
            label = f"{ticker}/{year}"
            print(f"\n  [{combo_idx}/{total_combos}] Testing {label} ...", end=" ", flush=True)

            t0 = time.time()
            try:
                result = test_single_filing(company_obj, ticker, year, Company)
            except Exception as e:
                result = {
                    "ticker": ticker,
                    "year": year,
                    "passed": False,
                    "steps": {},
                    "errors": [f"Unhandled exception: {traceback.format_exc()[:500]}"],
                    "timings_seconds": {},
                    "total_time_seconds": round(time.time() - t0, 3),
                }

            all_results.append(result)

            status_icon = "PASS" if result["passed"] else "FAIL"
            elapsed = result.get("total_time_seconds", round(time.time() - t0, 3))
            print(f"{status_icon} ({elapsed:.1f}s)", flush=True)

            if result["errors"]:
                for err in result["errors"][:2]:
                    print(f"        -> {err[:120]}")

            # Respect SEC rate limits between filings
            time.sleep(REQUEST_DELAY)

    overall_elapsed = round(time.time() - overall_start, 2)

    # ------------------------------------------------------------------
    # Build summary
    # ------------------------------------------------------------------
    pass_count = sum(1 for r in all_results if r["passed"])
    fail_count = total_combos - pass_count

    # Build the matrix (ticker x year)
    matrix = {}
    for r in all_results:
        t = r["ticker"]
        y = r["year"]
        if t not in matrix:
            matrix[t] = {}
        matrix[t][y] = "PASS" if r["passed"] else "FAIL"

    # Aggregate ESG stats
    esg_agg = {"Environmental": [], "Social": [], "Governance": []}
    for r in all_results:
        esg_step = r.get("steps", {}).get("esg_analysis", {})
        if esg_step.get("status") == "pass":
            by_cat = esg_step.get("by_category", {})
            for cat in esg_agg:
                hits = by_cat.get(cat, {}).get("hits", 0)
                esg_agg[cat].append(hits)

    esg_summary = {}
    for cat, vals in esg_agg.items():
        if vals:
            esg_summary[cat] = {
                "filings_with_hits": len([v for v in vals if v > 0]),
                "total_filings_analyzed": len(vals),
                "avg_hits": round(sum(vals) / len(vals), 1),
                "max_hits": max(vals),
                "min_hits": min(vals),
            }
        else:
            esg_summary[cat] = {
                "filings_with_hits": 0,
                "total_filings_analyzed": 0,
            }

    # ------------------------------------------------------------------
    # Assemble final JSON output
    # ------------------------------------------------------------------
    output = {
        "evaluation": "edgartools comprehensive SEC EDGAR extraction test",
        "library": "edgartools (dgunning/edgartools)",
        "run_timestamp": datetime.now().isoformat(),
        "total_runtime_seconds": overall_elapsed,
        "configuration": {
            "companies": COMPANIES,
            "years": YEARS,
            "total_combinations": total_combos,
            "operation_timeout_seconds": OPERATION_TIMEOUT,
            "request_delay_seconds": REQUEST_DELAY,
        },
        "summary": {
            "total_tests": total_combos,
            "passed": pass_count,
            "failed": fail_count,
            "pass_rate": f"{100 * pass_count / total_combos:.1f}%",
            "matrix": matrix,
        },
        "esg_summary": esg_summary,
        "esg_keywords_used": {
            cat: len(kws) for cat, kws in ESG_KEYWORDS.items()
        },
        "detailed_results": all_results,
    }

    # ------------------------------------------------------------------
    # Write JSON results
    # ------------------------------------------------------------------
    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n\nResults saved to: {RESULTS_FILE}")

    # ------------------------------------------------------------------
    # Print summary table
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("  SUMMARY TABLE")
    print("=" * 72)

    # Header row
    year_strs = [str(y) for y in YEARS]
    header = f"{'Ticker':<8}" + "".join(f"{y:>8}" for y in year_strs) + f"{'  Total':>8}"
    print(header)
    print("-" * len(header))

    for ticker in COMPANIES:
        row = f"{ticker:<8}"
        tick_pass = 0
        for year in YEARS:
            status = matrix.get(ticker, {}).get(year, "N/A")
            row += f"{status:>8}"
            if status == "PASS":
                tick_pass += 1
        row += f"{tick_pass:>6}/{len(YEARS)}"
        print(row)

    print("-" * len(header))
    totals_row = f"{'Total':<8}"
    for year in YEARS:
        yr_pass = sum(
            1 for t in COMPANIES
            if matrix.get(t, {}).get(year) == "PASS"
        )
        totals_row += f"{yr_pass}/{len(COMPANIES):>7}"
    totals_row += f"{pass_count:>6}/{total_combos}"
    print(totals_row)

    print(f"\nOverall pass rate: {pass_count}/{total_combos} "
          f"({100 * pass_count / total_combos:.1f}%)")
    print(f"Total runtime: {overall_elapsed:.1f}s")

    # ------------------------------------------------------------------
    # Print ESG summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("  ESG KEYWORD ANALYSIS SUMMARY")
    print("=" * 72)
    for cat in ["Environmental", "Social", "Governance"]:
        info = esg_summary.get(cat, {})
        analyzed = info.get("total_filings_analyzed", 0)
        with_hits = info.get("filings_with_hits", 0)
        avg = info.get("avg_hits", 0)
        mx = info.get("max_hits", 0)
        print(
            f"  {cat:<16}: {with_hits}/{analyzed} filings with hits | "
            f"avg={avg} | max={mx}"
        )

    print("\n" + "=" * 72)
    print("  EVALUATION COMPLETE")
    print("=" * 72)

    return output


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_full_evaluation()
