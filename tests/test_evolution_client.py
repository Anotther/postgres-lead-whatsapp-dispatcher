from lead_dispatcher.evolution_client import EvolutionClient


def test_parse_state_accepts_evolution_go_connected_response():
    client = EvolutionClient(base_url="http://localhost:4002", api_key="test")

    state = client._parse_state(
        {
            "data": {
                "Connected": True,
                "LoggedIn": True,
                "Name": "Leonardo Fortes",
            },
            "message": "success",
        }
    )

    assert state == "connected"


def test_parse_state_accepts_connection_state_response():
    client = EvolutionClient(base_url="http://localhost:4002", api_key="test")

    state = client._parse_state({"instance": {"state": "open"}})

    assert state == "open"
