--
-- Create model CustomerIpLease
--
CREATE TABLE "networks_ip_leases"
(
  "id"           bigserial                   NOT NULL PRIMARY KEY,
  "ip_address"   inet                        NOT NULL UNIQUE,
  "pool_id"      integer                     NOT NULL,
  "lease_time"   timestamp without time zone NOT NULL DEFAULT now()::timestamp(0),
  "mac_address"  macaddr                     NULL,
  "customer_id"  integer                     NOT NULL,
  "is_dynamic"   boolean                     NOT NULL DEFAULT FALSE
);
CREATE INDEX "networks_ip_leases_pool_id"
  ON "networks_ip_leases"
  USING btree ("pool_id");
ALTER TABLE "networks_ip_leases" ADD CONSTRAINT "networks_ip_leases_ip_address_mac_address__customer_uniq" UNIQUE ("ip_address", "mac_address", "pool_id", "customer_id");

--
-- Create model NetworkIpPool
--
CREATE TABLE "networks_ip_pool"
(
  "id"          bigserial   NOT NULL PRIMARY KEY,
  "network"     inet        NOT NULL UNIQUE,
  --   "net_mask"    smallint    NOT NULL CHECK ("net_mask" >= 0),
  "kind"        smallint    NOT NULL CHECK ("kind" >= 0),
  "description" varchar(64) NOT NULL,
  "ip_start"    inet        NOT NULL,
  "ip_end"      inet        NOT NULL,
  "vlan_if_id"  integer     NULL,
  "gateway"     inet        NOT NULL
);
CREATE INDEX "networks_ip_pool_vlan_if_id"
  ON "networks_ip_pool"
  USING btree ("vlan_if_id");
ALTER TABLE "networks_ip_pool"
  ADD CONSTRAINT "networks_ip_pool_vlan_if_id_networks_vlan_id" FOREIGN KEY ("vlan_if_id") REFERENCES "networks_vlan" ("id")
  DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "networks_ip_leases"
  ADD CONSTRAINT "networks_ip_leases_pool_id_fk_networks_ip_pool_id" FOREIGN KEY ("pool_id") REFERENCES "networks_ip_pool" ("id")
  DEFERRABLE INITIALLY DEFERRED;

--
-- Copy old network table to new ip_pool table
--
INSERT INTO networks_ip_pool ("id", "network", "kind", "description", "ip_start", "ip_end", "vlan_if_id", "gateway")
  SELECT
    "id",
    "network",
    "kind",
    "description",
    "ip_start",
    "ip_end",
    "vlan_if_id",
    HOST(NETWORK("network")::inet + 1)::inet
  FROM networks_network;


--
-- Copy old ip address from customer accounts to ip leases
--
INSERT INTO networks_ip_leases ("ip_address", "pool_id", "lease_time", "customer_id", "is_dynamic")
  SELECT
    customers.ip_address,
    networks_ip_pool.id,
    (timestamp without time zone '1000-01-01 00:00:00'),
    customers.baseaccount_ptr_id,
    customers.is_dynamic_ip
  FROM customers
  LEFT JOIN networks_ip_pool ON (customers.ip_address << networks_ip_pool.network)
  WHERE customers.ip_address IS NOT NULL AND networks_ip_pool.id IS NOT NULL;


--
-- Add field groups to networkippool
--
CREATE TABLE "networks_ippool_groups" ("id" serial NOT NULL PRIMARY KEY, "networkippool_id" integer NOT NULL, "group_id" integer NOT NULL);

-- Copy old network group relations into new
INSERT INTO networks_ippool_groups ("networkippool_id", "group_id")
  SELECT
    "networkmodel_id",
    "group_id"
  FROM networks_network_groups;
