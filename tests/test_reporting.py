import csv

from lead_dispatcher import reporting
from lead_dispatcher.reporting import DispatchRecord, render_markdown_report, save_reports


def test_markdown_report_omits_lead_phone_details():
    report = render_markdown_report(
        [
            DispatchRecord(
                lead_id=1,
                full_name="Ana Silva",
                phone="41995306821",
                instance="sua-instancia-principal",
                message_id="ead_continuidade_01",
                status="sent",
            )
        ]
    )

    assert "41995306821" not in report
    assert "4199*****21" not in report
    assert "sua-instancia-principal: 1" in report


def test_save_reports_respects_configured_formats(tmp_path, monkeypatch):
    monkeypatch.setattr(reporting.settings, "report_dir", str(tmp_path))

    paths = save_reports(
        [
            DispatchRecord(
                lead_id=1,
                full_name="Ana Silva",
                phone="5541995306821",
                instance="caixa-01",
                message_id="ead_continuidade_01",
                status="sent",
            )
        ],
        report_formats="csv,md",
    )

    assert set(paths) == {"csv", "md"}
    assert paths["csv"].exists()
    assert paths["md"].exists()

    assert "5541995306821" not in paths["csv"].read_text(encoding="utf-8")
    assert "5541995306821" not in paths["md"].read_text(encoding="utf-8")


def test_save_reports_exports_failed_contacts_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(reporting.settings, "report_dir", str(tmp_path))

    paths = save_reports(
        [
            DispatchRecord(
                lead_id=1,
                full_name="Ana Silva",
                phone="ABC",
                instance=None,
                message_id=None,
                status="skipped_invalid_phone",
                reason="invalid_phone_characters",
                original_phone="ABC",
            )
        ],
        report_formats="json",
    )

    assert set(paths) == {"json", "failed_contacts_csv"}

    with paths["failed_contacts_csv"].open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    assert rows[0]["lead_id"] == "1"
    assert rows[0]["original_phone"] == "ABC"
    assert rows[0]["status"] == "skipped_invalid_phone"
    assert rows[0]["reason"] == "invalid_phone_characters"
