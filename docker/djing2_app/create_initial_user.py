from profiles.models import UserProfile


def make_initial_user():
    if not UserProfile.objects.filter(username="admin").exists():
        UserProfile.objects.create_superuser(telephone="+79780000000", username="admin", password="ex_password")
