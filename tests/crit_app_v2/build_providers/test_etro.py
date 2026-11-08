"""Tests for the Etro HTTP API adapter."""

import json

import requests

from crit_app_v2.build_providers.etro import _list_gearset
from crit_app_v2.build_providers.models import EtroBuildResponse


def test_list_gearset_fetches_and_validates_direct_api_response(monkeypatch):
    """Fetch one Etro gearset directly and validate the returned JSON."""
    gearset_id = "1dde8dd8-0953-4760-a5a4-1710a023f064"
    response_data = {
        "name": "Test build",
        "jobAbbrev": "PLD",
        "partyBonus": 1.05,
        "totalParams": [
            {"name": name, "value": value}
            for name, value in {
                "STR": 6772,
                "DET": 3066,
                "SKS": 420,
                "CRT": 3595,
                "DH": 1230,
                "Weapon Damage": 158,
                "TEN": 622,
            }.items()
        ],
    }
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps(response_data).encode()
    request_arguments = {}

    def fake_get(url, **kwargs):
        request_arguments["url"] = url
        request_arguments.update(kwargs)
        return response

    monkeypatch.setattr("crit_app_v2.build_providers.etro.requests.get", fake_get)

    result = _list_gearset(gearset_id)

    assert result == EtroBuildResponse.model_validate(response_data)
    assert request_arguments == {
        "url": f"https://etro.gg/api/gearsets/{gearset_id}/",
        "timeout": 30,
    }
