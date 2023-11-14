# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot

snapshots = Snapshot()

snapshots["test_custom_route_definitions Custom route definition"] = {
    "detail": [
        {
            "input": None,
            "loc": ["query", "vendor"],
            "msg": "Field required",
            "type": "missing",
            "url": "https://errors.pydantic.dev/2.4/v/missing",
        },
        {
            "input": None,
            "loc": ["header", "auth-header"],
            "msg": "Field required",
            "type": "missing",
            "url": "https://errors.pydantic.dev/2.4/v/missing",
        },
    ]
}

snapshots["test_weather_route_payload_errors Incorrect payload type"] = {
    "detail": [
        {
            "input": "1,1.2",
            "loc": ["body", "lat"],
            "msg": "Input should be a valid number, unable to parse string as a number",
            "type": "float_parsing",
            "url": "https://errors.pydantic.dev/2.4/v/float_parsing",
        },
        {
            "ctx": {"le": 180.0},
            "input": "99999",
            "loc": ["body", "lon"],
            "msg": "Input should be less than or equal to 180",
            "type": "less_than_equal",
            "url": "https://errors.pydantic.dev/2.4/v/less_than_equal",
        },
    ]
}

snapshots["test_weather_route_payload_errors Missing payload"] = {
    "detail": [
        {
            "input": {},
            "loc": ["body", "lat"],
            "msg": "Field required",
            "type": "missing",
            "url": "https://errors.pydantic.dev/2.4/v/missing",
        },
        {
            "input": {},
            "loc": ["body", "lon"],
            "msg": "Field required",
            "type": "missing",
            "url": "https://errors.pydantic.dev/2.4/v/missing",
        },
    ]
}
