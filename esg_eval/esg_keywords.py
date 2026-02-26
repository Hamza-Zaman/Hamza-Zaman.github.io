"""
Shared ESG keyword dictionary for fair comparison across all repos.
Used consistently in all test scripts to measure ESG signal detection.
"""

ESG_KEYWORDS = {
    'Environmental': [
        'climate change', 'carbon emissions', 'greenhouse gas', 'renewable energy',
        'environmental impact', 'sustainability', 'carbon footprint', 'net zero',
        'clean energy', 'environmental matters', 'climate risk', 'emissions reduction',
        'water usage', 'waste management', 'biodiversity', 'pollution',
        'energy efficiency', 'solar', 'wind power', 'recycling'
    ],
    'Social': [
        'human capital', 'employee', 'workforce', 'diversity', 'inclusion',
        'health and safety', 'labor practices', 'community', 'human rights',
        'employee benefits', 'talent', 'workplace', 'supply chain',
        'data privacy', 'customer safety', 'equal opportunity',
        'training', 'working conditions'
    ],
    'Governance': [
        'board of directors', 'corporate governance', 'ethics', 'compliance',
        'risk management', 'audit committee', 'executive compensation',
        'shareholder rights', 'anti-corruption', 'code of conduct',
        'internal controls', 'transparency', 'whistleblower',
        'independent directors', 'fiduciary'
    ]
}


def count_esg_hits(text, keywords=None):
    """Count ESG keyword matches in text. Returns dict with counts per category."""
    if keywords is None:
        keywords = ESG_KEYWORDS

    import re
    text_lower = text.lower()
    results = {}

    for category, kw_list in keywords.items():
        hits = {}
        for kw in kw_list:
            count = len(re.findall(r'\b' + re.escape(kw) + r'\b', text_lower))
            if count > 0:
                hits[kw] = count
        results[category] = {
            'total_hits': sum(hits.values()),
            'unique_keywords_matched': len(hits),
            'keyword_hits': hits
        }

    return results


def extract_esg_sentences(text, keywords=None, max_per_keyword=3):
    """Extract sentences containing ESG keywords from text."""
    if keywords is None:
        keywords = ESG_KEYWORDS

    import re
    results = {}

    for category, kw_list in keywords.items():
        sentences = []
        for kw in kw_list:
            pattern = r'[^.]*\b' + re.escape(kw) + r'\b[^.]*\.'
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:max_per_keyword]:
                cleaned = match.strip()
                if 50 < len(cleaned) < 500 and cleaned not in sentences:
                    sentences.append(cleaned)
        results[category] = sentences

    return results
