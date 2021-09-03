from django.test import SimpleTestCase

from radiusapp.vendors import parse_opt82


class Option82TestCase(SimpleTestCase):
    def test_parse_opt82_ok(self):
        circuit_id = b"\x00\x04\x00\x98\x00\x05"
        rem_id = b"\x00\x06\xec\x22\x80\x7f\xad\xb8"
        mac, port = parse_opt82(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "ec:22:80:7f:ad:b8")
        self.assertEqual(port, 5)

    def test_parse_opt82_ok2(self):
        circuit_id = b"\x00\x74\x00\x07\x1d"
        rem_id = b"\x1c\x87\x79\x12\xe6\x1a"
        mac, port = parse_opt82(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "1c:87:79:12:e6:1a")
        self.assertEqual(port, 29)

    def test_parse_opt82_long_data(self):
        circuit_id = b"\x00\x74\x00\xff\x1d\xff\x01"
        rem_id = b"\xff\x12\x1c\x87\x79\x12\xe6\x1a"
        mac, port = parse_opt82(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "1c:87:79:12:e6:1a")
        self.assertEqual(port, 1)

    def test_parse_opt82_short_data(self):
        circuit_id = b"\x00\x74\x00\xff"
        rem_id = b"\x1c\x87\x79"
        mac, port = parse_opt82(remote_id=rem_id, circuit_id=circuit_id)
        self.assertIsNone(mac)
        self.assertEqual(port, 255)

    def test_parse_opt82_ok_zte(self):
        circuit_id = b"\x5a\x54\x45\x47\x43\x30\x32\x38\x38\x45\x37\x30"
        rem_id = b"\x34\x35\x3a\x34\x37\x3a\x63\x30\x3a\x32\x38\x3a\x38\x65\x3a\x37\x30"
        mac, port = parse_opt82(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "45:47:c0:28:8e:70")
        self.assertEqual(port, 0)

    def test_parse_opt82_ok_zte2(self):
        circuit_id = b"\x5a\x54\x45\x47\x43\x34\x30\x32\x35\x33\x42\x33"
        rem_id = b"\x34\x35\x3a\x34\x37\x3a\x63\x34\x3a\x32\x3a\x35\x33\x3a\x62\x33"
        mac, port = parse_opt82(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "45:47:c4:2:53:b3")
        self.assertEqual(port, 0)
