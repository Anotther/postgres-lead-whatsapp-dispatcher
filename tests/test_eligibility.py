import pytest

from lead_dispatcher.eligibility import check_lead_eligibility


@pytest.mark.parametrize(
    ("lead", "reason"),
    [
        ({}, "missing_phone"),
        ({"phone": "5511999999999", "sale_started": True}, "sale_started"),
        ({"phone": "5511999999999", "enrollment_done": "sim"}, "enrollment_done"),
        ({"phone": "5511999999999", "already_sent": 1}, "already_sent"),
        (
            {"phone": "5511999999999", "opt_in_whatsapp": False},
            "missing_whatsapp_opt_in",
        ),
    ],
)
def test_check_lead_eligibility_rejects_invalid_leads(lead, reason):
    result = check_lead_eligibility(lead)

    assert result.is_eligible is False
    assert result.reason == reason


def test_check_lead_eligibility_accepts_valid_lead():
    result = check_lead_eligibility(
        {
            "phone": "5511999999999",
            "sale_started": False,
            "enrollment_done": False,
            "already_sent": False,
            "opt_in_whatsapp": True,
        }
    )

    assert result.is_eligible is True
    assert result.reason == "eligible"
