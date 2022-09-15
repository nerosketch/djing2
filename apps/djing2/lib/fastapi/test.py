from django.test.testcases import TestCase
from django.test.runner import DiscoverRunner
from django.db import connection
from django.conf import settings
from fastapi.testclient import TestClient
from fastapi_app import app


class TClient(TestClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers.update({
            'Authorization': 'Token asdasd'
        })


class DjingTestCase(TestCase):
    c = TClient(
        app=app,
        base_url="http://example.com"
    )


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
