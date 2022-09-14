from django.test.testcases import TestCase
from fastapi.testclient import TestClient
from fastapi_app import app


class DjingTestCase(TestCase):
    client = TestClient(app=app)
