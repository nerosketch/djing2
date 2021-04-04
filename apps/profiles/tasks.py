import os
from PIL import Image
from uwsgi_tasks import task


@task()
def resize_profile_avatar(image_path: str):
    if image_path and os.path.isfile(image_path):
        im = Image.open(image_path)
        im.thumbnail((200, 121), Image.ANTIALIAS)
        im.save(image_path)
