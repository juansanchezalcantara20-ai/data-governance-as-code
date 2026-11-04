-- Monthly KPIs per site for the operations dashboard.
SELECT
    e.site,
    CAST(date_trunc('month', e.opened_on) AS DATE)                    AS month,
    count(*)                                                          AS orders,
    count(*) FILTER (WHERE e.status = 'CLOSED')                       AS closed_orders,
    round(sum(e.actual_hours), 1)                                     AS actual_hours,
    round(sum(e.actual_cost), 2)                                      AS actual_cost,
    round(sum(e.price), 2)                                            AS revenue,
    round(100 * sum(e.gross_margin) / nullif(sum(e.price), 0), 2)     AS gross_margin_pct
FROM gold.service_order_economics e
GROUP BY e.site, CAST(date_trunc('month', e.opened_on) AS DATE)
