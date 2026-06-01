SELECT *
FROM {{ ref('fct_card_sales') }}
WHERE sale_price_usd <= 0
