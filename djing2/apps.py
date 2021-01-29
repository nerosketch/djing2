from django.apps import AppConfig


class Djing2Config(AppConfig):
    name = 'djing2'

    def ready(self):
        from uwsgi_tasks import django_setup
        django_setup()
