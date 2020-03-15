--
-- Create model CustomerIpLease
--
CREATE TABLE "networks_ip_leases"
(
  "id"           bigserial                   NOT NULL PRIMARY KEY,
  "ip_address"   inet                        NOT NULL UNIQUE,
  "pool_id"      integer                     NOT NULL,
  "lease_time"   timestamp without time zone NOT NULL DEFAULT 'now' :: timestamp(0),
  "customer_mac" macaddr                     NULL,
  "customer_id"  integer                     NOT NULL,
  "is_dynamic"   boolean                     NOT NULL DEFAULT FALSE
);
CREATE INDEX "networks_ip_leases_pool_id"
  ON "networks_ip_leases"
  USING btree ("pool_id");
ALTER TABLE "networks_ip_leases" ADD CONSTRAINT "networks_ip_leases_ip_address_customer_mac__customer_uniq" UNIQUE ("ip_address", "customer_mac", "customer_id");

--
-- Create model NetworkIpPool
--
CREATE TABLE "networks_ip_pool"
(
  "id"          bigserial   NOT NULL PRIMARY KEY,
  "network"     inet        NOT NULL UNIQUE,
  --   "net_mask"    smallint    NOT NULL CHECK ("net_mask" >= 0),
  "kind"        smallint    NOT NULL CHECK ("kind" >= 0),
  "description" varchar(64) NOT NULL,
  "ip_start"    inet        NOT NULL,
  "ip_end"      inet        NOT NULL,
  "vlan_if_id"  integer     NULL,
  "gateway"     inet        NOT NULL,
  "lease_time"  INTEGER    NOT NULL CHECK ("lease_time" >= 0) DEFAULT 3600
);
CREATE INDEX "networks_ip_pool_vlan_if_id"
  ON "networks_ip_pool"
  USING btree ("vlan_if_id");
ALTER TABLE "networks_ip_pool"
  ADD CONSTRAINT "networks_ip_pool_vlan_if_id_networks_vlan_id" FOREIGN KEY ("vlan_if_id") REFERENCES "networks_vlan" ("id")
  DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "networks_ip_leases"
  ADD CONSTRAINT "networks_ip_leases_pool_id_fk_networks_ip_pool_id" FOREIGN KEY ("pool_id") REFERENCES "networks_ip_pool" ("id")
  DEFERRABLE INITIALLY DEFERRED;

--
-- Copy old network table to new ip_pool table
--
INSERT INTO networks_ip_pool ("network", "kind", "description", "ip_start", "ip_end", "vlan_if_id", "gateway", "lease_time")
  SELECT
    "network",
    "kind",
    "description",
    "ip_start",
    "ip_end",
    "vlan_if_id",
    NETWORK("network") :: inet + 1,
    86700
  FROM networks_network;


--
-- Function that find free ip for new lease
--
--
-- Пробуем найти свободный ip из пула адресов. Если не находит то возвращается null.
-- Берём диапазон ip из пула от networks_ip_pool.ip_start до networks_ip_pool.ip_end
-- параллельно берём записи из networks_ip_leases о занятых ip, берём их отсортированными
-- по ip_address. И, по идее, при итерации ip совпадают, когда сгенерированный ip из подести
-- пула меньше ip из занятых то это значит что ip из пула уже удалился, и мы нашли свободный.
--
CREATE OR REPLACE FUNCTION find_new_ip_pool_lease(
  v_pool_id integer
)
  RETURNS inet
LANGUAGE plpgsql
AS $$
DECLARE
  t_ip_iter        inet;
  t_ip_lease       inet;
  t_net_ippool_tbl RECORD;
  t_leases_curs    REFCURSOR;
BEGIN

  -- Ищем текущий пул
  select
    network,
    ip_start,
    ip_end,
    lease_time
  into t_net_ippool_tbl
  from networks_ip_pool
  where id = v_pool_id
  limit 1;

  if not FOUND
  then
    return null;
  end if;

  -- Берём курсор по существующим лизам для текущего пула
  -- и где лизы ещё не просрочены
  open t_leases_curs no scroll for select ip_address
                                   from networks_ip_leases
                                   where
                                     pool_id = v_pool_id and
                                     (lease_time + make_interval(secs => t_net_ippool_tbl.lease_time)) >
                                     'now' :: timestamp(0) and
                                     ip_address >= t_net_ippool_tbl.ip_start and
                                     ip_address <<= t_net_ippool_tbl.network
                                   order by ip_address;

  t_ip_iter := t_net_ippool_tbl.ip_start;

  while true loop

    fetch t_leases_curs into t_ip_lease;
    if not FOUND
    then
      -- не нашли лизу, возвращаем текущий ip из подсети
      --       raise notice 'lease not found, return current ip %', t_ip_iter;
      return t_ip_iter;
    end if;

    -- если текущий ip больше или равен максимальному допустимому ip то всё, не нашли свободный ip
    if t_ip_iter >= t_net_ippool_tbl.ip_end
    then
      --       raise notice 'current ip is more than max allowable % -%, end', t_ip_iter, t_net_ippool_tbl.ip_end;
      return null;
    end if;

    -- если текущий ip меньше начального допустимого ip
    if t_ip_iter < t_net_ippool_tbl.ip_start
    then
      --       raise notice 'current ip is less than minimum. go next % - %', t_ip_iter, t_net_ippool_tbl.ip_start;
      t_ip_iter := t_ip_iter + 1;
      continue;
    end if;

    if t_ip_iter = t_ip_lease
    then
      -- сгенерированный ip и занятый из лизов совпадают, дальше
      --       raise notice 'current ip and lease ip is exact, next % - %', t_ip_iter, t_ip_lease;
      t_ip_iter := t_ip_iter + 1;
      continue;
    end if;

    -- Если текущий ip меньше текущего из пула то значит освободился
    -- один из ip и пропал из таблицы занятых ip, выдаём его
    if t_ip_iter < t_ip_lease
    then
      --       raise notice 'current ip is less than ip lease, got it %', t_ip_iter;
      return t_ip_iter;
    end if;

    raise exception 'End loop, unexpected!';
  end loop;

  return null;
END
$$;