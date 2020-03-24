from django.test import TestCase

from groupapp.models import Group


class BaseGroupTestCase(TestCase):
    def setUp(self):
        self.group = Group.objects.create(
            title='test group',
            code='tst'
        )
