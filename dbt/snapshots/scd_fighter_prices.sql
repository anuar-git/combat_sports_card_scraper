{% snapshot scd_fighter_prices %}

{{
    config(
        target_schema='snapshots',
        unique_key="fighter_id || '-' || cast(grade_id as string)",
        strategy='check',
        check_cols=['vwap_30d', 'vwap_7d', 'sale_count_30d'],
        invalidate_hard_deletes=True
    )
}}

SELECT
    fighter_id,
    grade_id,
    benchmark_date,
    vwap_7d,
    vwap_30d,
    vwap_90d,
    sale_count_7d,
    sale_count_30d
FROM {{ ref('fct_price_benchmarks') }}

{% endsnapshot %}
