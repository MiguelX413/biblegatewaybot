from __future__ import annotations

import json as _stdlib_json
from types import ModuleType
from typing import Any, Final

_orjson: ModuleType | None
try:
    import orjson as _orjson_module
except ImportError:  # pragma: no cover - exercised when optional extra is absent
    _orjson = None
else:
    _orjson = _orjson_module

_ujson: ModuleType | None
try:
    import ujson as _ujson_module
except ImportError:  # pragma: no cover - exercised when optional extra is absent
    _ujson = None
else:
    _ujson = _ujson_module

BACKEND_NAME: Final[str] = (
    "orjson" if _orjson is not None else "ujson" if _ujson is not None else "json"
)


def loads(data: str | bytes | bytearray) -> Any:
    if _orjson is not None:
        return _orjson.loads(str(data) if isinstance(data, str) else data)
    if _ujson is not None:
        return _ujson.loads(data)
    return _stdlib_json.loads(data)


def dumps(obj: Any, /, **kwargs: Any) -> str:
    if _orjson is not None:
        if kwargs:
            return _stdlib_json.dumps(obj, **kwargs)
        return _orjson.dumps(obj).decode("utf-8")
    if _ujson is not None:
        return _ujson.dumps(obj, **kwargs)
    return _stdlib_json.dumps(obj, **kwargs)
