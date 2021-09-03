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

  return true;

END;
$$;

CREATE UNIQUE INDEX usrses_uid_uni_idx
  ON user_session (session_id)
  WHERE session_id IS NOT NULL;
