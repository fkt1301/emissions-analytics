{{
    config(
        materialized='table'
    )
}}

with emissions as (
    select * from {{ ref('fct_co2_emissions') }}
),

-- rank countries within each year
ranked as (
    select
        country_code,
        country_name,
        reference_year,
        co2_mt,
        gdp_per_capita_usd,
        fossil_share,
        energy_profile,

        -- absolute emissions rank (1 = highest emitter)
        rank() over (
            partition by reference_year
            order by co2_mt desc
        )                                       as co2_rank,

        -- emissions per capita rank
        rank() over (
            partition by reference_year
            order by safe_divide(co2_mt, population) desc
        )                                       as co2_per_capita_rank,

        -- fossil dependency rank (1 = most fossil dependent)
        rank() over (
            partition by reference_year
            order by fossil_share desc
        )                                       as fossil_rank,

        population,

        -- metadata
        current_timestamp()                     as dbt_updated_at

    from emissions
    where co2_mt is not null
)

select * from ranked
