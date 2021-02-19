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
                                                  v_vid smallint)
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
  end if;

  -- Find leases by customer and mac
  SELECT nil.id, nil.ip_address, nil.pool_id, nil.lease_time, nil.mac_address, nil.customer_id, nil.is_dynamic, false
         INTO t_lease
  FROM networks_ip_leases nil
  where nil.customer_id = t_customer.baseaccount_ptr_id
    and (not v_is_dynamic or nil.mac_address = v_mac_addr)
    and nil.is_dynamic = v_is_dynamic
  order by nil.id desc
  limit 1;

  if FOUND
  then
    -- Update `last_update` field in customer lease
    perform update_customer_lease_last_update_time_field(
        t_customer.baseaccount_ptr_id,
        t_lease.ip_address);
    -- And returning it
    return t_lease;
  end if;

  -- raise notice 'not found existed lease';

  -- find pools for customer.
  -- fetched all pools that is available in customers group.
  for t_net in select nipg.networkippool_id
               from networks_ippool_groups nipg
               where nipg.group_id = t_customer.group_id
    loop

      -- raise notice 'search in pool %', t_net.pool_id;

      -- Find new lease
      select *
             into t_ip
      from find_new_ip_pool_lease(t_net.networkippool_id, v_is_dynamic, v_vid);
      -- raise notice 'from find_new_ip_pool_lease %', t_ip;
      if t_ip is not null
      then

        -- raise notice 'found new lease %', t_ip;

        -- lease found, attach to customer and return it
        insert into networks_ip_leases (ip_address, pool_id, mac_address, customer_id, is_dynamic, last_update)
        values
        (t_ip, t_net.networkippool_id, v_mac_addr, t_customer.baseaccount_ptr_id, v_is_dynamic, now())
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
CREATE OR REPLACE FUNCTION create_or_update_radius_session(
  v_sess_id        uuid,
  v_ip_addr        inet,
  v_dev_mac        macaddr,
  v_dev_port       smallint,
  v_sess_time_secs integer,
  v_uname          character varying,
  v_inp_oct        integer,
  v_out_oct        integer,
  v_in_pkt         integer,
  v_out_pkt        integer,
  v_is_stop        boolean
)
  RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
  upd_count integer;
BEGIN

  -- find existing session by session id
  -- if found then update existing session
  -- if act-type is stop then finish session
  update user_session
  set last_event_time = now(), radius_username = v_uname, framed_ip_addr = v_ip_addr,
    session_duration  = make_interval(secs := v_sess_time_secs), input_octets = v_inp_oct,
    output_octets     = v_out_oct,
    input_packets     = v_in_pkt, output_packets = v_out_pkt, closed = v_is_stop
  where session_id = v_sess_id;

  GET DIAGNOSTICS upd_count = ROW_COUNT;

  if upd_count = 0
  then
    -- if not found then create new session

    raise notice 'create new session';

    insert into user_session (assign_time, last_event_time, radius_username,
                              framed_ip_addr, session_id, session_duration,
                              input_octets, output_octets, input_packets,
                              output_packets, closed, customer_id)
      select
        now(),
        now(),
        v_uname,
        v_ip_addr,
        v_sess_id,
        make_interval(secs := 0),
        0, 0, 0, 0,
        false,
        baseaccount_ptr_id
      from
          find_customer_by_device_credentials(v_dev_mac, v_dev_port)
      limit 1;

    GET DIAGNOSTICS upd_count = ROW_COUNT;
    return upd_count > 0;
  end if;

  return false;

END;
$$;
