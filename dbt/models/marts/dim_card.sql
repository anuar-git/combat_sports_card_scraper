{{
    config(materialized='table')
}}

WITH cards AS (
    SELECT DISTINCT
        card_year,
        card_set,
        card_number,
        fighter_id
    FROM {{ ref('int_fighter_name_resolved') }}
    WHERE card_year IS NOT NULL
      AND card_set IS NOT NULL
      AND card_number IS NOT NULL
),

fighters AS (
    SELECT fighter_id, debut_year
    FROM {{ ref('dim_fighter') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['card_year', 'card_set', 'card_number']) }} AS card_id,
    c.card_year,
    c.card_set,
    c.card_number,
    CASE
        WHEN f.debut_year IS NOT NULL AND c.card_year = f.debut_year THEN TRUE
        ELSE FALSE
    END AS is_rookie
FROM cards c
LEFT JOIN fighters f USING (fighter_id)
