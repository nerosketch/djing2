DROP TYPE IF EXISTS FetchSubscriberLeaseReturnType CASCADE;

DROP FUNCTION IF EXISTS fetch_subscriber_lease(
  uuid, inet, macaddr, smallint, integer,
  varchar(32), integer, integer, integer,
  integer, boolean);
