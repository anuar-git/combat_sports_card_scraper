WITH ebay AS (
    SELECT * FROM {{ ref('stg_ebay_sales') }}
),

pwcc AS (
    SELECT * FROM {{ ref('stg_pwcc_sales') }}
),

unioned AS (
    SELECT * FROM ebay
    UNION ALL
    SELECT * FROM pwcc
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['source', 'source_listing_id']) }} AS sale_id,
    *
FROM unioned
