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
    return null;
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
    return null;
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
    insert into networks_ip_leases (ip_address, pool_id, mac_address, customer_id, is_dynamic, last_update)
    values
    (v_client_ip, t_pool.id, v_mac_addr, t_customer.baseaccount_ptr_id, true, now())
    returning id, ip_address, pool_id, lease_time, mac_address, customer_id, is_dynamic
    into t_lease;
  end if;

  return t_lease;
END;
$$;

DROP TRIGGER networks_ip_lease_log_trigger ON networks_ip_leases;
CREATE TRIGGER networks_ip_lease_log_trigger
  AFTER INSERT OR UPDATE OF customer_id
  ON networks_ip_leases
  FOR EACH ROW
EXECUTE PROCEDURE networks_ip_lease_log_fn();
