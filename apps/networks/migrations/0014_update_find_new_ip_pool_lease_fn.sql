--
-- Function that find ip for customer.
--
--
-- Пробуем найти свободный ip из пула адресов. Если не находит то возвращается null.
-- Берём диапазон ip из пула от networks_ip_pool.ip_start до networks_ip_pool.ip_end
-- параллельно берём записи из networks_ip_leases о занятых ip, берём их отсортированными
-- по ip_address. И, по идее, при итерации ip совпадают, когда сгенерированный ip из подести
-- пула меньше ip из занятых то это значит что ip из пула это свободный ip.
--
DROP FUNCTION IF EXISTS find_new_ip_pool_lease( integer, boolean, character varying );
CREATE OR REPLACE FUNCTION find_new_ip_pool_lease(
  v_pool_id    integer,
  v_is_dynamic boolean,
  v_vid        smallint,
  v_pool_kind  smallint
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

  -- Ищем текущий пул, если указан v_vid то учитываем его
  if v_vid is not null and v_vid > 1
  then
    select
      nip.id,
      nip.network,
      nip.ip_start,
      nip.ip_end
    into t_net_ippool_tbl
    from networks_ip_pool nip
      left join networks_vlan nv on nip.vlan_if_id = nv.id
    where nip.id = v_pool_id
      and nip.is_dynamic = v_is_dynamic
      and nv.vid = v_vid
      and nip.kind = v_pool_kind
    limit 1;
  else
    select
      id,
      network,
      ip_start,
      ip_end
    into t_net_ippool_tbl
    from networks_ip_pool nip
    where id = v_pool_id
      and is_dynamic = v_is_dynamic
      and nip.kind = v_pool_kind
    limit 1;
  end if;


  if not FOUND
  then
    return null;
  end if;

  -- Берём курсор по существующим лизам для текущего пула
  -- и где лизы ещё не просрочены
  open t_leases_curs no scroll for select ip_address
                                   from networks_ip_leases
                                   where
                                     pool_id = t_net_ippool_tbl.id and
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


CREATE OR REPLACE FUNCTION networks_ip_lease_log_fn()
  RETURNS TRIGGER AS
$$
DECLARE
  now_time timestamptz;
BEGIN
  if NEW.customer_id is null then
    RETURN NEW;
  end if;

  now_time := now();

  update networks_ip_lease_log set end_use_time = now_time
  where ip_address = NEW.ip_address and (
      OLD is null or customer_id = OLD.customer_id);

  insert into networks_ip_lease_log(customer_id, ip_address, lease_time,
                                    last_update, mac_address, is_dynamic, event_time)
  values (NEW.customer_id, NEW.ip_address, NEW.lease_time,
          NEW.last_update, NEW.mac_address, NEW.is_dynamic, now_time);

  RETURN NEW;
END
$$
LANGUAGE plpgsql;
