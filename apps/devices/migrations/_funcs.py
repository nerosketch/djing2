from devices.device_config.device_type_collection import DEVICE_TYPES

create_tbl = """CREATE TABLE "device_dev_type_is_use_dev_port"
(
  "id"              serial  NOT NULL PRIMARY KEY,
  "dev_type"        integer NOT NULL,
  "is_use_dev_port" boolean NOT NULL
);
ALTER TABLE "device_dev_type_is_use_dev_port"
  ADD CONSTRAINT "device_dev_type_is_use_dev_port_type_is_use" UNIQUE ("dev_type", "is_use_dev_port");"""


def prepare_sql_inject():
    vals = ", ".join("(%d, %s)" % (num, klass.is_use_device_port) for num, klass in DEVICE_TYPES).lower()
    return (
        'INSERT INTO "device_dev_type_is_use_dev_port" (dev_type, is_use_dev_port) '
        'VALUES %s ON CONFLICT DO NOTHING;' % vals
    )
