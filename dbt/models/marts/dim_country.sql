{{
    config(
        materialized='table'
    )
}}

with countries as (
    select * from {{ ref('int_countries__profile') }}
),

-- take the most recent year as the current country profile
latest as (
    select *
    from countries
    qualify row_number() over (
        partition by country_code
        order by reference_year desc
    ) = 1
)

select
    country_code                        as country_key,
    country_name,
    reference_year                      as profile_year,
    population,
    gdp_usd,
    gdp_per_capita_usd,
    energy_profile,
    co2_per_unit_energy,

    -- metadata
    current_timestamp()                     as dbt_updated_at

from latest
