-- Material master with stock parameters.
SELECT DISTINCT
    upper(trim(material_id))                 AS material_id,
    trim(description)                        AS description,
    trim(category)                           AS category,
    try_cast(unit_cost AS DOUBLE)            AS unit_cost,
    try_cast(stock_on_hand AS INTEGER)       AS stock_on_hand,
    try_cast(reorder_point AS INTEGER)       AS reorder_point,
    try_cast(lead_time_days AS INTEGER)      AS lead_time_days
FROM bronze.materials
