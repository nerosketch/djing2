from typing import Optional, Any

from django.core.management import CommandParser
from django.core.management.base import CommandError, BaseCommand, no_translations
from django.contrib.sites.models import Site


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            'action', choices=['add', 'show', 'patch'], default='show'
        )
        parser.add_argument(
            '-i', '--id', type=int, required=False
        )
        parser.add_argument(
            '-d', '--domain', type=str, help='Domain string'
        )
        parser.add_argument(
            '-n', '--name', type=str, help='Domain title'
        )

    def _add(self, domain: str, name: str, *args, **options):
        s = Site.objects.create(
            domain=domain,
            name=name
        )
        self.stdout.write(f'Domain "{s.domain}"[{s.name}] created {self.style.SUCCESS("OK")}')

    def _show(self, *args, **options):
        sites = Site.objects.all()
        text = f"{'ID' : <5}{'DOMAIN' : <30}NAME"
        self.stdout.write(text)
        for s in sites:
            text = f"{s.pk : <5}{s.domain : <30}{s.name}"
            self.stdout.write(text)

    def _patch(self, id: int, domain: str, name: str, *args, **options):
        if id is None:
            raise CommandError('ID is required for patch')
        sites = Site.objects.filter(pk=id)
        if sites.exists():
            sites.update(
                domain=domain,
                name=name
            )
            self.stdout.write('Changed', ending=' ')
            self.stdout.write(self.style.SUCCESS('OK'))
        else:
            self.stdout.write(self.style.ERROR('Not found'))

    def _unknown_action(self, *args, **options):
        self.stderr.write(self.style.ERROR('Unknown command'))

    @no_translations
    def handle(self, action: str, *args: Any, **options: Any) -> Optional[str]:
        actions = {
            'add': self._add,
            'show': self._show,
            'patch': self._patch
        }
        fn = actions.get(action, self._unknown_action)
        return fn(*args, **options)
