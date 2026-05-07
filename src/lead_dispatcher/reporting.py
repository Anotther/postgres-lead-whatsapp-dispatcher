from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .settings import settings


@dataclass
class DispatchRecord:
    lead_id: str | int | None
    full_name: str | None
    phone: str | None
    instance: str | None
    message_id: str | None
    status: str
    reason: str | None = None
    error: str | None = None
    original_phone: str | None = None
    normalized_phone: str | None = None
    limit_override: bool = False


def build_report_summary(records: list[DispatchRecord]) -> dict[str, Any]:
    status_counter = Counter(record.status for record in records)
    instance_counter = Counter(
        record.instance for record in records if record.instance and record.status == "sent"
    )
    failure_reason_counter = Counter(
        record.reason or record.status
        for record in records
        if record.status in FAILED_CONTACT_STATUSES
        or record.status == "skipped"
    )

    return {
        "total": len(records),
        "sent": status_counter.get("sent", 0),
        "skipped": status_counter.get("skipped", 0),
        "invalid_phone": status_counter.get("skipped_invalid_phone", 0),
        "not_sent_limit_reached": status_counter.get("not_sent_limit_reached", 0),
        "failed": status_counter.get("failed", 0),
        "limit_override": sum(1 for record in records if record.limit_override),
        "by_instance": dict(instance_counter),
        "by_failure_reason": dict(failure_reason_counter),
    }


def render_markdown_report(records: list[DispatchRecord]) -> str:
    summary = build_report_summary(records)

    lines = [
        "# Relatório de envio",
        "",
        f"- Total processado: {summary['total']}",
        f"- Enviados: {summary['sent']}",
        f"- Ignorados: {summary['skipped']}",
        f"- Telefones inválidos: {summary['invalid_phone']}",
        f"- Não enviados por limite: {summary['not_sent_limit_reached']}",
        f"- Falhas: {summary['failed']}",
        f"- Enviados com override de limite: {summary['limit_override']}",
        "",
        "## Enviados por instância",
        "",
    ]

    if summary["by_instance"]:
        for instance, total in summary["by_instance"].items():
            lines.append(f"- {instance}: {total}")
    else:
        lines.append("- Nenhum envio registrado.")

    lines.extend(["", "## Falhas por motivo", ""])

    if summary["by_failure_reason"]:
        for reason, total in summary["by_failure_reason"].items():
            lines.append(f"- {reason}: {total}")
    else:
        lines.append("- Nenhuma falha registrada.")

    return "\n".join(lines)


REPORT_FIELDS = [
    "metric",
    "value",
]

FAILED_CONTACT_STATUSES = {
    "failed",
    "interrupted",
    "skipped_invalid_phone",
    "not_sent_limit_reached",
}


def parse_report_formats(report_formats: str | None = None) -> set[str]:
    raw_value = report_formats or getattr(settings, "report_formats", "md")
    formats = [
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip()
    ]

    for report_format in formats:
        if report_format in {"csv", "json", "md"}:
            return {report_format}

    return {"md"}


def _summary_rows(records: list[DispatchRecord]) -> list[dict[str, Any]]:
    summary = build_report_summary(records)
    rows = [
        {"metric": "total", "value": summary["total"]},
        {"metric": "sent", "value": summary["sent"]},
        {"metric": "skipped", "value": summary["skipped"]},
        {"metric": "invalid_phone", "value": summary["invalid_phone"]},
        {
            "metric": "not_sent_limit_reached",
            "value": summary["not_sent_limit_reached"],
        },
        {"metric": "failed", "value": summary["failed"]},
        {"metric": "limit_override", "value": summary["limit_override"]},
    ]

    for instance, total in summary["by_instance"].items():
        rows.append({"metric": f"sent_by_instance:{instance}", "value": total})

    for reason, total in summary["by_failure_reason"].items():
        rows.append({"metric": f"failure_reason:{reason}", "value": total})

    return rows


def _record_to_failure_row(record: DispatchRecord) -> dict[str, Any]:
    return {
        "lead_id": record.lead_id,
        "phone": record.normalized_phone or record.phone or record.original_phone,
        "instance": record.instance,
        "status": record.status,
        "reason": record.reason,
        "error": record.error,
        "limit_override": record.limit_override,
    }


def _record_to_sent_row(record: DispatchRecord) -> dict[str, Any]:
    return {
        "lead_id": record.lead_id,
        "phone": record.normalized_phone or record.phone,
        "instance": record.instance,
    }


def cleanup_old_reports(report_dir: Path) -> None:
    if getattr(settings, "report_keep_history", False):
        return

    for pattern in ("send_report_*", "sent_contacts_*", "failed_contacts_*"):
        for path in report_dir.glob(pattern):
            if path.is_file():
                path.unlink()


def save_reports(
    records: list[DispatchRecord],
    *,
    report_formats: str | None = None,
) -> dict[str, Path]:
    report_dir = Path(getattr(settings, "report_dir", "reports"))
    report_dir.mkdir(parents=True, exist_ok=True)
    cleanup_old_reports(report_dir)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base_name = f"send_report_{timestamp}"
    formats = parse_report_formats(report_formats)

    paths: dict[str, Path] = {}

    rows = _summary_rows(records)

    if "csv" in formats:
        paths["csv"] = report_dir / f"{base_name}.csv"
        with paths["csv"].open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=REPORT_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    if "json" in formats:
        paths["json"] = report_dir / f"{base_name}.json"
        with paths["json"].open("w", encoding="utf-8") as file:
            json.dump(
                {
                    "summary": build_report_summary(records),
                },
                file,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

    if "md" in formats:
        paths["md"] = report_dir / f"{base_name}.md"
        with paths["md"].open("w", encoding="utf-8") as file:
            file.write(render_markdown_report(records))

    failure_path = save_failed_contacts_report(records, timestamp=timestamp)
    if failure_path:
        paths["failed_contacts_csv"] = failure_path

    sent_path = save_sent_contacts_report(records, timestamp=timestamp)
    if sent_path:
        paths["sent_contacts_csv"] = sent_path

    return paths


def save_sent_contacts_report(
    records: list[DispatchRecord],
    *,
    timestamp: str | None = None,
) -> Path | None:
    sent_records = [record for record in records if record.status == "sent"]

    if not sent_records:
        return None

    report_dir = Path(getattr(settings, "report_dir", "reports"))
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = timestamp or datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = report_dir / f"sent_contacts_{timestamp}.csv"

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["lead_id", "phone", "instance"])
        writer.writeheader()
        for record in sent_records:
            writer.writerow(_record_to_sent_row(record))

    return path


def save_failed_contacts_report(
    records: list[DispatchRecord],
    *,
    timestamp: str | None = None,
) -> Path | None:
    failed_records = [
        record for record in records
        if record.status in FAILED_CONTACT_STATUSES
    ]

    if not failed_records:
        return None

    report_dir = Path(getattr(settings, "report_dir", "reports"))
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = timestamp or datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = report_dir / f"failed_contacts_{timestamp}.csv"
    fieldnames = [
        "lead_id",
        "phone",
        "instance",
        "status",
        "reason",
        "error",
        "limit_override",
    ]

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for record in failed_records:
            writer.writerow(_record_to_failure_row(record))

    return path


def render_whatsapp_summary(records: list[DispatchRecord]) -> str:
    summary = build_report_summary(records)

    lines = [
        "Relatório de envio - Leads Ensino Superior",
        "",
        f"Total processado: {summary['total']}",
        f"Enviados: {summary['sent']}",
        f"Ignorados: {summary['skipped']}",
        f"Telefones inválidos: {summary['invalid_phone']}",
        f"Não enviados por limite: {summary['not_sent_limit_reached']}",
        f"Falhas: {summary['failed']}",
        f"Com override de limite: {summary['limit_override']}",
        "",
        "Por instância:",
    ]

    if summary["by_instance"]:
        for instance, total in summary["by_instance"].items():
            lines.append(f"- {instance}: {total} enviados")
    else:
        lines.append("- Nenhum envio registrado.")

    return "\n".join(lines)
