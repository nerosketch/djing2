--
-- Find customer by device mac and device port, if device supports
-- port allocation to customer
--
CREATE OR REPLACE FUNCTION find_customer_service_by_device_credentials(v_dev_mac macaddr,
                                                                       v_dev_port smallint)
  RETURNS SETOF services AS
$$

with tcust (b_id, s_id) as (
  select baseaccount_ptr_id, current_service_id
  from find_customer_by_device_credentials(v_dev_mac, v_dev_port)
  limit 1
)
select
  services.*
from services
       left join base_accounts on (base_accounts.id = (select b_id from tcust))
       left join customer_service on (customer_service.service_id = services.id)
where base_accounts.is_active
  and customer_service.id = (select s_id from tcust)
limit 1;

$$
  LANGUAGE sql;
