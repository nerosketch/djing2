DROP FUNCTION IF EXISTS create_lease_w_auto_pool_n_session(
  INET, MACADDR, INT, VARCHAR, UUID);

-- create lease with auto pool
CREATE OR REPLACE FUNCTION create_lease_w_auto_pool(
    v_ip inet,
    v_mac macaddr,
    v_customer_id int,
    v_radius_username varchar,
    v_rad_uniq_id uuid,
    v_svid smallint,
    v_cvid smallint
)
RETURNS bool
AS $$
BEGIN
      -- UPDATE networks_ip_leases SET last_update = now(), mac_address = v_mac WHERE ip_address = v_ip RETURNING id
      UPDATE networks_ip_leases
      SET
          last_update = now(),
          customer_id = v_customer_id,
          radius_username = v_radius_username
      WHERE
          session_id=v_rad_uniq_id;

    IF FOUND THEN
        -- lease exists, a new record has not been created
        RETURN false;
    END IF;

    INSERT INTO networks_ip_leases(
        ip_address, mac_address,
        pool_id,
        customer_id, is_dynamic,
        input_octets, output_octets, input_packets, output_packets,
        cvid, svid, state,
        lease_time, last_update,
        session_id,
        radius_username
    )
    VALUES (v_ip, v_mac, (
        SELECT id FROM networks_ip_pool WHERE v_ip <<= network LIMIT 1
      ), v_customer_id, true,
      0,0,0,0,
      v_cvid, v_svid, true,
      now(), now(),
      v_rad_uniq_id,
      v_radius_username
    )
      ON CONFLICT (ip_address, mac_address, pool_id, customer_id) DO UPDATE SET
        last_update=now(), ip_address=v_ip, mac_address=v_mac, session_id=v_rad_uniq_id;

    RETURN true;
END
$$ LANGUAGE plpgsql VOLATILE;

