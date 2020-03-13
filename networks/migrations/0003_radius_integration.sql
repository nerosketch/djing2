BEGIN;
--
-- Create model CustomerIpLease
--
CREATE TABLE "networks_ip_leases"
(
  "id"           serial                      NOT NULL PRIMARY KEY,
  "ip_address"   inet                        NOT NULL,
  "pool_id"      integer                     NOT NULL,
  "lease_time"   timestamp without time zone NOT NULL default 'now'::timestamp(0),
  "customer_mac" macaddr                     NOT NULL,
  "customer_id"  integer                     NOT NULL
);
create INDEX "networks_ip_leases_pool_id" ON "networks_ip_leases" USING btree ("pool_id");
ALTER TABLE "networks_ip_leases" ADD CONSTRAINT "networks_ip_leases_pool_id_fk_networks_ip_pool_id" FOREIGN KEY ("pool_id") REFERENCES "networks_ip_pool" ("id") DEFERRABLE INITIALLY DEFERRED;



--
-- Create model NetworkIpPool
--
CREATE TABLE "networks_ip_pool"
(
  "id"          serial      NOT NULL PRIMARY KEY,
  "network"     inet        NOT NULL UNIQUE,
  "net_mask"    smallint    NOT NULL CHECK ("net_mask" >= 0),
  "kind"        smallint    NOT NULL CHECK ("kind" >= 0),
  "description" varchar(64) NOT NULL,
  "ip_start"    inet        NOT NULL,
  "ip_end"      inet        NOT NULL,
  "vlan_if_id"  integer     NULL,
  "gateway"     inet        NOT NULL,
  "lease_time"  smallint    NOT NULL CHECK ("lease_time" >= 0) DEFAULT 3600
);
CREATE INDEX "networks_ip_pool_vlan_if_id" ON "networks_ip_pool" USING btree ("vlan_if_id");
ALTER TABLE "networks_ip_pool" ADD CONSTRAINT "networks_ip_pool_vlan_if_id_networks_vlan_id" FOREIGN KEY ("vlan_if_id") REFERENCES "networks_vlan" ("id") DEFERRABLE INITIALLY DEFERRED;

--
-- Copy old network table to new ip_pool table
--
INSERT INTO networks_ip_pool(network, kind, description, ip_start, ip_end, vlan_if_id, gateway)
SELECT network, kind, description, ip_start, ip_end, vlan_if_id, ip_start-1 FROM networks_network;


--
-- Function that find free ip for new lease
--
CREATE OR REPLACE FUNCTION find_new_ip_pool_lease (
  v_pool_id integer
)
RETURNS inet
LANGUAGE plpgsql
AS $$
DECLARE
  r_address inet;
BEGIN
  SELECT ip_address FROM networks_ip_leases
END
$$

COMMIT;
