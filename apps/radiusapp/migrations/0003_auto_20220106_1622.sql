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
BEGIN
    WITH updated_lease AS (
        -- UPDATE networks_ip_leases SET last_update = now(), mac_address = v_mac WHERE ip_address = v_ip RETURNING id
        UPDATE networks_ip_leases SET last_update = now() WHERE ip_address = v_ip RETURNING id
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
        v_rad_uniq_id,
        0, 0, 0, 0, false,
        v_customer_id,
        id
    FROM updated_lease
       -- Когда пытаемся создать сессию на аренду у которой уже есть сессия, то мы просто обновляем время, а надо ???
       -- Не терять бы сессию, когда обновляем session_id.
        ON CONFLICT (ip_lease_id) DO UPDATE SET
            last_event_time=now(),
            customer_id=v_customer_id,
            radius_username=v_radius_username,
            session_id=v_rad_uniq_id;

    IF FOUND THEN
        -- lease exists, a new record has not been created
        RETURN false;
    END IF;

    WITH new_lease AS (
        INSERT INTO networks_ip_leases(
            ip_address, pool_id, mac_address, customer_id, is_dynamic, last_update
        )
        VALUES (v_ip, (
            SELECT id FROM networks_ip_pool WHERE v_ip <<= network LIMIT 1
        ), v_mac, v_customer_id, true, now())
        ON CONFLICT (ip_address, mac_address, pool_id, customer_id) DO UPDATE SET last_update=now() RETURNING id
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
        v_rad_uniq_id,
        0, 0, 0, 0, false,
        v_customer_id,
        id
    FROM new_lease;

    RETURN FOUND;
END
$$ LANGUAGE plpgsql VOLATILE;
