import logging

from lead_dispatcher.logging_config import PhoneMaskingFilter
from lead_dispatcher.utils import mask_phone, mask_phone_numbers, normalize_phone


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


def test_phone_masking_filter_preserves_non_string_log_args():
    record = logging.LogRecord(
        name="httpx",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='HTTP Request: %s %s "%s %d %s"',
        args=("POST", "http://localhost:4002/send/text", "HTTP/1.1", 401, "Unauthorized"),
        exc_info=None,
    )

    PhoneMaskingFilter().filter(record)

    assert record.getMessage() == (
        'HTTP Request: POST http://localhost:4002/send/text "HTTP/1.1 401 Unauthorized"'
    )


def test_normalize_phone_adds_default_country_code():
    result = normalize_phone("41995306821", default_country_code="55")

    assert result.normalized == "5541995306821"
    assert result.reason is None


def test_normalize_phone_keeps_existing_country_code():
    result = normalize_phone("5541995306821", default_country_code="55")

    assert result.normalized == "5541995306821"
    assert result.reason is None


def test_normalize_phone_cleans_masked_number():
    result = normalize_phone("(41) 99530-6821", default_country_code="55")

    assert result.normalized == "5541995306821"


def test_normalize_phone_rejects_missing_phone():
    result = normalize_phone(None, default_country_code="55")

    assert result.normalized is None
    assert result.reason == "missing_phone"


def test_normalize_phone_rejects_invalid_characters():
    result = normalize_phone("41ABC995306821", default_country_code="55")

    assert result.normalized is None
    assert result.reason == "invalid_phone_characters"


def test_normalize_phone_rejects_short_numbers():
    result = normalize_phone("123", default_country_code="55")

    assert result.normalized is None
    assert result.reason == "invalid_phone_length"
