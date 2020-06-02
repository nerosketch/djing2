--
-- Fetch customers service and network credentials by gateway.
--
DROP FUNCTION IF EXISTS fetch_customers_srvnet_credentials_by_gw;
CREATE OR REPLACE FUNCTION fetch_customers_srvnet_credentials_by_gw(
  v_gw_id integer
)
  RETURNS TABLE(
    ip_address  inet,
    speed_in    double precision,
    speed_out   double precision
  )
LANGUAGE plpgsql
AS $$
BEGIN

  if v_gw_id is not null
  then
    return query select
                   nil.ip_address,
                   services.speed_in,
                   services.speed_out
                 from customers
                   left join networks_ip_leases nil on (nil.customer_id = customers.baseaccount_ptr_id)
                   left join customer_service on (customer_service.id = customers.current_service_id)
                   left join services on (services.id = customer_service.service_id)

                   left join base_accounts on (base_accounts.id = customers.baseaccount_ptr_id)
                 where customers.gateway_id = v_gw_id and base_accounts.is_active and customers.current_service_id is not null and nil.ip_address is not null;
  end if;

  return next;

end
$$;
