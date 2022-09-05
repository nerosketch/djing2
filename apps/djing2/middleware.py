# TODO: deprecated, defined in 'fastapi_app.py'
class XRealIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        real_ip = request.META.get('HTTP_X_REAL_IP')
        if real_ip is not None:
            request.META['REMOTE_ADDR'] = real_ip
        return self.get_response(request)
