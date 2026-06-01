{{
    config(
        materialized='table',
        partition_by={
            "field": "sale_date",
            "data_type": "date",
            "granularity": "day"
        }
    )
}}

WITH sales AS (
    SELECT * FROM {{ ref('int_fighter_name_resolved') }}
),

cards AS (
    SELECT * FROM {{ ref('dim_card') }}
),

grades AS (
    SELECT * FROM {{ ref('dim_grade') }}
),

joined AS (
    SELECT
        s.sale_id,
        s.fighter_id,
        c.card_id,
        g.grade_id,
        s.source_listing_id,
        s.source,
        s.sale_price_usd,
        s.sale_date,
        s.sale_type,
        s.has_buyer_premium,
        s.listing_title,
        s.listing_url,
        s.scraped_at,
        s.ingested_at
    FROM sales s
    LEFT JOIN cards c
        ON s.card_year = c.card_year
        AND s.card_set = c.card_set
        AND s.card_number = c.card_number
    LEFT JOIN grades g
        ON UPPER(TRIM(s.grader)) = g.grader
        AND s.grade_numeric = g.grade_numeric
)

SELECT * FROM joined
