--
-- Checks if customer with specified ip has permit to service
--
CREATE OR REPLACE FUNCTION find_service_permit(
  v_ip inet)
  RETURNS SETOF boolean AS
$$

  select exists(select customer_service.id
  from customer_service
--     left join customer_service on (customer_service.service_id = services.id)
    left join customers on (customers.current_service_id = customer_service.id)
    left join base_accounts on (base_accounts.id = customers.baseaccount_ptr_id)
    left join networks_ip_leases nil on (nil.customer_id = customers.baseaccount_ptr_id)
  where nil.ip_address = v_ip and base_accounts.is_active
  limit 1);

$$
LANGUAGE sql;
