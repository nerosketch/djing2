import os


def read_all_file(fname, fl):
    curr_dir = os.path.dirname(os.path.abspath(fl))
    with open(os.path.join(curr_dir, fname), 'r') as f:
        data = f.read(0xffff)
    return data


def model2default_site(apps, schema_editor, app_name, model_name):
    Site = apps.get_model('sites', 'Site')
    model_klass = apps.get_model(app_name, model_name)
    site = Site.objects.all().first()
    if site is None:
        site = Site.objects.create(
            domain='example.com',
            name='example.com'
        )
    for ba in model_klass.objects.all().iterator():
        ba.sites.set([site])
