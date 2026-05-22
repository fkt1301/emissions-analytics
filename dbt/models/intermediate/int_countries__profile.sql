with owid as (
    select * from {{ ref('stg_owid__co2') }}
),

worldbank as (
    select * from {{ ref('stg_worldbank__indicators') }}
),

joined as (
    select
        o.country_code,
        o.country_name,
        o.reference_year,
        o.population,
        o.gdp_usd,

        -- derived
        case
            when o.gdp_usd is not null and o.population > 0
            then o.gdp_usd / o.population
        end                                         as gdp_per_capita_usd,

        o.co2_per_unit_energy,

        -- world bank energy indicators
        w.renewable_energy_pct,
        w.renewable_electricity_pct,
        w.energy_use_per_capita_kgoe,
        w.electricity_access_pct,
        w.urban_population_pct,

        -- energy profile flag — now uses World Bank renewable data when available
        case
            when coalesce(w.renewable_energy_pct, 0) >= 50  then 'high_renewable'
            when coalesce(w.renewable_energy_pct, 0) >= 20  then 'transitioning'
            else                                                  'fossil_dependent'
        end                                         as energy_profile

    from owid o
    left join worldbank w
        on o.country_code = w.country_code
        and o.reference_year = w.reference_year
    where o.population > 0
)

select * from joined


/*
with countries as (
    select
        country_code,
        country_name,
        reference_year,
        population,
        gdp_usd,

        -- derived
        case
            when gdp_usd is not null and population > 0
            then gdp_usd / population
        end                                     as gdp_per_capita_usd,

        co2_per_unit_energy,

        -- energy profile flag
        case
            when co2_per_unit_energy < 1.5  then 'low_carbon'
            when co2_per_unit_energy < 2.5  then 'transitioning'
            else                                 'fossil_dependent'
        end                                     as energy_profile

    from {{ ref('stg_owid__co2') }}
    where population > 0
)

select * from countries
*/
