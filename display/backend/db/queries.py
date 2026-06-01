import os

_PROJECT = os.getenv("GCP_PROJECT_ID", "{project}")
_DATASET = f"`{_PROJECT}.alt_cards_prod`"


def _t(table: str) -> str:
    return f"`{_PROJECT}.alt_cards_prod.{table}`"


MARKET_OVERVIEW_QUERY = f"""
SELECT
    f.fighter_name_canonical,
    f.fighter_id,
    f.sport,
    g.grade_label,
    pb.vwap_7d,
    pb.vwap_30d,
    pb.sale_count_30d,
    pb.price_pct_change_7d,
    pb.price_pct_change_30d,
    pb.benchmark_date
FROM {_t("fct_price_benchmarks")} pb
JOIN {_t("dim_fighter")} f ON pb.fighter_id = f.fighter_id
JOIN {_t("dim_grade")} g ON pb.grade_id = g.grade_id
WHERE pb.benchmark_date = CURRENT_DATE()
  AND pb.sale_count_30d >= 3
ORDER BY pb.sale_count_30d DESC
LIMIT 100
"""

FIGHTER_METADATA_QUERY = f"""
SELECT
    fighter_id,
    fighter_name_canonical,
    sport,
    promotion
FROM {_t("dim_fighter")}
WHERE fighter_id = @fighter_id
LIMIT 1
"""

FIGHTER_PRICE_HISTORY_QUERY = f"""
SELECT
    pb.benchmark_date,
    g.grade_label,
    pb.vwap_7d,
    pb.vwap_30d,
    pb.sale_count_30d
FROM {_t("fct_price_benchmarks")} pb
JOIN {_t("dim_grade")} g ON pb.grade_id = g.grade_id
WHERE pb.fighter_id = @fighter_id
  AND pb.benchmark_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
ORDER BY pb.benchmark_date ASC
"""

RECENT_SALES_QUERY = f"""
SELECT
    cs.source_listing_id,
    cs.listing_title,
    cs.sale_price_usd,
    cs.sale_date,
    cs.sale_type,
    cs.source,
    cs.listing_url,
    g.grade_label
FROM {_t("fct_card_sales")} cs
JOIN {_t("dim_grade")} g ON cs.grade_id = g.grade_id
WHERE cs.fighter_id = @fighter_id
ORDER BY cs.sale_date DESC
LIMIT 20
"""

TOP_MOVERS_QUERY = f"""
SELECT
    f.fighter_name_canonical,
    f.fighter_id,
    g.grade_label,
    pb.vwap_7d,
    pb.vwap_30d,
    pb.price_pct_change_7d,
    pb.sale_count_7d
FROM {_t("fct_price_benchmarks")} pb
JOIN {_t("dim_fighter")} f ON pb.fighter_id = f.fighter_id
JOIN {_t("dim_grade")} g ON pb.grade_id = g.grade_id
WHERE pb.benchmark_date = CURRENT_DATE()
  AND pb.sale_count_7d >= 2
  AND pb.price_pct_change_7d IS NOT NULL
ORDER BY ABS(pb.price_pct_change_7d) DESC
LIMIT 20
"""

ALL_FIGHTERS_QUERY = f"""
SELECT DISTINCT
    f.fighter_id,
    f.fighter_name_canonical,
    f.sport,
    f.promotion,
    MAX(pb.vwap_30d) AS vwap_30d,
    SUM(pb.sale_count_30d) AS sale_count_30d
FROM {_t("dim_fighter")} f
JOIN {_t("fct_price_benchmarks")} pb ON f.fighter_id = pb.fighter_id
WHERE pb.benchmark_date = CURRENT_DATE()
  AND pb.sale_count_30d >= 1
GROUP BY f.fighter_id, f.fighter_name_canonical, f.sport, f.promotion
ORDER BY f.fighter_name_canonical ASC
"""

FIGHTER_SEARCH_QUERY = f"""
SELECT DISTINCT
    f.fighter_id,
    f.fighter_name_canonical,
    f.sport,
    f.promotion,
    MAX(pb.vwap_30d) AS vwap_30d
FROM {_t("dim_fighter")} f
LEFT JOIN {_t("fct_price_benchmarks")} pb
    ON f.fighter_id = pb.fighter_id AND pb.benchmark_date = CURRENT_DATE()
WHERE LOWER(f.fighter_name_canonical) LIKE LOWER(@search_pattern)
GROUP BY f.fighter_id, f.fighter_name_canonical, f.sport, f.promotion
ORDER BY f.fighter_name_canonical ASC
LIMIT 20
"""
