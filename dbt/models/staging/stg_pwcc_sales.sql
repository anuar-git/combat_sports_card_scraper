WITH source AS (
    SELECT * FROM {{ source('raw', 'pwcc_sales') }}
),

cleaned AS (
    SELECT
        CAST(listing_id AS STRING)                  AS source_listing_id,
        'pwcc'                                      AS source,
        CAST(sale_price_usd AS NUMERIC)             AS sale_price_usd,
        CAST(sale_date AS DATE)                     AS sale_date,
        CAST(scraped_at AS TIMESTAMP)               AS scraped_at,
        CAST(ingested_at AS TIMESTAMP)              AS ingested_at,
        listing_title,
        fighter_name,
        fighter_name_canonical,
        card_year,
        card_set,
        card_number,
        grade,
        grader,
        CAST(grade_numeric AS FLOAT64)              AS grade_numeric,
        CAST(listing_url AS STRING)                 AS listing_url,
        sale_type,
        CAST(TRUE AS BOOL)                          AS has_buyer_premium,
        CAST(is_outlier AS BOOL)                    AS is_outlier,
        sport,
        record_hash
    FROM source
    WHERE sale_price_usd > 0
      AND sale_date IS NOT NULL
      AND sale_date <= CURRENT_DATE()
      AND is_outlier = FALSE
)

SELECT * FROM cleaned
