--
-- Find customer service by device mac and device port, if device supports
-- port allocation to customer
--
CREATE OR REPLACE FUNCTION find_customer_service_by_device_credentials(v_dev_mac  macaddr,
                                                                       v_dev_port smallint)
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

  if v_dev_mac is not null and v_dev_port > 0
  then
    return query with tcust (b_id, s_id) as (
        select
          baseaccount_ptr_id,
          current_service_id
        from find_customer_by_device_credentials(v_dev_mac, v_dev_port)
        limit 1
    )
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
      left join base_accounts on (base_accounts.id = (select b_id
                                                      from tcust))
      left join services on (services.id = customer_service.service_id)
    where base_accounts.is_active
          and customer_service.id = (select s_id
                                     from tcust)
    limit 1;
  end if;
  return next;

end;
$$;
