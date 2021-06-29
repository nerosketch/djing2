from django.test import SimpleTestCase
from radiusapp.vendors import VendorManager


class VendorsBuildDevMacByOpt82TestCase(SimpleTestCase):
    def _make_request(self, remote_id: str, circuit_id: str):
        dev_mac, dev_port = VendorManager.build_dev_mac_by_opt82(
            agent_remote_id=remote_id, agent_circuit_id=circuit_id
        )
        return dev_mac, dev_port

    def test_parse_opt82_ok(self):
        circuit_id = "0x000400980005"
        rem_id = "0x0006f8e903e755a6"
        mac, port = self._make_request(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "f8:e9:03:e7:55:a6")
        self.assertEqual(port, 5)

    def test_parse_opt82_ok2(self):
        circuit_id = "0x00007400071d"
        rem_id = "0x00061c877912e61a"
        mac, port = self._make_request(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "1c:87:79:12:e6:1a")
        self.assertEqual(port, 29)

    def test_parse_opt82_long_data(self):
        circuit_id = "0x007400ff1dff01"
        rem_id = "0x0006ff121c877912e61a"
        mac, port = self._make_request(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "1c:87:79:12:e6:1a")
        self.assertEqual(port, 1)

    def test_parse_opt82_short_data(self):
        circuit_id = "0x007400ff"
        rem_id = "0x1c8779"
        mac, port = self._make_request(remote_id=rem_id, circuit_id=circuit_id)
        self.assertIsNone(mac)
        self.assertEqual(port, 255)

    def test_parse_opt82_ok_zte(self):
        circuit_id = "0x5a5445474330323838453730"
        rem_id = "0x34353a34373a63303a32383a38653a3730"
        mac, port = self._make_request(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "45:47:c0:28:8e:70")
        self.assertEqual(port, 0)

    def test_parse_opt82_ok_zte2(self):
        circuit_id = "0x5a5445474334303235334233"
        rem_id = "0x34353a34373a63343a323a35333a6233"
        mac, port = self._make_request(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "45:47:c4:2:53:b3")
        self.assertEqual(port, 0)
