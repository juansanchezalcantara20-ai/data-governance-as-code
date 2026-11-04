-- Revenue and ABC tier per customer account. Contains contact personal data: masked by policy.
WITH orders AS (
    SELECT e.customer_id,
           count(*)                 AS orders,
           sum(e.price)             AS revenue,
           sum(e.gross_margin)      AS gross_margin,
           max(e.opened_on)         AS last_order_on
    FROM gold.service_order_economics e
    GROUP BY e.customer_id
)
SELECT
    c.customer_id,
    c.company_name,
    c.segment,
    c.country,
    c.contact_name,
    c.contact_email,
    c.marketing_consent,
    coalesce(o.orders, 0)                                AS orders,
    round(coalesce(o.revenue, 0), 2)                     AS revenue,
    round(coalesce(o.gross_margin, 0), 2)                AS gross_margin,
    o.last_order_on,
    CASE WHEN coalesce(o.revenue, 0) >= 60000 THEN 'A'
         WHEN coalesce(o.revenue, 0) >= 25000 THEN 'B'
         ELSE 'C' END                                    AS customer_tier
FROM silver.customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
