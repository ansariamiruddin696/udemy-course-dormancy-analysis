# Udemy Course Dormancy & Reactivation Analysis

A behavioral segmentation and reactivation-targeting analysis built on the public Udemy India course catalog, framed around a banking-style "account dormancy" model — courses stand in for accounts, and engagement signals stand in for account activity.

## Problem

Most dormancy analyses use a binary flag ("no activity in 90 days = dormant"). That misses accounts that are declining but not yet inactive, and treats a barely-active account the same as a completely dead one. This project instead builds a **continuous severity score** so accounts can be triaged and prioritized, not just flagged.

## Approach: Weighted Signal Dormancy Score (WSDS)

A 0–100 composite score built from four independent, business-weighted signals:

| Signal | Max Points | Logic | Rationale |
|---|---|---|---|
| Subscriber count | 40 | 0 subs → 40, <10 → 30, <50 → 20, <100 → 10, ≥100 → 0 | Primary demand indicator |
| Average rating | 30 | 0 → 30, <3.0 → 20, <3.5 → 10, ≥3.5 → 0 | Quality/visibility proxy |
| Review count | 20 | 0 → 20, <5 → 15, <10 → 8, ≥10 → 0 | Social proof signal |
| Lecture count | 10 | 0 → 10, <5 → 5, ≥5 → 0 | Content completeness |

Accounts are then classified into 5 tiers:

| Tier | Score Range | Action |
|---|---|---|
| Active | < 10 | Retention rewards |
| Low Engagement | 10–24 | Proactive monitoring |
| At Risk | 25–44 | Early intervention |
| Critically Inactive | 45–69 | Urgent outreach |
| Fully Dormant | ≥ 70 | Reactivation campaign |

A separate **Reactivation Priority Score (RPS)** ranks dormant accounts for outreach:
`RPS = 50% score-proximity-to-active + 30% subscriber base + 20% paid-account lever`

## Scope

- **Source data:** 13,608 Udemy India courses (2010–2020)
- **Analysis window:** 3,515 courses published Sep 11, 2019 – Sep 10, 2020 (12 months)
- **Data quality:** 0 duplicates, 0 missing values, 0 out-of-range ratings, 0 pricing anomalies; 120 zero-lecture-but-subscribed courses flagged and retained with a partial score rather than dropped

## Key Findings

- **61.4% dormancy rate** (2,159 of 3,515 scoped courses) across the four non-active tiers
- **Zero/low subscriber count is the dominant driver**, affecting 73.8% of dormant accounts — more than double any other single signal
- Segmenting by account tier ("job class," a paid/subscriber-based grouping) shows dormancy is highly concentrated: the largest segment (**JC-3 Basic, paid + <10K subscribers**) has **65.4% dormancy**, versus 5.2% for the higher-tier segment
- **Dormancy rate rises with publish recency within the window** — peaking at 79% for courses published April 2020 — since newer listings have had less time to accumulate traction, a recency bias worth controlling for in any point-in-time dormancy model
- A 7% reactivation target on the dormant base equals **151 accounts**, with a segment-specific strategy (channel + offer + expected uplift) proposed for each tier

## Tech Stack

- **SQL (PostgreSQL):** table/view creation, CASE-based scoring logic, window functions, aggregations — used as an independent cross-validation of the Python results (matching tier counts)
- **Python (Pandas, Matplotlib/Seaborn):** data cleaning, feature engineering, scoring pipeline, and 3 figures (8 charts total) covering distribution, root-cause, and reactivation analysis
- **Power BI:** 4 exported CSVs (main dataset, KPI cards, reactivation targets, job-class breakdown) structured for a 4-row dashboard (KPI cards → tier trend → job-class breakdown → reactivation target table)

## Repository Structure

```
├── sql/
│   └── dormancy_queries.sql        # Table creation, scoring views, 11 analytical queries
├── python/
│   └── dormancy_analysis.py        # Cleaning, feature engineering, scoring, figure generation
├── figures/
│   ├── fig1_eda.png                # Distribution overview (4 charts)
│   ├── fig2_root_causes.png        # Root-cause analysis (2 charts)
│   └── fig3_reactivation.png       # Reactivation priority analysis (2 charts)
├── powerbi/
│   ├── pbi_main_dataset.csv
│   ├── pbi_kpi_cards.csv
│   ├── pbi_reactivation_targets.csv
│   └── pbi_jobclass_dormancy.csv
├── data/
│   └── sample_data.csv             # Sample of the source dataset (schema reference)
└── README.md
```

## Notes on Methodology

- Signal weights (40/30/20/10) reflect a deliberate business judgment — subscriber count is treated as the strongest demand signal — rather than being statistically derived; a natural extension would be to validate these weights against an actual outcome variable (e.g., revenue or completion rate) if one were available.
- Because this is a point-in-time model applied to a fixed 12-month window, newer accounts are structurally more likely to score as dormant simply because they've had less time to accumulate engagement. This recency effect is visible in the monthly trend and is called out explicitly rather than treated as a true health signal.

## Limitations

- Built on a public course-catalog dataset with course engagement standing in for account activity — a proxy, not real account/transaction data.
- Signal weights are heuristic, not statistically fit.
- The Power BI dashboard layout is specified but not yet built as a live `.pbix` file.
