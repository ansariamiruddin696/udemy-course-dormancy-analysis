-- ============================================================
-- RP WHIZ COMPANY | Account Dormancy & Reactivation Analysis
-- Approach : Weighted Signal Dormancy Score (WSDS) Model
-- Scope    : 12-Month Window — Sep 11, 2019 to Sep 10, 2020
-- Database : PostgreSQL
-- ============================================================
-- KEY NUMBERS (consistent with Python analysis):
--   Total scoped courses : 3,515
--   Active               : 1,356  (38.6%)
--   Low Engagement       : 610    (17.4%)
--   At Risk              : 695    (19.8%)
--   Critically Inactive  : 396    (11.3%)
--   Fully Dormant        : 458    (13.0%)
--   Total Dormant        : 2,159  (61.4%)
--   7% Reactivation Goal : 151 courses
-- ============================================================


-- ============================================================
-- SECTION 1: TABLE CREATION
-- ============================================================

CREATE TABLE IF NOT EXISTS udemy_courses (
    id                            INTEGER PRIMARY KEY,
    title                         TEXT,
    url                           TEXT,
    is_paid                       BOOLEAN,
    num_subscribers               INTEGER,
    avg_rating                    FLOAT,
    avg_rating_recent             FLOAT,
    rating                        FLOAT,
    num_reviews                   INTEGER,
    is_wishlisted                 BOOLEAN,
    num_published_lectures        INTEGER,
    num_published_practice_tests  INTEGER,
    created                       TIMESTAMPTZ,
    published_time                TIMESTAMPTZ,
    discount_price_amount         FLOAT,
    discount_price_currency       VARCHAR(10),
    price_detail_amount           FLOAT,
    price_detail_currency         VARCHAR(10)
);


-- ============================================================
-- SECTION 2: 12-MONTH SCOPE FILTER VIEW
-- ============================================================
-- Only courses published Sep 11, 2019 → Sep 10, 2020

CREATE OR REPLACE VIEW vw_scoped_courses AS
SELECT
    id,
    title,
    is_paid,
    num_subscribers,
    avg_rating,
    avg_rating_recent,
    num_reviews,
    num_published_lectures,
    num_published_practice_tests,
    published_time,
    price_detail_amount                                     AS full_price,
    discount_price_amount,
    EXTRACT(YEAR  FROM published_time)                      AS published_year,
    EXTRACT(MONTH FROM published_time)                      AS published_month,

    -- Discount percentage
    CASE
        WHEN price_detail_amount > 0 AND discount_price_amount IS NOT NULL
        THEN ROUND(
            (price_detail_amount - discount_price_amount)
            / price_detail_amount * 100, 1)
        ELSE 0
    END                                                     AS discount_pct,

    -- Price tier
    CASE
        WHEN price_detail_amount <= 2000  THEN 'Budget (<₹2K)'
        WHEN price_detail_amount <= 5000  THEN 'Mid (₹2K-5K)'
        WHEN price_detail_amount <= 9000  THEN 'Standard (₹5K-9K)'
        WHEN price_detail_amount <= 13000 THEN 'Premium (₹9K-13K)'
        ELSE                                   'Luxury (>₹13K)'
    END                                                     AS price_tier

FROM udemy_courses
WHERE published_time >= '2019-09-11 00:00:00+00'
  AND published_time <= '2020-09-10 23:59:59+00';


-- ============================================================
-- SECTION 3: WSDS SCORING & DORMANCY CLASSIFICATION VIEW
-- ============================================================
-- Weighted Signal Dormancy Score (0–100):
--   Signal 1 — Subscribers  (0–40 pts): primary demand indicator
--   Signal 2 — Avg Rating   (0–30 pts): quality & visibility proxy
--   Signal 3 — Review Count (0–20 pts): social proof signal
--   Signal 4 — Lecture Count(0–10 pts): content completeness
--
-- Dormancy Tiers:
--   Active              : score  < 10
--   Low Engagement      : score  < 25
--   At Risk             : score  < 45
--   Critically Inactive : score  < 70
--   Fully Dormant       : score >= 70

CREATE OR REPLACE VIEW vw_dormancy_scored AS
WITH scored AS (
    SELECT
        *,

        -- Signal 1: Subscriber Count (0-40 pts)
        CASE
            WHEN num_subscribers = 0   THEN 40
            WHEN num_subscribers < 10  THEN 30
            WHEN num_subscribers < 50  THEN 20
            WHEN num_subscribers < 100 THEN 10
            ELSE 0
        END

        -- Signal 2: Average Rating (0-30 pts)
        + CASE
            WHEN avg_rating = 0    THEN 30
            WHEN avg_rating < 3.0  THEN 20
            WHEN avg_rating < 3.5  THEN 10
            ELSE 0
        END

        -- Signal 3: Review Count (0-20 pts)
        + CASE
            WHEN num_reviews = 0   THEN 20
            WHEN num_reviews < 5   THEN 15
            WHEN num_reviews < 10  THEN 8
            ELSE 0
        END

        -- Signal 4: Lecture Count (0-10 pts)
        + CASE
            WHEN num_published_lectures = 0  THEN 10
            WHEN num_published_lectures < 5  THEN 5
            ELSE 0
        END                                                 AS dormancy_score

    FROM vw_scoped_courses
)
SELECT
    *,

    -- Dormancy tier classification
    CASE
        WHEN dormancy_score < 10 THEN 'Active'
        WHEN dormancy_score < 25 THEN 'Low Engagement'
        WHEN dormancy_score < 45 THEN 'At Risk'
        WHEN dormancy_score < 70 THEN 'Critically Inactive'
        ELSE                          'Fully Dormant'
    END                                                     AS dormancy_status,

    -- Job class (banking segment analogy)
    CASE
        WHEN NOT is_paid                       THEN 'JC-4 Freemium'
        WHEN num_subscribers >= 100000         THEN 'JC-1 Premium'
        WHEN num_subscribers >= 10000          THEN 'JC-2 Standard'
        ELSE                                        'JC-3 Basic'
    END                                                     AS job_class

FROM scored;


-- ============================================================
-- SECTION 4: KPI SUMMARY CARD
-- ============================================================
-- Expected output:
--   total_courses=3515 | dormancy_rate=61.4% | active=1356
--   dormant=2159 | reactivation_target_7pct=151

SELECT
    COUNT(*)                                                AS total_courses,
    SUM(CASE WHEN dormancy_status = 'Active'             THEN 1 ELSE 0 END) AS active,
    SUM(CASE WHEN dormancy_status = 'Low Engagement'     THEN 1 ELSE 0 END) AS low_engagement,
    SUM(CASE WHEN dormancy_status = 'At Risk'            THEN 1 ELSE 0 END) AS at_risk,
    SUM(CASE WHEN dormancy_status = 'Critically Inactive'THEN 1 ELSE 0 END) AS critically_inactive,
    SUM(CASE WHEN dormancy_status = 'Fully Dormant'      THEN 1 ELSE 0 END) AS fully_dormant,
    SUM(CASE WHEN dormancy_status != 'Active'            THEN 1 ELSE 0 END) AS total_dormant,
    ROUND(
        SUM(CASE WHEN dormancy_status != 'Active' THEN 1 ELSE 0 END)
        * 100.0 / COUNT(*), 1
    )                                                       AS dormancy_rate_pct,
    ROUND(
        SUM(CASE WHEN dormancy_status != 'Active' THEN 1 ELSE 0 END) * 0.07
    )                                                       AS reactivation_target_7pct,
    ROUND(AVG(dormancy_score), 2)                           AS avg_dormancy_score
FROM vw_dormancy_scored;


-- ============================================================
-- SECTION 5: DORMANCY BREAKDOWN BY TIER
-- ============================================================

SELECT
    dormancy_status,
    COUNT(*)                                                AS course_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1)      AS pct_of_total,
    ROUND(AVG(num_subscribers), 1)                          AS avg_subscribers,
    ROUND(AVG(avg_rating), 2)                               AS avg_rating,
    ROUND(AVG(num_reviews), 1)                              AS avg_reviews,
    ROUND(AVG(dormancy_score), 1)                           AS avg_dormancy_score
FROM vw_dormancy_scored
GROUP BY dormancy_status
ORDER BY
    CASE dormancy_status
        WHEN 'Active'              THEN 1
        WHEN 'Low Engagement'      THEN 2
        WHEN 'At Risk'             THEN 3
        WHEN 'Critically Inactive' THEN 4
        ELSE 5
    END;


-- ============================================================
-- SECTION 6: DORMANCY BY JOB CLASS
-- ============================================================
-- Expected: JC-3 Basic has highest dormancy rate (65.4%)

SELECT
    job_class,
    COUNT(*)                                                AS total_courses,
    SUM(CASE WHEN dormancy_status = 'Active'  THEN 1 ELSE 0 END) AS active_count,
    SUM(CASE WHEN dormancy_status != 'Active' THEN 1 ELSE 0 END) AS dormant_count,
    ROUND(
        SUM(CASE WHEN dormancy_status != 'Active' THEN 1 ELSE 0 END)
        * 100.0 / COUNT(*), 1
    )                                                       AS dormancy_rate_pct,
    ROUND(AVG(dormancy_score), 2)                           AS avg_dormancy_score,
    ROUND(AVG(num_subscribers), 1)                          AS avg_subscribers
FROM vw_dormancy_scored
GROUP BY job_class
ORDER BY job_class;


-- ============================================================
-- SECTION 7: MONTHLY DORMANCY TREND (12-Month Window)
-- ============================================================
-- Expected: Dormancy peaks in Jul-Aug 2020 (~70-79%)

SELECT
    published_month,
    TO_CHAR(DATE '2020-01-01' + (published_month - 1) * INTERVAL '1 month',
            'Mon YYYY')                                     AS month_label,
    COUNT(*)                                                AS total_courses,
    SUM(CASE WHEN dormancy_status != 'Active' THEN 1 ELSE 0 END) AS dormant_count,
    ROUND(
        SUM(CASE WHEN dormancy_status != 'Active' THEN 1 ELSE 0 END)
        * 100.0 / COUNT(*), 1
    )                                                       AS dormancy_rate_pct,
    ROUND(AVG(dormancy_score), 2)                           AS avg_score
FROM vw_dormancy_scored
GROUP BY published_month
ORDER BY published_month;


-- ============================================================
-- SECTION 8: ROOT CAUSE ANALYSIS — INACTIVITY DRIVERS
-- ============================================================

SELECT
    dormancy_status,
    COUNT(*)                                                AS course_count,

    ROUND(SUM(CASE WHEN num_subscribers = 0  THEN 1.0 ELSE 0 END)
          * 100 / COUNT(*), 1)                              AS pct_zero_subscribers,

    ROUND(SUM(CASE WHEN num_subscribers < 50 THEN 1.0 ELSE 0 END)
          * 100 / COUNT(*), 1)                              AS pct_low_subscribers,

    ROUND(SUM(CASE WHEN avg_rating = 0       THEN 1.0 ELSE 0 END)
          * 100 / COUNT(*), 1)                              AS pct_unrated,

    ROUND(SUM(CASE WHEN avg_rating < 3.5 AND avg_rating > 0 THEN 1.0 ELSE 0 END)
          * 100 / COUNT(*), 1)                              AS pct_low_rating,

    ROUND(SUM(CASE WHEN num_reviews = 0      THEN 1.0 ELSE 0 END)
          * 100 / COUNT(*), 1)                              AS pct_zero_reviews,

    ROUND(SUM(CASE WHEN num_published_lectures < 5 THEN 1.0 ELSE 0 END)
          * 100 / COUNT(*), 1)                              AS pct_minimal_content

FROM vw_dormancy_scored
GROUP BY dormancy_status
ORDER BY
    CASE dormancy_status
        WHEN 'Active'              THEN 1
        WHEN 'Low Engagement'      THEN 2
        WHEN 'At Risk'             THEN 3
        WHEN 'Critically Inactive' THEN 4
        ELSE 5
    END;


-- ============================================================
-- SECTION 9: PRICE TIER vs DORMANCY
-- ============================================================

SELECT
    price_tier,
    COUNT(*)                                                AS total_courses,
    SUM(CASE WHEN dormancy_status = 'Active'  THEN 1 ELSE 0 END) AS active_count,
    SUM(CASE WHEN dormancy_status != 'Active' THEN 1 ELSE 0 END) AS dormant_count,
    ROUND(
        SUM(CASE WHEN dormancy_status != 'Active' THEN 1 ELSE 0 END)
        * 100.0 / COUNT(*), 1
    )                                                       AS dormancy_rate_pct,
    ROUND(AVG(dormancy_score), 2)                           AS avg_score
FROM vw_dormancy_scored
WHERE full_price > 0
GROUP BY price_tier
ORDER BY
    CASE price_tier
        WHEN 'Budget (<₹2K)'      THEN 1
        WHEN 'Mid (₹2K-5K)'       THEN 2
        WHEN 'Standard (₹5K-9K)'  THEN 3
        WHEN 'Premium (₹9K-13K)'  THEN 4
        ELSE 5
    END;


-- ============================================================
-- SECTION 10: TOP 50 REACTIVATION TARGETS (RPS Score)
-- ============================================================
-- RPS = 50% closeness to active threshold
--     + 30% subscriber base (scale/reach)
--     + 20% paid account lever (revenue potential)

SELECT
    id,
    title,
    job_class,
    dormancy_status,
    num_subscribers,
    dormancy_score,
    ROUND(
        0.50 * (1.0 - dormancy_score / 100.0) +
        0.30 * (num_subscribers::FLOAT / 374836) +
        0.20 * CASE WHEN is_paid THEN 1 ELSE 0 END,
        4
    )                                                       AS reactivation_priority_score,
    full_price,
    ROUND(avg_rating, 2)                                    AS avg_rating,
    num_reviews
FROM vw_dormancy_scored
WHERE dormancy_status != 'Active'
ORDER BY reactivation_priority_score DESC
LIMIT 50;


-- ============================================================
-- SECTION 11: DORMANCY SIGNAL CONTRIBUTION BREAKDOWN
-- ============================================================
-- Shows which signals drive dormancy score for each tier

SELECT
    dormancy_status,
    COUNT(*)                                                AS n,
    ROUND(AVG(
        CASE WHEN num_subscribers = 0   THEN 40
             WHEN num_subscribers < 10  THEN 30
             WHEN num_subscribers < 50  THEN 20
             WHEN num_subscribers < 100 THEN 10
             ELSE 0 END
    ), 2)                                                   AS avg_subscriber_pts,
    ROUND(AVG(
        CASE WHEN avg_rating = 0   THEN 30
             WHEN avg_rating < 3.0 THEN 20
             WHEN avg_rating < 3.5 THEN 10
             ELSE 0 END
    ), 2)                                                   AS avg_rating_pts,
    ROUND(AVG(
        CASE WHEN num_reviews = 0  THEN 20
             WHEN num_reviews < 5  THEN 15
             WHEN num_reviews < 10 THEN 8
             ELSE 0 END
    ), 2)                                                   AS avg_review_pts,
    ROUND(AVG(
        CASE WHEN num_published_lectures = 0 THEN 10
             WHEN num_published_lectures < 5 THEN 5
             ELSE 0 END
    ), 2)                                                   AS avg_lecture_pts,
    ROUND(AVG(dormancy_score), 2)                           AS avg_total_score
FROM vw_dormancy_scored
GROUP BY dormancy_status
ORDER BY avg_total_score DESC;
