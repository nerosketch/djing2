--
-- Creating or updating radius session during accounting.
--


CREATE OR REPLACE FUNCTION create_or_update_radius_session(
  v_sess_id        uuid,
  v_ip_addr        inet,
  v_dev_mac        macaddr,
  v_dev_port       smallint,
  v_sess_time_secs integer,
  v_uname          varchar(32),
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
        0,
        0,
        0,
        0,
        false,
        baseaccount_ptr_id
      from
          find_customer_by_device_credentials(v_dev_mac, v_dev_port)
      limit 1;

    GET DIAGNOSTICS upd_count = ROW_COUNT;
    if upd_count > 0
    then
      return true;
    else
      return false;
    end if;
  end if;

  return false;

END;
$$;

CREATE UNIQUE INDEX usrses_uid_uni_idx
  ON user_session (session_id)
  WHERE session_id IS NOT NULL;
