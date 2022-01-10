DROP TYPE IF EXISTS FetchSubscriberLeaseReturnType CASCADE;

DROP FUNCTION IF EXISTS fetch_subscriber_lease(
  UUID, INET, MACADDR, SMALLINT, INTEGER,
  VARCHAR(32), INTEGER, INTEGER, INTEGER,
  INTEGER, BOOLEAN);

-- create lease with auto pool and session
CREATE OR REPLACE FUNCTION create_lease_w_auto_pool_n_session(
    v_ip inet,
    v_mac macaddr,
    v_customer_id int,
    v_radius_username varchar,
    v_rad_uniq_id uuid
)
RETURNS bool
AS $$
DECLARE
    aff_rows int;
BEGIN
    PERFORM id FROM networks_ip_leases WHERE ip_address=v_ip LIMIT 1;

    IF FOUND THEN
        -- update session counters
        RETURN false;
    END IF;

    WITH new_lease AS (
        WITH find_pool AS (
            SELECT id
            FROM networks_ip_pool
            WHERE
                v_ip <<= network
            LIMIT 1
        )
        INSERT INTO networks_ip_leases(
            ip_address, pool_id, mac_address, customer_id, is_dynamic, last_update
        )
        (SELECT v_ip, id, v_mac, v_customer_id, true, now() FROM find_pool)
        ON CONFLICT DO NOTHING RETURNING id
    )
    INSERT INTO radius_customer_session(
        assign_time,
        last_event_time,
        radius_username,
        session_id,
        input_octets, output_octets, input_packets, output_packets, closed,
        customer_id,
        ip_lease_id
    )
    SELECT
        now(),
        now(),
        v_radius_username,
        v_rad_uniq_id::uuid,
        0, 0, 0, 0, false,
        v_customer_id,
        new_lease.id
    FROM new_lease;

    GET DIAGNOSTICS aff_rows := ROW_COUNT;
    RETURN aff_rows > 0;
END
$$ LANGUAGE plpgsql VOLATILE;
