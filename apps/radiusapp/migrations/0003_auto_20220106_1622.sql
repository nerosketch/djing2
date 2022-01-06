DROP TYPE if exists FetchSubscriberLeaseReturnType CASCADE;

DROP FUNCTION fetch_subscriber_lease(
  uuid, inet, macaddr, smallint, integer,
  varchar(32), integer, integer, integer,
  integer, boolean);
