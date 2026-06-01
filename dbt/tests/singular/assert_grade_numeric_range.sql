SELECT *
FROM {{ ref('fct_card_sales') }}
WHERE grade_numeric IS NOT NULL
  AND (grade_numeric < 1.0 OR grade_numeric > 10.0)
