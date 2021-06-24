-- TODO: make it works
ALTER TABLE sorm_address_groups add CONSTRAINT
  sorm_address_groups_groupid_uniq UNIQUE (group_id);


CREATE OR REPLACE VIEW get_streets_as_addr_objects AS
  SELECT cs.id AS street_id, sa.id AS parent_ao_id, sa.ao_type AS parent_ao_type, cs.name AS street_name
  FROM customer_street cs
    INNER JOIN sorm_address_groups sag ON (sag.group_id = cs.group_id)
    INNER JOIN sorm_address sa ON (sa.id = sag.fiasrecursiveaddressmodel_id)
  ORDER BY sa.ao_level;
