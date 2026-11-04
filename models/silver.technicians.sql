-- Field technicians with normalised contact data and numeric hourly cost.
SELECT DISTINCT
    upper(trim(technician_id))               AS technician_id,
    trim(national_id)                        AS national_id,
    trim(first_name)                         AS first_name,
    trim(last_name)                          AS last_name,
    lower(trim(email))                       AS email,
    regexp_replace(phone, '\D', '', 'g')     AS phone,
    trim(trade)                              AS trade,
    try_cast(hourly_cost AS DOUBLE)          AS hourly_cost
FROM bronze.technicians
