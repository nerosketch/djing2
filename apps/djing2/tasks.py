# from webpush import send_group_notification
# from uwsgi_tasks import task


# TODO: enable push
# @task()
# def send_broadcast_push_notification(title: str, body: str, url=None, **other_info):
#     pass
#     payload = {"title": title, "body": body}
#     if url:
#        payload["url"] = url
#     if other_info:
#        payload.update(other_info)
#     send_group_notification(group_name="group_name", payload=payload, ttl=3600)
