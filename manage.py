#!/usr/bin/env python3
import os
import sys


if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath("apps"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djing2.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        )
    execute_from_command_line(sys.argv)
