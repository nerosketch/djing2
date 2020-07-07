--
-- dhcp commit event
--
DROP FUNCTION IF EXISTS dhcp_commit_lease_add_update;
CREATE OR REPLACE FUNCTION dhcp_commit_lease_add_update(v_client_ip inet,
                                                        v_mac_addr macaddr,
                                                        v_dev_mac macaddr,
                                                        v_dev_port smallint)
  RETURNS networks_ip_leases
  LANGUAGE plpgsql
AS
$$
DECLARE
  t_customer record;
  t_pool     record;
  t_lease    record;
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
  select nil.id
  from networks_ip_leases nil
  where nil.customer_id = t_customer.baseaccount_ptr_id and
        nil.ip_address = v_client_ip and
        nil.is_dynamic
  limit 1;
  if FOUND
  then
    raise notice 'Ip has already attached';
    return null;
  end if;

  -- Create lease for customer.
  --  Find pool for new lease.
  select id into t_pool from networks_ip_pool where v_client_ip << network limit 1;

  --  Insert new lease
  insert into networks_ip_leases (ip_address, pool_id, mac_address, customer_id, is_dynamic)
      values
      (v_client_ip, t_pool.id, v_mac_addr, t_customer.baseaccount_ptr_id, true)
      returning id, ip_address, pool_id, lease_time, mac_address, customer_id, is_dynamic
      into t_lease;

  return t_lease;
END;
$$;
