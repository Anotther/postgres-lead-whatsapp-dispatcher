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


def build_report_summary(records: list[DispatchRecord]) -> dict[str, Any]:
    status_counter = Counter(record.status for record in records)
    instance_counter = Counter(
        record.instance for record in records if record.instance and record.status == "sent"
    )

    return {
        "total": len(records),
        "sent": status_counter.get("sent", 0),
        "skipped": status_counter.get("skipped", 0),
        "failed": status_counter.get("failed", 0),
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
        f"- Falhas: {summary['failed']}",
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
            "| Lead ID | Nome | Telefone | Instância | Mensagem | Status | Motivo | Erro |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )

    for record in records:
        lines.append(
            "| {lead_id} | {full_name} | {phone} | {instance} | {message_id} | {status} | {reason} | {error} |".format(
                lead_id=record.lead_id or "",
                full_name=record.full_name or "",
                phone=mask_phone(record.phone or ""),
                instance=record.instance or "",
                message_id=record.message_id or "",
                status=record.status,
                reason=record.reason or "",
                error=record.error or "",
            )
        )

    return "\n".join(lines)


def save_reports(records: list[DispatchRecord]) -> dict[str, Path]:
    report_dir = Path(getattr(settings, "report_dir", "reports"))
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base_name = f"send_report_{timestamp}"

    paths = {
        "csv": report_dir / f"{base_name}.csv",
        "json": report_dir / f"{base_name}.json",
        "md": report_dir / f"{base_name}.md",
    }

    rows = [asdict(record) for record in records]

    with paths["csv"].open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "lead_id",
                "full_name",
                "phone",
                "instance",
                "message_id",
                "status",
                "reason",
                "error",
            ],
        )
        writer.writeheader()
        for row in rows:
            row["phone"] = mask_phone(row.get("phone") or "")
            writer.writerow(row)

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

    with paths["md"].open("w", encoding="utf-8") as file:
        file.write(render_markdown_report(records))

    return paths


def render_whatsapp_summary(records: list[DispatchRecord]) -> str:
    summary = build_report_summary(records)

    lines = [
        "Relatório de envio - Leads Ensino Superior",
        "",
        f"Total processado: {summary['total']}",
        f"Enviados: {summary['sent']}",
        f"Ignorados: {summary['skipped']}",
        f"Falhas: {summary['failed']}",
        "",
        "Por instância:",
    ]

    if summary["by_instance"]:
        for instance, total in summary["by_instance"].items():
            lines.append(f"- {instance}: {total} enviados")
    else:
        lines.append("- Nenhum envio registrado.")

    return "\n".join(lines)