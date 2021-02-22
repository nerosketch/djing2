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
                                                  v_customer_id integer,
                                                  v_customer_group integer,
                                                  v_is_dynamic boolean,
                                                  v_vid smallint,
                                                  v_pool_kind smallint)
  RETURNS FetchSubscriberLeaseReturnType
  LANGUAGE plpgsql
AS
$$
DECLARE
  t_lease    FetchSubscriberLeaseReturnType;
  t_ip       inet;
  t_net      record;
BEGIN
  -- check if lease is exists
  -- if exists then return it
  -- else allocate new lease for customer
  --   and return it

  -- Find leases by customer and mac
  SELECT nil.id, nil.ip_address, nil.pool_id, nil.lease_time, nil.mac_address, nil.customer_id, nil.is_dynamic, false
         INTO t_lease
  FROM networks_ip_leases nil
  where (v_customer_id is null or nil.customer_id = v_customer_id)
    and (not v_is_dynamic or nil.mac_address = v_mac_addr)
    and nil.is_dynamic = v_is_dynamic
  order by nil.id desc
  limit 1;

  if FOUND
  then
    -- Update `last_update` field in customer lease
    if v_customer_id is not null then
      perform update_customer_lease_last_update_time_field(
          v_customer_id,
          t_lease.ip_address);
    end if;
    -- And returning it
    return t_lease;
  end if;

  -- find pools for customer.
  -- fetched all pools that is available in customers group.
  for t_net in select nip.id
               from networks_ip_pool nip
                 left join networks_ippool_groups nipg on nipg.networkippool_id = nip.id
               where (v_customer_group is null or nipg.group_id = v_customer_group)
                 and nip.kind = v_pool_kind
    group by nip.id
    loop

      -- Find new lease
      select *
             into t_ip
      from find_new_ip_pool_lease(
        t_net.id::integer,
        v_is_dynamic, v_vid,
        v_pool_kind
      );

      if t_ip is not null
      then

        -- lease found, attach to customer and return it
        insert into networks_ip_leases (ip_address, pool_id, mac_address, customer_id, is_dynamic, last_update)
        values
        (t_ip, t_net.id, v_mac_addr, v_customer_id, v_is_dynamic, now())
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



--
-- Creating or updating radius session during accounting.
--
DROP FUNCTION create_or_update_radius_session(
  uuid, inet, macaddr, smallint, integer,
  varchar(32), integer, integer, integer,
  integer, boolean);
