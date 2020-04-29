--
-- Find customer service credentials by ip address.
--
DROP FUNCTION IF EXISTS find_customer_service_by_ip( inet );
CREATE OR REPLACE FUNCTION find_customer_service_by_ip(
  v_customer_ip inet
)
  RETURNS TABLE(
    id          integer,
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

  if v_customer_ip is not null
  then
    return query select
                   services.id,
                   services.speed_in,
                   services.speed_out,
                   services.cost,
                   services.calc_type,
                   services.is_admin,
                   services.speed_burst,
                   customer_service.start_time,
                   customer_service.deadline
                 from services
                   left join customer_service on (customer_service.service_id = services.id)
                   left join customers on (customers.current_service_id = customer_service.id)
                   left join networks_ip_leases nil on (nil.customer_id = customers.baseaccount_ptr_id)
                   left join base_accounts on (base_accounts.id = customers.baseaccount_ptr_id)
                 where nil.ip_address = v_customer_ip and base_accounts.is_active
                 limit 1;
  end if;

  return next;

end
$$;
