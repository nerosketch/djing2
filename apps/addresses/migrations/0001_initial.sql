-- Copy title from groupapp.Group to addresses.LocalityModel
insert into locality(id, title)
select id, title from groups;

-- Copy sites for addresses.LocalityModel
insert into locality_sites(localitymodel_id, site_id)
select group_id, site_id from groups_sites;

-- Copy streets from customers.CustomerStreet into addresses.StreetModel
insert into locality_street(id, name, locality_id)
select id, name, group_id from customer_street;
