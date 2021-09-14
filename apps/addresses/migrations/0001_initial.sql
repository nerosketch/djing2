-- Copy title from groupapp.Group to addresses.LocalityModel
insert into locality(title)
select title from groups;

-- Copy sites for addresses.LocalityModel
insert into locality_sites(localitymodel_id, site_id)
select l.id, gs.site_id from groups_sites gs
    left join groups g on gs.group_id = g.id
    left join locality l on g.title = l.title;

-- Copy streets from customers.CustomerStreet into addresses.StreetModel
insert into locality_street(name, locality_id)
select name, l.id from customer_street cs
left join groups g on cs.group_id = g.id
left join locality l on g.title = l.title;
