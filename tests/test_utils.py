import logging

from lead_dispatcher.logging_config import PhoneMaskingFilter
from lead_dispatcher.utils import mask_phone, mask_phone_numbers


def test_mask_phone_keeps_only_safe_edges():
    assert mask_phone("41995306821") == "4199*****21"
    assert "41995306821" not in mask_phone("41995306821")


def test_mask_phone_numbers_masks_embedded_phone():
    text = "Enviando de 5541995306821 para 41995306821"

    masked = mask_phone_numbers(text)

    assert "5541995306821" not in masked
    assert "41995306821" not in masked
    assert "5541*******21" in masked
    assert "4199*****21" in masked


def test_phone_masking_filter_masks_log_record_message():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Contato phone=%s",
        args=("41995306821",),
        exc_info=None,
    )

    PhoneMaskingFilter().filter(record)

    assert "41995306821" not in record.getMessage()
    assert "4199*****21" in record.getMessage()
