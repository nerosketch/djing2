DROP TYPE if exists FetchSubscriberLeaseReturnType CASCADE;
CREATE TYPE FetchSubscriberLeaseReturnType AS (
  id bigint,
  ip_address inet,
  pool_id integer,
  lease_time timestamp without time zone,
  mac_address macaddr,
  customer_id integer,
  is_dynamic boolean,
  is_assigned boolean
);


--
-- Fetch lease from subscriber.
-- If v_is_dynamic is False then v_mac_addr(users mac) is
-- ignored during the search by leases
--
DROP FUNCTION IF EXISTS fetch_subscriber_lease(macaddr,macaddr,smallint,boolean,character varying);
CREATE OR REPLACE FUNCTION fetch_subscriber_lease(v_mac_addr macaddr,
                                                  v_dev_mac macaddr,
                                                  v_dev_port smallint,
                                                  v_is_dynamic boolean,
                                                  v_tag varchar(32))
  RETURNS FetchSubscriberLeaseReturnType
  LANGUAGE plpgsql
AS
$$
DECLARE
  t_lease    FetchSubscriberLeaseReturnType;
  t_ip       inet;
  t_net      record;
  t_customer record;
BEGIN
  -- check if lease is exists
  -- if exists then return it
  -- else allocate new lease for customer
  --   and return it

  -- find customer by device mac
  select *
         into t_customer
  from find_customer_by_device_credentials(v_dev_mac, v_dev_port);
  if not FOUND
  then
    raise exception 'Customer with device mac=% not found', v_dev_mac;
    return null;
  end if;

  -- Find leases by customer and mac, where pool of this lease in
  -- the same group as the subscriber
  SELECT nil.id, nil.ip_address, nil.pool_id, nil.lease_time, nil.mac_address, nil.customer_id, nil.is_dynamic, false
         INTO t_lease
  FROM networks_ip_leases nil
         left join customers cst on cst.baseaccount_ptr_id = nil.customer_id
         left join networks_ippool_groups nipg on nipg.networkippool_id = nil.pool_id
       --     left join networks_ip_pool nip on nil.pool_id = nip.id
  where nil.customer_id = t_customer.baseaccount_ptr_id
    and (not v_is_dynamic or nil.mac_address = v_mac_addr)
    and nipg.group_id = cst.group_id
    and nil.is_dynamic = v_is_dynamic
    --         and nip.pool_tag is not distinct from v_tag
  order by nil.id desc
  limit 1;

  if FOUND
  then
    -- return it
    return t_lease;
  end if;

  -- raise notice 'not found lease';

  -- find pools for customer.
  -- fetched all pools that is available in customers group.
  for t_net in select nipg.networkippool_id as pool_id
               from networks_ippool_groups nipg
                      left join customers on customers.group_id = nipg.group_id
               where customers.baseaccount_ptr_id = t_customer.baseaccount_ptr_id
                 for update skip locked
    loop

    -- raise notice 'search in pool %', t_net.pool_id;

      -- Find new lease
      select *
             into t_ip
      from find_new_ip_pool_lease(t_net.pool_id, v_is_dynamic, v_tag);
      -- raise notice 'from find_new_ip_pool_lease %', t_ip;
      if t_ip is not null
      then

        -- raise notice 'found new lease %', t_ip;

        -- lease found, attach to customer and return it
        insert into networks_ip_leases (ip_address, pool_id, mac_address, customer_id, is_dynamic)
        values
        (t_ip, t_net.pool_id, v_mac_addr, t_customer.baseaccount_ptr_id, v_is_dynamic)
        returning id, ip_address, pool_id, lease_time, mac_address, customer_id, is_dynamic, true
          into t_lease;
        return t_lease;
      end if;

      -- new lease is not found, then try next pool
    end loop;

  -- leases from all pools is not found, nothing to return
  return null;
END;
$$;
