# from typing import List
# from services.models import Service
# from sorm_export.hier_export.service import NomenclatureSimpleExportTree
# from sorm_export.models import ExportStampTypeEnum
# from sorm_export.tasks.task_export import task_export


# @task()
# def service_export_task(service_id_list: List[int], event_time=None):
#     services = Service.objects.filter(pk__in=service_id_list)
#     data, fname = export_nomenclature(services=services, event_time=event_time)
#     task_export(data, fname, ExportStampTypeEnum.SERVICE_NOMENCLATURE)
#    exporter = NomenclatureSimpleExportTree(recursive=False)
#    data = exporter.export()
#    exporter.upload2ftp(data=data)
