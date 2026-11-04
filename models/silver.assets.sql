-- Asset master, standardised.
SELECT DISTINCT
    upper(trim(asset_id))                    AS asset_id,
    trim(asset_type)                         AS asset_type,
    trim(manufacturer)                       AS manufacturer,
    trim(site)                               AS site,
    try_cast(operating_hours AS INTEGER)     AS operating_hours,
    try_cast(commissioned_on AS DATE)        AS commissioned_on
FROM bronze.assets
