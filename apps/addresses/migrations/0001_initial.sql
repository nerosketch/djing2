-- Copy groups into addresses
INSERT INTO addresses (id, address_type, fias_address_level, fias_address_type, title)
SELECT id, 4, 0, 0, title from groups;
SELECT setval('addresses_id_seq', (SELECT max(id) as mid from addresses));

-- Attach customers to addresses
-- UPDATE customers SET address_id = group_id;

-- Copy streets to addresses
INSERT INTO addresses (parent_addr_id, address_type, fias_address_level, fias_address_type, title)
SELECT group_id, 8, 0, 0, name from customer_street;
