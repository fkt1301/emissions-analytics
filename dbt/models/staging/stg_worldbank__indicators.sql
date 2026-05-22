with source as (
    select * from {{ source('worldbank', 'worldbank_indicators_raw') }}
),

renamed as (
    select
        -- identifiers
        country_code,
        country_name,
        cast(year as integer)                       as reference_year,

        -- energy
        cast(renewable_energy_pct as float64)       as renewable_energy_pct,
        cast(renewable_electricity_pct as float64)  as renewable_electricity_pct,
        cast(energy_use_per_capita_kgoe as float64) as energy_use_per_capita_kgoe,
        cast(electricity_access_pct as float64)     as electricity_access_pct,

        -- development
        cast(urban_population_pct as float64)       as urban_population_pct,

        -- metadata
        _ingested_at

    from source
    where country_code is not null
)

select * from renamed
