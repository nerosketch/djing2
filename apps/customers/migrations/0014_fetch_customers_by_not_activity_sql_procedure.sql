DROP TYPE IF EXISTS CUSTOMERS_AFK_TYPE CASCADE;
CREATE TYPE CUSTOMERS_AFK_TYPE AS
(
    timediff       interval,
    last_date      timestamptz,
    customer_id    bigint,
    customer_uname varchar,
    customer_fio   varchar
);


CREATE OR REPLACE FUNCTION fetch_customers_by_not_activity(
    date_limit timestamptz,
    out_limit integer
) RETURNS SETOF CUSTOMERS_AFK_TYPE AS
$$
WITH afk AS (
    SELECT MAX(CL.date)     AS last_date,
           CL.customer_id,
           MAX(BA.username) AS customer_uname,
           MAX(BA.fio)      AS customer_fio
    FROM customer_log CL
             LEFT JOIN base_accounts BA ON CL.customer_id = BA.id
             LEFT JOIN customers CS ON BA.id = CS.baseaccount_ptr_id
    WHERE CL.cost < 0
      AND BA.is_active
      AND CS.current_service_id IS NULL
    GROUP BY CL.customer_id
)
SELECT (NOW() - afk.last_date) as timediff, afk.*
FROM afk
WHERE afk.last_date < date_limit
LIMIT out_limit;
$$
    LANGUAGE sql;
