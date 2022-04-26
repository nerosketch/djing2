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
          radius_username = v_radius_username,
          state = true
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
      0, 0, 0, 0,
      v_cvid, v_svid, true,
      now(), now(),
      v_rad_uniq_id,
      v_radius_username
    )
      ON CONFLICT (ip_address) DO UPDATE SET
        last_update=now(), ip_address=v_ip, mac_address=v_mac,
        session_id=v_rad_uniq_id, radius_username=v_radius_username;

    RETURN true;
END
$$ LANGUAGE plpgsql VOLATILE;


----------------------------------------------------------------------------


CREATE OR REPLACE FUNCTION lease_commit_add_update(v_client_ip inet,
                                                   v_mac_addr macaddr,
                                                   v_dev_mac macaddr,
                                                   v_dev_port smallint)
  RETURNS networks_ip_leases
  LANGUAGE plpgsql
AS
$$
DECLARE
  t_customer customers;
  t_pool     networks_ip_pool;
  t_lease    networks_ip_leases;
BEGIN
  -- find customer by device
  -- if customer is dynamic then check
  -- if lease is exist, if lease does not exists
  -- then assign a new session

  -- find customer by device
  select *
         into t_customer
  from find_customer_by_device_credentials(v_dev_mac, v_dev_port);
  if not FOUND
  then
    raise exception 'Customer with device mac=% not found', v_dev_mac;
  end if;

  -- Find customer leases
  perform
  nil.id
  from networks_ip_leases nil
  where nil.customer_id = t_customer.baseaccount_ptr_id
    and
    nil.ip_address = v_client_ip
    and
    nil.is_dynamic
  limit 1;
  if FOUND
  then
    -- raise notice 'Ip has already attached';
    -- Update `last_update` field in customer lease
    perform update_customer_lease_last_update_time_field(t_customer.baseaccount_ptr_id, v_client_ip);
    return null;
  end if;

  -- Create lease for customer.
  --  Find pool for new lease.
  select id into t_pool from networks_ip_pool where v_client_ip << network limit 1;
  if not FOUND then
    raise exception 'client_ip in unknown subnet';
  end if;

  -- Try update ip lease
  update networks_ip_leases nil
  set customer_id = t_customer.baseaccount_ptr_id,
    lease_time = now(),
    mac_address = v_mac_addr,
    last_update = now()
  where
    nil.ip_address = v_client_ip
  and nil.is_dynamic
  returning id, ip_address, pool_id, lease_time, mac_address, customer_id, is_dynamic
  into t_lease;

  if not FOUND then
    --  Insert new lease if not updated
    insert into networks_ip_leases (
      ip_address, pool_id, mac_address, customer_id, is_dynamic, last_update, cvid, svid,
      input_octets, input_packets, output_octets, output_packets
    )
    values
    (
      v_client_ip, t_pool.id, v_mac_addr, t_customer.baseaccount_ptr_id, true, now(), 0, 0,
      0, 0, 0, 0
    )
    returning id, ip_address, pool_id, lease_time, mac_address, customer_id, is_dynamic
    into t_lease;
  end if;

  return t_lease;
END;
$$;
