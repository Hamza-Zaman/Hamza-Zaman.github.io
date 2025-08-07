---
title: Power BI Sales Insights
summary: Automated reporting cut weekly work from 3h to 15m.
tech: Power BI • DAX • SQL
github: https://github.com/HamzaZaman/powerbi-sales
demo:
---

## Problem
Manual Excel reporting consumed hours and caused inconsistencies.

## Approach
- Star schema (sales/invoices facts; date/product/customer dims).
- DAX measures for margin %, YoY, variance.
- Automated refresh & exception logging.

## Result
- Weekly report time reduced from **3 hours** to **15 minutes**.
- Single KPI source of truth for Finance & Sales.

[Code ↗]({frontmatter.github})
