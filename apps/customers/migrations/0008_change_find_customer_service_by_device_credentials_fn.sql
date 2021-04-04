--
-- Find customer service by device mac and device port, if device supports
-- port allocation to customer
--
DROP FUNCTION IF EXISTS find_customer_service_by_device_credentials( macaddr, smallint);
CREATE OR REPLACE FUNCTION find_customer_service_by_device_credentials(v_customer_id integer,
                                                                       v_current_service_id integer)
  RETURNS TABLE(
    id          integer,
    service_id  integer,
    speed_in    double precision,
    speed_out   double precision,
    cost        double precision,
    calc_type   smallint,
    is_admin    boolean,
    speed_burst double precision,
    start_time  timestamptz,
    deadline    timestamptz
  )
LANGUAGE plpgsql
AS $$
BEGIN

  if v_customer_id > 0 and v_current_service_id > 0
  then
    return query
    select
      customer_service.id,
      services.id,
      services.speed_in,
      services.speed_out,
      services.cost,
      services.calc_type,
      services.is_admin,
      services.speed_burst,
      customer_service.start_time,
      customer_service.deadline
    from customer_service
      left join base_accounts on (base_accounts.id = v_customer_id)
      left join services on (services.id = customer_service.service_id)
    where base_accounts.is_active
          and customer_service.id = v_current_service_id
    limit 1;
  end if;
  return next;

end;
$$;