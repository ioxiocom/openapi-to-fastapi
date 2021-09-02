# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot

snapshots = Snapshot()

snapshots["test_weather_route_payload_errors Missing payload"] = {
    "detail": [
        {
            "loc": ["body", "lat"],
            "msg": "field required",
            "type": "value_error.missing",
        },
        {
            "loc": ["body", "lon"],
            "msg": "field required",
            "type": "value_error.missing",
        },
    ]
}

snapshots["test_weather_route_payload_errors Incorrect payload type"] = {
    "detail": [
        {
            "loc": ["body", "lat"],
            "msg": "value is not a valid float",
            "type": "type_error.float",
        },
        {
            "ctx": {"limit_value": 180.0},
            "loc": ["body", "lon"],
            "msg": "ensure this value is less than or equal to 180.0",
            "type": "value_error.number.not_le",
        },
    ]
}

snapshots["test_custom_route_definitions Custom route definition"] = {
    "detail": [
        {
            "loc": ["query", "vendor"],
            "msg": "field required",
            "type": "value_error.missing",
        },
        {
            "loc": ["header", "auth-header"],
            "msg": "field required",
            "type": "value_error.missing",
        },
    ]
}
