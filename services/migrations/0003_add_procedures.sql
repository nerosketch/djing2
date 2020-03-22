---
--- Find customer service credentials by device SWITCH credentials.
--- ATTENTION: If you pass null into v_dev_port, then it returns first available
--- user on the found switch, and he will get service WITHOUT pay
---
DROP FUNCTION IF EXISTS find_customer_service_by_device_switch_credentials(macaddr,smallint);
CREATE OR REPLACE FUNCTION find_customer_service_by_device_switch_credentials(
  v_dev_mac macaddr,
  v_dev_port smallint
)
  RETURNS services
  LANGUAGE plpgsql
AS $$
DECLARE
  t_res_row RECORD;
BEGIN

  if v_dev_port > 0 and v_dev_mac is not null then
    select into t_res_row
      services.*
    from services
      left join customer_service on (customer_service.service_id = services.id)
      left join customers on (customers.current_service_id = customer_service.id)
      left join device on (customers.device_id = device.id)
      left join device_port on (device_port.device_id = device.id)
    where device.mac_addr = v_dev_mac and device_port.num = v_dev_port
    limit 1;
    return t_res_row;
  end if;

end
$$;

---
--- Find customer service credentials by device ONU credentials(mac address).
--- ATTENTION: If you apply this function to switch or other device with multiple ports,
--- then it returns first available user on the found switch, and he will get service WITHOUT pay
---
DROP FUNCTION IF EXISTS find_customer_service_by_device_onu_credentials(macaddr);
CREATE OR REPLACE FUNCTION find_customer_service_by_device_onu_credentials(
  v_dev_mac macaddr
)
  RETURNS services
  LANGUAGE plpgsql
AS $$
DECLARE
  t_res_row RECORD;
BEGIN

  if v_dev_mac is not null then
    select into t_res_row
      services.*
    from services
      left join customer_service on (customer_service.service_id = services.id)
      left join customers on (customers.current_service_id = customer_service.id)
      left join device on (customers.device_id = device.id)
    where device.mac_addr = v_dev_mac
    limit 1;
    return t_res_row;
  end if;

end
$$;