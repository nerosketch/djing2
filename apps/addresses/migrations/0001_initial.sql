-- Copy groups into addresses
INSERT INTO addresses (id, address_type, title) SELECT id, 4, title from groups;
SELECT setval('addresses_id_seq', (SELECT max(id) as mid from addresses));

-- Attach customers to addresses
-- UPDATE customers SET address_id = group_id;

-- Copy streets to addresses
INSERT INTO addresses (parent_addr_id, address_type, title)
SELECT group_id, 8, name from customer_street;

--Attach customers to address streets
UPDATE customers SET address_id = adrs.id
from addresses adrs
left join customer_street cs on group_id = adrs.parent_addr_id
WHERE adrs.parent_addr_id = customers.group_id
  AND adrs.title = cs.name
  AND adrs.address_type = 8;
