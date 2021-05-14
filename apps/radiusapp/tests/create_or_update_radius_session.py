from datetime import timedelta
from uuid import UUID

from customers.tests.get_user_credentials_by_ip import BaseServiceTestCase
from radiusapp.models import CustomerRadiusSession


class CreateOrUpdateRadiusSession(BaseServiceTestCase):
    def setUp(self):
        super().setUp()

        self.customer.device = self.device_switch
        self.customer.dev_port = self.ports[1]
        self.customer.add_balance(self.admin, 10000, "test")
        self.customer.save()
        self.customer.refresh_from_db()
        self.customer.pick_service(self.service, self.customer)

    def test_new_session_ok(self):
        is_created = CustomerRadiusSession.objects.create_or_update_session(
            session_id="b51db081c208510befe067ae1507d79f",
            v_ip_addr="192.168.3.50",
            v_dev_mac="12:13:14:15:16:17",
            v_dev_port="2",
            v_sess_time=timedelta(seconds=0),
            v_uname="F8:75:A4:AA:C9:E0",
            v_inp_oct=0,
            v_out_oct=0,
            v_in_pkt=0,
            v_out_pkt=0,
        )
        self.assertTrue(is_created)
        created_sess = CustomerRadiusSession.objects.filter(session_id="b51db081c208510befe067ae1507d79f").first()
        self.assertIsNotNone(created_sess)
        self.assertEqual(created_sess.framed_ip_addr, "192.168.3.50")
        self.assertEqual(created_sess.radius_username, "F8:75:A4:AA:C9:E0")
        self.assertEqual(created_sess.session_id, UUID("b51db081c208510befe067ae1507d79f"))
        self.assertEqual(created_sess.session_duration, timedelta(seconds=0))
        self.assertEqual(created_sess.input_octets, 0)
        self.assertEqual(created_sess.output_octets, 0)
        self.assertEqual(created_sess.input_packets, 0)
        self.assertEqual(created_sess.output_packets, 0)
        self.assertFalse(created_sess.closed)

    def test_new_session_customer_not_found(self):
        is_created = CustomerRadiusSession.objects.create_or_update_session(
            session_id="b51db081c208510befe067ae1507d79f",
            v_ip_addr="192.168.3.50",
            v_dev_mac="12:13:14:15:16:17",
            v_dev_port="1",
            v_sess_time=timedelta(seconds=0),
            v_uname="F8:75:A4:AA:C9:E0",
            v_inp_oct=0,
            v_out_oct=0,
            v_in_pkt=0,
            v_out_pkt=0,
        )
        self.assertFalse(is_created)

    def test_update_session(self):
        self.test_new_session_ok()
        is_created = CustomerRadiusSession.objects.create_or_update_session(
            session_id="b51db081c208510befe067ae1507d79f",
            v_ip_addr="192.168.3.55",
            v_dev_mac="12:13:14:15:16:17",
            v_dev_port="1",
            v_sess_time=timedelta(seconds=11),
            v_uname="F8:71:A4:A3:C9:E2",
            v_inp_oct=12,
            v_out_oct=17,
            v_in_pkt=19,
            v_out_pkt=21,
        )
        self.assertFalse(is_created)
        created_sess = CustomerRadiusSession.objects.filter(session_id="b51db081c208510befe067ae1507d79f").first()
        self.assertIsNotNone(created_sess)
        self.assertEqual(created_sess.framed_ip_addr, "192.168.3.55")
        self.assertEqual(created_sess.radius_username, "F8:71:A4:A3:C9:E2")
        self.assertEqual(created_sess.session_duration, timedelta(seconds=11))
        self.assertEqual(created_sess.input_octets, 12)
        self.assertEqual(created_sess.output_octets, 17)
        self.assertEqual(created_sess.input_packets, 19)
        self.assertEqual(created_sess.output_packets, 21)
        self.assertFalse(created_sess.closed)

    def test_close_session(self):
        self.test_new_session_ok()
        is_created = CustomerRadiusSession.objects.create_or_update_session(
            session_id="b51db081c208510befe067ae1507d79f",
            v_ip_addr="192.168.3.50",
            v_dev_mac="12:13:14:15:16:17",
            v_dev_port="1",
            v_sess_time=timedelta(seconds=11),
            v_uname="F8:75:A4:AA:C9:E0",
            v_inp_oct=12,
            v_out_oct=17,
            v_in_pkt=19,
            v_out_pkt=21,
            v_is_stop=True,
        )
        self.assertFalse(is_created)
        created_sess = CustomerRadiusSession.objects.filter(session_id="b51db081c208510befe067ae1507d79f").first()
        self.assertIsNotNone(created_sess)
        self.assertEqual(created_sess.session_duration, timedelta(seconds=11))
        self.assertEqual(created_sess.input_octets, 12)
        self.assertEqual(created_sess.output_octets, 17)
        self.assertEqual(created_sess.input_packets, 19)
        self.assertEqual(created_sess.output_packets, 21)
        self.assertTrue(created_sess.closed)

    def test_new_session_without_session_id(self):
        is_created = CustomerRadiusSession.objects.create_or_update_session(
            session_id=None,
            v_ip_addr="192.168.3.50",
            v_dev_mac="12:13:14:15:16:17",
            v_dev_port="2",
            v_sess_time=timedelta(seconds=0),
            v_uname="F8:75:A4:AA:C9:E0",
            v_inp_oct=0,
            v_out_oct=0,
            v_in_pkt=0,
            v_out_pkt=0,
        )
        self.assertFalse(is_created)

    def test_new_session_with_empty_str_session_id(self):
        is_created = CustomerRadiusSession.objects.create_or_update_session(
            session_id="",
            v_ip_addr="192.168.3.50",
            v_dev_mac="12:13:14:15:16:17",
            v_dev_port="2",
            v_sess_time=timedelta(seconds=0),
            v_uname="F8:75:A4:AA:C9:E0",
            v_inp_oct=0,
            v_out_oct=0,
            v_in_pkt=0,
            v_out_pkt=0,
        )
        self.assertFalse(is_created)
