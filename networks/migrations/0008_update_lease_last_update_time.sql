CREATE OR REPLACE FUNCTION update_customer_lease_last_update_time_field(v_customer_id integer,
                                                                        v_client_ip inet) RETURNS void AS
$$
  -- Update `last_update` field in leases
update networks_ip_leases nil
set last_update = now()
where nil.customer_id = v_customer_id
  and nil.ip_address = v_client_ip
  and nil.is_dynamic
$$
  LANGUAGE sql;


--
-- dhcp commit event
--
DROP FUNCTION IF EXISTS dhcp_commit_lease_add_update(inet, macaddr, macaddr, smallint);
CREATE OR REPLACE FUNCTION dhcp_commit_lease_add_update(v_client_ip inet,
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

  --  Insert new lease
  insert into networks_ip_leases (ip_address, pool_id, mac_address, customer_id, is_dynamic, last_update)
  values
  (v_client_ip, t_pool.id, v_mac_addr, t_customer.baseaccount_ptr_id, true, now())
  returning id, ip_address, pool_id, lease_time, mac_address, customer_id, is_dynamic
  into t_lease;

  return t_lease;
END;
$$;
