CREATE OR REPLACE VIEW get_streets_as_addr_objects AS
  SELECT cs.id AS street_id, sa.id AS parent_ao_id, sa.ao_type AS parent_ao_type, cs.name AS street_name
  FROM locality_street cs
    INNER JOIN sorm_address_groups sag ON (sag.group_id = cs.locality_id)
    INNER JOIN sorm_address sa ON (sa.id = sag.fiasrecursiveaddressmodel_id)
  ORDER BY sa.ao_level;
