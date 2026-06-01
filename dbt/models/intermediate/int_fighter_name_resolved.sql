WITH sales AS (
    SELECT * FROM {{ ref('int_card_sales_unioned') }}
),

fighters AS (
    SELECT * FROM {{ ref('dim_fighter') }}
),

resolved AS (
    SELECT
        s.*,
        f.fighter_id,
        COALESCE(f.fighter_name_canonical, s.fighter_name_canonical) AS fighter_name_canonical,
        f.sport                                                        AS fighter_sport,
        f.nationality
    FROM sales s
    LEFT JOIN fighters f
        ON LOWER(TRIM(s.fighter_name)) = LOWER(TRIM(f.fighter_name_alias))
)

SELECT * FROM resolved
