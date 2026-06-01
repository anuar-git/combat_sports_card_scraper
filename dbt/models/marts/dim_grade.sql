{{
    config(materialized='table')
}}

WITH grades AS (
    SELECT 1 AS grade_id, 'PSA' AS grader, 10.0 AS grade_numeric, 'PSA 10'      AS grade_label UNION ALL
    SELECT 2,              'PSA',           9.0,                   'PSA 9'                      UNION ALL
    SELECT 3,              'BGS',           9.5,                   'BGS 9.5'                    UNION ALL
    SELECT 4,              'BGS',           9.0,                   'BGS 9'                      UNION ALL
    SELECT 5,              'SGC',           10.0,                  'SGC 10'                     UNION ALL
    SELECT 6,              'Raw',           NULL,                  'Raw/Ungraded'
)

SELECT
    grade_id,
    grader,
    CAST(grade_numeric AS FLOAT64) AS grade_numeric,
    grade_label
FROM grades
