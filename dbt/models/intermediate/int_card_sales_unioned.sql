WITH ebay AS (
    SELECT * FROM {{ ref('stg_ebay_sales') }}
),

pwcc AS (
    SELECT * FROM {{ ref('stg_pwcc_sales') }}
),

myslabs AS (
    SELECT * FROM {{ ref('stg_myslabs_sales') }}
),

unioned AS (
    SELECT * FROM ebay
    UNION ALL
    SELECT * FROM pwcc
    UNION ALL
    SELECT * FROM myslabs
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['source', 'source_listing_id']) }} AS sale_id,
    *
FROM unioned
