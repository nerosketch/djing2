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
ALTER TABLE traf_cache SET UNLOGGED;

CREATE INDEX traf_cache_ip_addr_index ON traf_cache USING GIST(ip_addr inet_ops);


CREATE OR REPLACE FUNCTION traffic_copy_stat2archive()
  RETURNS TRIGGER AS
$$
DECLARE
  v_parition_name text;
BEGIN
  v_parition_name := to_char('traf_archive_YYYYMMID', NEW.event_time );
  execute 'INSERT INTO ' || v_parition_name || '(customer_id,event_time,octets,packets) VALUES ($1,$2,$3,$4);'
  using NEW.customer_id, NEW.event_time, NEW.octets, NEW.packets;
  return NULL;
END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER traffic_copy_stat2archive_trigger
  AFTER INSERT OR UPDATE
  ON traf_cache
  FOR EACH ROW
EXECUTE PROCEDURE traffic_copy_stat2archive();


ALTER TABLE traf_archive SET UNLOGGED ;

CREATE OR REPLACE FUNCTION create_traf_archive_partition_tbl()
  RETURNS SETOF boolean
LANGUAGE plpgsql
AS $$
BEGIN

  -- TODO: Генерировать имя партиции, и временной промежуток для данных в этой партиции,
  -- чтоб он был валиден этому имени партиции
  create unlogged table if not exists traf_archive_1(like traf_archive including all);
  alter table traf_archive_1 inherit traf_archive;
  alter table traf_archive_1 add constraint partition_check check (event_time > now() and event_time < now() - '7 days'::interval);
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
  v_parition_name := to_char('traf_archive_YYYYMMID', NEW.event_time );
  execute 'INSERT INTO ' || v_parition_name || ' VALUES ( ($1).* )' using NEW;
  return NULL;
END;
$$
LANGUAGE plpgsql;

CREATE TRIGGER traffic_copy_stat2partition_from_traf_archive_trigger
  BEFORE INSERT
  ON traf_archive
  FOR EACH ROW
  EXECUTE PROCEDURE traffic_copy_stat2partition_from_traf_archive();
