-- Materials issued to service orders, with line cost.
SELECT DISTINCT
    upper(trim(issue_id))                    AS issue_id,
    upper(trim(order_id))                    AS order_id,
    upper(trim(material_id))                 AS material_id,
    try_cast(quantity AS INTEGER)            AS quantity,
    try_cast(unit_cost AS DOUBLE)            AS unit_cost,
    round(try_cast(quantity AS INTEGER) * try_cast(unit_cost AS DOUBLE), 2) AS line_cost,
    try_cast(issued_on AS DATE)              AS issued_on
FROM bronze.material_issues
