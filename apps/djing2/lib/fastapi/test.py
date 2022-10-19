from typing import Optional

from django.test.testcases import TransactionTestCase
from django.test.runner import DiscoverRunner
from django.db import connection
from django.conf import settings
from fastapi.testclient import TestClient
from fastapi_app import app
from profiles.models import UserProfile
from rest_framework.authtoken.models import Token


class DjingTestCase(TransactionTestCase):
    c = TestClient(
        app=app,
        base_url='http://example.com'
    )

    def create_admin(self) -> None:
        # Login super user
        admin = UserProfile.objects.create_superuser(
            username="admin",
            password="admin",
            telephone="+797812345678",
            is_active=True
        )
        self.admin = admin
        token = str(Token.objects.get(user=admin).key)
        self.c.headers.update({
            'Authorization': f'Token {token}'
        })

    def logout(self):
        self.c.headers.pop('Authorization', None)

    def login(self, username: str):
        token = str(Token.objects.get(user__username=username).key)
        self.c.headers.update({
            'Authorization': f'Token {token}'
        })

    def setUp(self) -> None:
        super().setUp()
        self.create_admin()

    def get(self, url: str, data: Optional[dict] = None):
        return self.c.get(url, params=data)

    def post(self, url: str, data):
        return self.c.post(url, json=data)


class TestRunner(DiscoverRunner):
    def teardown_databases(self, old_config, **kwargs):
        # This is necessary because either FastAPI/Starlette or Django's
        # ORM isn't cleaning up the connections after it's done with
        # them.
        # The query below kills all database connections before
        # dropping the database.
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT
                pg_terminate_backend(pid) FROM pg_stat_activity WHERE
                pid <> pg_backend_pid() AND
                pg_stat_activity.datname =
                  '{settings.DATABASES["default"]["NAME"]}';"""
            )
            print(f"Killed {len(cursor.fetchall())} stale connections.")
        super().teardown_databases(old_config, **kwargs)
