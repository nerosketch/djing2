-- Copy groups into addresses
INSERT INTO addresses (id, address_type, title) SELECT id, 4, title from groups;

-- Attach customers to addresses
UPDATE customers SET address_id = group_id;
