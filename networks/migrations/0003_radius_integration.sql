--
-- Create model CustomerIpLease
--
CREATE TABLE "networks_ip_leases"
(
  "id"           bigserial                   NOT NULL PRIMARY KEY,
  "ip_address"   inet                        NOT NULL UNIQUE,
  "pool_id"      integer                     NOT NULL,
  "lease_time"   timestamp without time zone NOT NULL DEFAULT now()::timestamp(0),
  "mac_address"  macaddr                     NULL,
  "customer_id"  integer                     NOT NULL,
  "is_dynamic"   boolean                     NOT NULL DEFAULT FALSE
);
CREATE INDEX "networks_ip_leases_pool_id"
  ON "networks_ip_leases"
  USING btree ("pool_id");
ALTER TABLE "networks_ip_leases" ADD CONSTRAINT "networks_ip_leases_ip_address_mac_address__customer_uniq" UNIQUE ("ip_address", "mac_address", "pool_id", "customer_id");

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
  "gateway"     inet        NOT NULL
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
INSERT INTO networks_ip_pool ("id", "network", "kind", "description", "ip_start", "ip_end", "vlan_if_id", "gateway")
  SELECT
    "id",
    "network",
    "kind",
    "description",
    "ip_start",
    "ip_end",
    "vlan_if_id",
    NETWORK("network") :: inet + 1
  FROM networks_network;


--
-- Copy old ip address from customer accounts to ip leases
--
INSERT INTO networks_ip_leases ("ip_address", "pool_id", "lease_time", "customer_id", "is_dynamic")
  SELECT
    customers.ip_address,
    networks_ip_pool.id,
    (timestamp without time zone '1000-01-01 00:00:00'),
    customers.baseaccount_ptr_id,
    customers.is_dynamic_ip
  FROM customers
  LEFT JOIN networks_ip_pool ON (customers.ip_address << networks_ip_pool.network)
  WHERE customers.ip_address IS NOT NULL AND networks_ip_pool.id IS NOT NULL;



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
    ip_end
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
                                     ip_address >= t_net_ippool_tbl.ip_start and
                                     ip_address <<= t_net_ippool_tbl.network
                                   order by ip_address;

  t_ip_iter := t_net_ippool_tbl.ip_start;

  while true loop

    fetch t_leases_curs into t_ip_lease;
    if not FOUND
    then
      -- не нашли лизу, возвращаем текущий ip из подсети
      -- raise notice 'lease not found, return current ip %', t_ip_iter;
      return t_ip_iter;
    end if;

    -- если текущий ip больше или равен максимальному допустимому ip то всё, не нашли свободный ip
    if t_ip_iter >= t_net_ippool_tbl.ip_end
    then
      -- raise notice 'current ip is more than max allowable % -%, end', t_ip_iter, t_net_ippool_tbl.ip_end;
      return null;
    end if;

    -- если текущий ip меньше начального допустимого ip
    if t_ip_iter < t_net_ippool_tbl.ip_start
    then
      -- raise notice 'current ip is less than minimum. go next % - %', t_ip_iter, t_net_ippool_tbl.ip_start;
      t_ip_iter := t_ip_iter + 1;
      continue;
    end if;

    if t_ip_iter = t_ip_lease
    then
      -- сгенерированный ip и занятый из лизов совпадают, дальше
      -- raise notice 'current ip and lease ip is exact, next % - %', t_ip_iter, t_ip_lease;
      t_ip_iter := t_ip_iter + 1;
      continue;
    end if;

    -- Если текущий ip меньше текущего из пула то значит освободился
    -- один из ip и пропал из таблицы занятых ip, выдаём его
    if t_ip_iter < t_ip_lease
    then
      -- raise notice 'current ip is less than ip lease, got it %', t_ip_iter;
      return t_ip_iter;
    end if;

    raise exception 'End loop, unexpected!';
  end loop;

  return null;
END
$$;

--
-- Add field groups to networkippool
--
CREATE TABLE "networks_ippool_groups" ("id" serial NOT NULL PRIMARY KEY, "networkippool_id" integer NOT NULL, "group_id" integer NOT NULL);

-- Copy old network group relations into new
INSERT INTO networks_ippool_groups ("networkippool_id", "group_id")
  SELECT
    "networkmodel_id",
    "group_id"
  FROM networks_network_groups;


--
-- fetch lease from dynamic subscriber
--
CREATE OR REPLACE FUNCTION fetch_subscriber_dynamic_lease(
  v_mac_addr macaddr,
  v_dev_mac macaddr,
  v_dev_port smallint)
  RETURNS networks_ip_leases
  LANGUAGE plpgsql
AS
$$
DECLARE
  t_lease       record;
  t_ip          inet;
  t_net         record;
  t_customer_id integer;
BEGIN
  -- check if lease is exists
  -- if exists then return it
  -- else allocate new lease for customer
  --   and return it

  -- find customer by device mac
  select cs.baseaccount_ptr_id into t_customer_id from customers cs
  left join device dv on (dv.id = cs.device_id)
  left join device_port dp on (cs.dev_port_id = dp.id)
  left join device_dev_type_is_use_dev_port ddtiudptiu on (ddtiudptiu.dev_type = dv.dev_type)
  where dv.mac_addr = v_dev_mac
    and ((not ddtiudptiu.is_use_dev_port) or dp.num = v_dev_port)
    limit 1;
  if not FOUND then
    raise exception 'Customer with device mac=% not found', v_dev_mac;
    return t_lease;
  end if;

  -- Find leases by customer and mac, where pool of this lease in
  -- the same group as the subscriber
  SELECT networks_ip_leases.* INTO t_lease
  FROM networks_ip_leases
  left join customers on (customers.baseaccount_ptr_id = networks_ip_leases.customer_id)
  left join networks_ippool_groups on (networks_ippool_groups.networkippool_id = networks_ip_leases.pool_id)
  where networks_ip_leases.customer_id = t_customer_id
    and networks_ippool_groups.group_id = customers.group_id
    and networks_ip_leases.is_dynamic
  limit 1;
  if FOUND then
    -- return it
    return t_lease;
  end if;

  -- raise notice 'not found lease';

  -- find pools for customer.
  -- fetched all pools that is available in customers group.
  for t_net in select networks_ippool_groups.networkippool_id as pool_id from networks_ippool_groups
  left join customers on (customers.group_id = networks_ippool_groups.group_id)
  where customers.baseaccount_ptr_id=t_customer_id loop

    -- raise notice 'search in pool %', t_net.pool_id;

    -- Find new lease
    select * into t_ip from find_new_ip_pool_lease(t_net.pool_id);
    -- raise notice 'from find_new_ip_pool_lease %', t_ip;
    if t_ip is not null then

      -- raise notice 'found new lease %', t_ip;

      -- lease found, attach to customer and return it
      insert into networks_ip_leases(ip_address, pool_id, mac_address, customer_id, is_dynamic) values
      (t_ip, t_net.pool_id, v_mac_addr, t_customer_id, true)
      returning * into t_lease;
      return t_lease;
    end if;

    -- new lease is not found, then try next pool
  end loop;

  -- leases from all pools is not found, nothing to return
  return t_lease;
END;
$$;
