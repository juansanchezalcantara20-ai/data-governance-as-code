-- Service orders: exact duplicates removed, both source date formats unified, status normalised.
SELECT DISTINCT
    upper(trim(order_id))                                      AS order_id,
    upper(trim(customer_id))                                   AS customer_id,
    nullif(upper(trim(asset_id)), '')                          AS asset_id,
    trim(service_type)                                         AS service_type,
    CAST(coalesce(try_strptime(opened_on, '%Y-%m-%d'),
                  try_strptime(opened_on, '%d/%m/%Y')) AS DATE) AS opened_on,
    CAST(coalesce(try_strptime(nullif(closed_on, ''), '%Y-%m-%d'),
                  try_strptime(nullif(closed_on, ''), '%d/%m/%Y')) AS DATE) AS closed_on,
    upper(trim(status))                                        AS status,
    try_cast(planned_hours AS INTEGER)                         AS planned_hours,
    try_cast(planned_labor_cost AS DOUBLE)                     AS planned_labor_cost,
    try_cast(planned_material_cost AS DOUBLE)                  AS planned_material_cost,
    try_cast(price AS DOUBLE)                                  AS price
FROM bronze.service_orders
