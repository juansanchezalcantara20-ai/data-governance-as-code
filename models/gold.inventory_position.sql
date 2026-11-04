-- Stock position per material: on-hand value, 90-day consumption and coverage.
WITH usage AS (
    SELECT i.material_id, sum(i.quantity) AS issued_qty_90d
    FROM silver.material_issues i
    WHERE i.issued_on > (SELECT max(x.issued_on) FROM silver.material_issues x) - INTERVAL 90 DAY
    GROUP BY i.material_id
)
SELECT
    m.material_id,
    m.description,
    m.category,
    m.stock_on_hand,
    m.reorder_point,
    round(m.stock_on_hand * m.unit_cost, 2)                                   AS stock_value,
    CAST(coalesce(u.issued_qty_90d, 0) AS BIGINT)                             AS issued_qty_90d,
    round(m.stock_on_hand / nullif(coalesce(u.issued_qty_90d, 0) / 90.0, 0), 1) AS days_of_cover,
    m.stock_on_hand <= m.reorder_point                                        AS below_reorder_point
FROM silver.materials m
LEFT JOIN usage u ON u.material_id = m.material_id
