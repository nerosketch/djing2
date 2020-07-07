--
-- Удаляем те динамические аренды которые были выделены на абонентов, а потом подсети
-- были убраны из тех групп где были абоненты, а аренды из тех подсетей остались.
-- Получается что эти аренды(ip адреса) висят в учётке, хотя по сути не используются.
--
delete from networks_ip_leases where id in (
select nil.id from networks_ip_leases nil
left join customers on (nil.customer_id = customers.baseaccount_ptr_id)
left join networks_ip_pool nip on (nil.pool_id = nip.id)

  left join networks_ippool_groups nipg on (nipg.networkippool_id = nip.id)
where nil.is_dynamic and customers.group_id not in (
  select group_id from networks_ippool_groups
  where networkippool_id = nip.id
));
