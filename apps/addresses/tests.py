from djing2.lib.fastapi.test import DjingTestCase
from starlette import status
from addresses.models import AddressModel, AddressModelTypes


class AddressesAPITestCase(DjingTestCase):
    def setUp(self):
        super().setUp()
        # Make addr hierarchy
        country = AddressModel.objects.create(
            parent_addr=None,
            address_type=AddressModelTypes.OTHER,
            fias_address_level=1,
            fias_address_type=1,
            title='Country'
        )
        state = AddressModel.objects.create(
            parent_addr=country,
            address_type=AddressModelTypes.OTHER,
            fias_address_level=1,
            fias_address_type=106,
            title="Some state"
        )
        region = AddressModel.objects.create(
            parent_addr=state,
            address_type=AddressModelTypes.OTHER,
            fias_address_level=3,
            fias_address_type=301,
            title="Area51"
        )
        self.region = region
        city = AddressModel.objects.create(
            parent_addr=region,
            address_type=AddressModelTypes.LOCALITY,
            fias_address_level=4,
            fias_address_type=405,
            title="Some region city"
        )
        self.city = city
        street = AddressModel.objects.create(
            parent_addr=city,
            address_type=AddressModelTypes.STREET,
            fias_address_level=5,
            fias_address_type=529,
            title="Street12"
        )
        house = AddressModel.objects.create(
            parent_addr=street,
            address_type=AddressModelTypes.HOUSE,
            fias_address_level=6,
            fias_address_type=601,
            title="1"
        )
        building = AddressModel.objects.create(
            parent_addr=house,
            address_type=AddressModelTypes.BUILDING,
            fias_address_level=6,
            fias_address_type=805,
            title="a"
        )
        corp = AddressModel.objects.create(
            parent_addr=building,
            address_type=AddressModelTypes.CORPUS,
            fias_address_level=6,
            fias_address_type=806,
            title="II"
        )
        office = AddressModel.objects.create(
            parent_addr=corp,
            address_type=AddressModelTypes.OFFICE_NUM,
            fias_address_level=6,
            fias_address_type=904,
            title="7"
        )
        self.office_addr = office

    def test_creating(self):
        r = self.post("/api/addrs/", {
            'parent_addr_id': self.office_addr.pk,
            'address_type': 64,
            'fias_address_level': 6,
            'fias_address_type': 905,
            'title': 'винный подвал'
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, msg=r.content)
        data = r.json()
        self.assertEqual(data['parent_addr_title'], '7')
        self.assertEqual(data['fias_address_level_name'], 'Дом')
        self.assertEqual(data['fias_address_type_name'], 'п-б')
        self.assertEqual(data['address_type'], 64)
        self.assertEqual(data['fias_address_level'], 6)
        self.assertEqual(data['fias_address_type'], 905)
        self.assertEqual(data['title'], 'винный подвал')
        self.assertEqual(data['parent_addr_id'], self.office_addr.pk)

    def _all_children_request(self, parent_addr):
        r = self.get("/api/addrs/get_all_children/", {
            'addr_type': AddressModelTypes.STREET.value,
            'parent_type': AddressModelTypes.LOCALITY.value,
            'parent_addr_id': parent_addr
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.json())
        return r.json()

    def test_fetch_all_streets_from_region(self):
        res = self._all_children_request(self.region.pk)
        self.assertIsNotNone(res)
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 0)

    def test_fetch_all_streets(self):
        res = self._all_children_request(self.city.pk)
        self.assertIsNotNone(res)
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 1)
        street = res[0]
        self.assertEqual(street['address_type'], 8)
        self.assertEqual(street['fias_address_level'], 5)
        self.assertEqual(street['fias_address_type'], 529)
        self.assertEqual(street['title'], 'Street12')
