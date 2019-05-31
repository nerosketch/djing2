from rest_framework.exceptions import APIException


class UniqueConstraintIntegrityError(APIException):
    status_code = 409
    default_detail = 'The request could not be completed due to a conflict with the current state of the resource'
    default_code = 'unique_conflict'
