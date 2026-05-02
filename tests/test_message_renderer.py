import pytest

from lead_dispatcher import message_renderer


def test_get_enabled_messages_filters_disabled_templates():
    config = {
        "messages": [
            {"id": "enabled-default"},
            {"id": "enabled-explicit", "enabled": True},
            {"id": "disabled", "enabled": False},
        ]
    }

    enabled_messages = message_renderer.get_enabled_messages(config)

    assert [message["id"] for message in enabled_messages] == [
        "enabled-default",
        "enabled-explicit",
    ]


def test_choose_weighted_message_raises_when_no_messages_are_enabled():
    with pytest.raises(ValueError, match="No enabled messages"):
        message_renderer.choose_weighted_message([])


def test_render_message_uses_selected_template_and_greeting(monkeypatch):
    config = {
        "greeting_variations": ["Oi"],
        "messages": [
            {
                "id": "template-1",
                "enabled": True,
                "weight": 1,
                "text": (
                    "{greeting}, {first_name}. "
                    "{full_name} quer {course_interest} em {duration_interest}."
                ),
            }
        ],
    }

    monkeypatch.setattr(message_renderer, "load_message_config", lambda: config)
    monkeypatch.setattr(message_renderer.random, "choice", lambda values: values[0])
    monkeypatch.setattr(
        message_renderer.random,
        "choices",
        lambda values, weights, k: [values[0]],
    )

    message_id, text = message_renderer.render_message(
        {
            "full_name": "Ana Silva",
            "course_interest": "Administração",
            "duration_interest": "4 anos",
        }
    )

    assert message_id == "template-1"
    assert text == "Oi, Ana. Ana Silva quer Administração em 4 anos."
