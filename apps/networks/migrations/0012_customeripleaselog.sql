CREATE OR REPLACE FUNCTION networks_ip_lease_log_fn()
  RETURNS TRIGGER AS
$$
BEGIN
  insert into networks_ip_lease_log(customer_id, ip_address, lease_time, last_update, mac_address, is_dynamic, event_time)
  values (NEW.customer_id, NEW.ip_address, NEW.lease_time, NEW.last_update, NEW.mac_address, NEW.is_dynamic, now());
  RETURN NEW;
END
$$
LANGUAGE plpgsql;


CREATE TRIGGER networks_ip_lease_log_trigger
  AFTER INSERT
  ON networks_ip_leases
  FOR EACH ROW
EXECUTE PROCEDURE networks_ip_lease_log_fn();
