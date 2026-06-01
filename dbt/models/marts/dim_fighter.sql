{{
    config(materialized='table')
}}

SELECT
    {{ dbt_utils.generate_surrogate_key(['fighter_name_canonical', 'fighter_name_alias']) }} AS fighter_id,
    fighter_name_canonical,
    fighter_name_alias,
    sport,
    nationality,
    promotion,
    CAST(active AS BOOL)        AS active,
    CAST(debut_year AS INT64)   AS debut_year
FROM {{ ref('fighters') }}
