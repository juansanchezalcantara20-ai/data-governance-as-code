-- Economics per service order: plan versus actual cost, cost variance and margin.
WITH labor AS (
    SELECT l.order_id,
           sum(l.hours)                      AS actual_hours,
           sum(l.hours * t.hourly_cost)      AS actual_labor_cost
    FROM silver.labor_entries l
    JOIN silver.technicians t ON t.technician_id = l.technician_id
    GROUP BY l.order_id
), materials AS (
    SELECT i.order_id, sum(i.line_cost) AS actual_material_cost
    FROM silver.material_issues i
    GROUP BY i.order_id
)
SELECT
    o.order_id,
    o.customer_id,
    o.asset_id,
    a.site,
    a.asset_type,
    o.service_type,
    o.status,
    o.opened_on,
    o.closed_on,
    o.planned_hours,
    round(coalesce(l.actual_hours, 0), 1)                                         AS actual_hours,
    round(o.planned_labor_cost + o.planned_material_cost, 2)                      AS planned_cost,
    round(coalesce(l.actual_labor_cost, 0), 2)                                    AS actual_labor_cost,
    round(coalesce(m.actual_material_cost, 0), 2)                                 AS actual_material_cost,
    round(coalesce(l.actual_labor_cost, 0) + coalesce(m.actual_material_cost, 0), 2) AS actual_cost,
    round(100 * ((coalesce(l.actual_labor_cost, 0) + coalesce(m.actual_material_cost, 0))
                 / nullif(o.planned_labor_cost + o.planned_material_cost, 0) - 1), 2) AS cost_variance_pct,
    o.price,
    round(o.price - coalesce(l.actual_labor_cost, 0) - coalesce(m.actual_material_cost, 0), 2) AS gross_margin,
    round(100 * (o.price - coalesce(l.actual_labor_cost, 0) - coalesce(m.actual_material_cost, 0))
          / nullif(o.price, 0), 2)                                                AS gross_margin_pct
FROM silver.service_orders o
LEFT JOIN silver.assets a ON a.asset_id = o.asset_id
LEFT JOIN labor l         ON l.order_id = o.order_id
LEFT JOIN materials m     ON m.order_id = o.order_id
WHERE o.status <> 'CANCELLED'
