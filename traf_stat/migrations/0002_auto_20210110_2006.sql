---
--- Prepare customer_id field while insert row in cache
---


CREATE OR REPLACE FUNCTION traffic_prepare_customer_id_by_ip()
  RETURNS TRIGGER AS
$func$
DECLARE
  t_customer_id integer;
BEGIN
  select customer_id
  into t_customer_id
  from networks_ip_leases
  where ip_address = NEW.ip_addr;

  if not FOUND
  then
    return NULL;
  end if;

  NEW."customer_id" := t_customer_id;
  RETURN NEW;
END
$func$
LANGUAGE plpgsql;

CREATE TRIGGER traffic_prepare_customer_id_by_ip_trigger
  BEFORE INSERT
  ON traf_cache
  FOR EACH ROW
EXECUTE PROCEDURE traffic_prepare_customer_id_by_ip();

-- traf_cache changes frequently
ALTER TABLE traf_cache SET UNLOGGED;

CREATE INDEX traf_cache_ip_addr_index ON traf_cache USING GIST(ip_addr inet_ops);
