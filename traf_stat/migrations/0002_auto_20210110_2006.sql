---
--- Prepare customer_id field while insert row in cache
---


CREATE OR REPLACE FUNCTION traffic_prepare_customer_id_by_ip()
  RETURNS TRIGGER AS
$$
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
$$
LANGUAGE plpgsql;

CREATE TRIGGER traffic_prepare_customer_id_by_ip_trigger
  BEFORE INSERT
  ON traf_cache
  FOR EACH ROW
EXECUTE PROCEDURE traffic_prepare_customer_id_by_ip();

-- traf_cache changes frequently
ALTER TABLE IF EXISTS traf_cache SET UNLOGGED;
ALTER TABLE IF EXISTS traf_cache ALTER COLUMN event_time TYPE TIMESTAMP WITHOUT TIME ZONE;

CREATE INDEX traf_cache_ip_addr_index ON traf_cache USING GIST(ip_addr inet_ops);


CREATE OR REPLACE FUNCTION traffic_copy_stat2archive()
  RETURNS TRIGGER AS
$$
DECLARE
  v_parition_name text;
BEGIN
  v_parition_name := to_char(NEW.event_time, 'traf_archive_YYYYMMW');
  execute format('INSERT INTO %I(customer_id,event_time,octets,packets) VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING;', v_parition_name)
    using NEW.customer_id, NEW.event_time, NEW.octets, NEW.packets;
  return NULL;
END
$$
  LANGUAGE plpgsql;

CREATE TRIGGER traffic_copy_stat2archive_trigger
  AFTER INSERT OR UPDATE
  ON traf_cache
  FOR EACH ROW
EXECUTE PROCEDURE traffic_copy_stat2archive();


ALTER TABLE IF EXISTS traf_archive SET UNLOGGED ;
ALTER TABLE IF EXISTS traf_archive ALTER COLUMN event_time TYPE TIMESTAMP WITHOUT TIME ZONE;

CREATE OR REPLACE FUNCTION create_traf_archive_partition_tbl(whentime timestamp)
  RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
  v_next_week_start timestamp;
  v_next_week_end timestamp;
  v_parition_name text;
BEGIN

  v_parition_name := to_char(whentime, 'traf_archive_YYYYMMW');
  if exists(
    select from information_schema.tables
    where table_schema = 'public'
    and table_name = v_parition_name
  ) then
      return false;
  end if;

  v_next_week_start := date_trunc('week', whentime);
  v_next_week_end := v_next_week_start + '1 week'::interval - '1 sec'::interval;

  execute 'create unlogged table if not exists ' || v_parition_name || '(like traf_archive including all)';
  execute 'alter table ' || v_parition_name || ' inherit traf_archive';
  execute format('alter table %I add constraint partition_check check (event_time >= ''%s'' and event_time < ''%s'')',
    v_parition_name,
    v_next_week_start,
    v_next_week_end);

  return true;
END
$$;

-- https://habr.com/ru/post/273933/
-- TODO: создавать партиции с подходящими именами


CREATE OR REPLACE FUNCTION traffic_copy_stat2partition_from_traf_archive()
  RETURNS TRIGGER AS
$$
DECLARE
  v_parition_name text;
BEGIN
  v_parition_name := to_char(NEW.event_time, 'traf_archive_YYYYMMW');
  execute 'INSERT INTO ' || v_parition_name || ' VALUES ( ($1).* ) ON CONFLICT DO NOTHING' using NEW;
  return NULL;
END
$$
LANGUAGE plpgsql;

CREATE TRIGGER traffic_copy_stat2partition_from_traf_archive_trigger
  BEFORE INSERT
  ON traf_archive
  FOR EACH ROW
  EXECUTE PROCEDURE traffic_copy_stat2partition_from_traf_archive();
