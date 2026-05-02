from lead_dispatcher.reporting import DispatchRecord, render_markdown_report


def test_markdown_report_masks_phone():
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
    assert "4199*****21" in report
