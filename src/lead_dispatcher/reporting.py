from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .settings import settings
from .utils import mask_phone


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

    return {
        "total": len(records),
        "sent": status_counter.get("sent", 0),
        "skipped": status_counter.get("skipped", 0),
        "invalid_phone": status_counter.get("skipped_invalid_phone", 0),
        "not_sent_limit_reached": status_counter.get("not_sent_limit_reached", 0),
        "failed": status_counter.get("failed", 0),
        "limit_override": sum(1 for record in records if record.limit_override),
        "by_instance": dict(instance_counter),
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

    lines.extend(
        [
            "",
            "## Detalhes",
            "",
            "| Lead ID | Nome | Telefone | Telefone normalizado | Instância | "
            "Mensagem | Status | Motivo | Erro | Override limite |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
    )

    for record in records:
        row_template = (
            "| {lead_id} | {full_name} | {phone} | {normalized_phone} | {instance} | "
            "{message_id} | {status} | {reason} | {error} | {limit_override} |"
        )
        lines.append(
            row_template.format(
                lead_id=record.lead_id or "",
                full_name=record.full_name or "",
                phone=mask_phone(record.phone or ""),
                normalized_phone=mask_phone(record.normalized_phone or ""),
                instance=record.instance or "",
                message_id=record.message_id or "",
                status=record.status,
                reason=record.reason or "",
                error=record.error or "",
                limit_override=str(record.limit_override).lower(),
            )
        )

    return "\n".join(lines)


REPORT_FIELDS = [
    "lead_id",
    "full_name",
    "phone",
    "original_phone",
    "normalized_phone",
    "instance",
    "message_id",
    "status",
    "reason",
    "error",
    "limit_override",
]

FAILED_CONTACT_STATUSES = {
    "failed",
    "interrupted",
    "skipped_invalid_phone",
    "not_sent_limit_reached",
}


def parse_report_formats(report_formats: str | None = None) -> set[str]:
    raw_value = report_formats or getattr(settings, "report_formats", "csv,json,md")
    formats = {
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip()
    }
    return formats & {"csv", "json", "md"}


def _record_to_masked_row(record: DispatchRecord) -> dict[str, Any]:
    row = asdict(record)
    row["phone"] = mask_phone(row.get("phone") or "")
    row["original_phone"] = mask_phone(row.get("original_phone") or "")
    row["normalized_phone"] = mask_phone(row.get("normalized_phone") or "")
    return row


def _record_to_failure_row(record: DispatchRecord) -> dict[str, Any]:
    return {
        "lead_id": record.lead_id,
        "full_name": record.full_name,
        "original_phone": record.original_phone or record.phone,
        "normalized_phone": record.normalized_phone,
        "instance": record.instance,
        "message_id": record.message_id,
        "status": record.status,
        "reason": record.reason,
        "error": record.error,
        "limit_override": record.limit_override,
    }


def save_reports(
    records: list[DispatchRecord],
    *,
    report_formats: str | None = None,
) -> dict[str, Path]:
    report_dir = Path(getattr(settings, "report_dir", "reports"))
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base_name = f"send_report_{timestamp}"
    formats = parse_report_formats(report_formats)

    paths: dict[str, Path] = {}

    rows = [_record_to_masked_row(record) for record in records]

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
                    "records": rows,
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

    return paths


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
        "full_name",
        "original_phone",
        "normalized_phone",
        "instance",
        "message_id",
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
