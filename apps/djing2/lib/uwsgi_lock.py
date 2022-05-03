
try:
    import uwsgi
except ImportError:
    _stub_fn = lambda *_: ...
    class uwsgi:
        lock = _stub_fn
        unlock = _stub_fn


