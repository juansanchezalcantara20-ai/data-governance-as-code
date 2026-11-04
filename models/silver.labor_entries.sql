-- Hours booked per technician and service order.
SELECT DISTINCT
    upper(trim(entry_id))                    AS entry_id,
    upper(trim(order_id))                    AS order_id,
    upper(trim(technician_id))               AS technician_id,
    try_cast(work_date AS DATE)              AS work_date,
    try_cast(hours AS DOUBLE)                AS hours,
    lower(trim(approver_email))              AS approver_email
FROM bronze.labor_entries
