import os

from django.contrib.sites.management import create_default_site


def read_all_file(fname, fl):
    curr_dir = os.path.dirname(os.path.abspath(fl))
    with open(os.path.join(curr_dir, fname)) as f:
        data = f.read(0xFFFF)
    return data


def model2default_site(apps, schema_editor, app_name, model_name):
    Site = apps.get_model("sites", "Site")
    model_klass = apps.get_model(app_name, model_name)
    site = Site.objects.all().first()
    if site is None:
        create_default_site(None, apps=apps)
        site = Site.objects.all().first()
    for ba in model_klass.objects.all().iterator():
        ba.sites.set([site])
