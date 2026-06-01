{{
    config(
        materialized='table',
        partition_by={
            "field": "benchmark_date",
            "data_type": "date",
            "granularity": "day"
        }
    )
}}

WITH sales AS (
    SELECT * FROM {{ ref('fct_card_sales') }}
    WHERE sale_price_usd IS NOT NULL
)

SELECT
    fighter_id,
    grade_id,
    sale_date                                                               AS benchmark_date,
    AVG(sale_price_usd) OVER (
        PARTITION BY fighter_id, grade_id
        ORDER BY sale_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )                                                                       AS vwap_7d,
    AVG(sale_price_usd) OVER (
        PARTITION BY fighter_id, grade_id
        ORDER BY sale_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    )                                                                       AS vwap_30d,
    AVG(sale_price_usd) OVER (
        PARTITION BY fighter_id, grade_id
        ORDER BY sale_date
        ROWS BETWEEN 89 PRECEDING AND CURRENT ROW
    )                                                                       AS vwap_90d,
    COUNT(*) OVER (
        PARTITION BY fighter_id, grade_id
        ORDER BY sale_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )                                                                       AS sale_count_7d,
    COUNT(*) OVER (
        PARTITION BY fighter_id, grade_id
        ORDER BY sale_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    )                                                                       AS sale_count_30d
FROM sales
