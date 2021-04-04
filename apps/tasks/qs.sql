SELECT
  task.id                         AS id,
  COUNT(task_extra_comments.id)   as comment_count,
  base_accounts_author.username   as author_uname,
  base_accounts_author.fio        as author_fio,
  task.*,
  groups_customer.title           as groups_customer_title,
  customer_street.name            as customer_street_name,
  customers.house,
  base_accounts_customer.username as customer_username,
  base_accounts_customer.fio      as customer_fio,
  customers.group_id
FROM task
  LEFT JOIN base_accounts AS base_accounts_author ON (task.author_id = base_accounts_author.id)
  LEFT JOIN task_extra_comments ON (task.id = task_extra_comments.task_id)
  LEFT JOIN customers ON (task.customer_id = customers.baseaccount_ptr_id)
  LEFT JOIN base_accounts AS base_accounts_customer ON (task.customer_id = base_accounts_customer.id)
  LEFT JOIN groups AS groups_customer ON (groups_customer.id = customers.group_id)
  LEFT JOIN customer_street ON (customer_street.group_id = customers.street_id)
WHERE base_accounts_customer.username = '19000'
GROUP BY task.id, base_accounts_author.id, groups_customer.id, customer_street.id, customers.baseaccount_ptr_id,
  base_accounts_customer.id
LIMIT 150;
