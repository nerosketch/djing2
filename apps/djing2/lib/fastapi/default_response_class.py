from ipaddress import IPv4Address
from typing import Any
from json import dumps, JSONEncoder

from starlette.responses import JSONResponse


class CompatibleJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, IPv4Address):
            return str(obj)
        return super().default(obj)


class CompatibleJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=CompatibleJSONEncoder
        ).encode("utf-8")
