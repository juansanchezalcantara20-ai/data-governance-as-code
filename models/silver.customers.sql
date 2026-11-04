-- Customer accounts; consent normalised to boolean.
SELECT DISTINCT
    upper(trim(customer_id))                 AS customer_id,
    trim(company_name)                       AS company_name,
    trim(segment)                            AS segment,
    trim(country)                            AS country,
    trim(contact_name)                       AS contact_name,
    lower(trim(contact_email))               AS contact_email,
    regexp_replace(contact_phone, '\D', '', 'g') AS contact_phone,
    try_cast(created_on AS DATE)             AS created_on,
    CASE WHEN upper(trim(marketing_consent)) IN ('Y', 'YES') THEN TRUE
         WHEN upper(trim(marketing_consent)) IN ('N', 'NO') THEN FALSE END AS marketing_consent
FROM bronze.customers
