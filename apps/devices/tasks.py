from uwsgi_tasks import task

from devices.models import Device
from devices.device_config.device_type_collection import DEVICE_ONU_TYPES


@task()
def unregister_device_async(device_id: int) -> None:
    """
    Remove ONU from OLT or make other post delete device action
    :return:
    """
    device = Device.objects.filter(pk=device_id).first()
    if not device:
        return None
    if device.dev_type in DEVICE_ONU_TYPES:
        device.remove_from_olt()
