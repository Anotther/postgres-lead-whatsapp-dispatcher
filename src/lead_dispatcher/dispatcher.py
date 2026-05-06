from __future__ import annotations

import logging
import select
import sys
import time
from typing import Any

from .dispatch_state import DispatchState
from .eligibility import check_lead_eligibility
from .evolution_client import EvolutionClient
from .instance_pool import InstancePool, apply_daily_counts, load_instances_config
from .lead_repository import fetch_leads
from .logging_config import setup_logging
from .message_renderer import render_message
from .reporting import DispatchRecord, render_whatsapp_summary, save_reports
from .settings import settings
from .utils import mask_phone, normalize_phone

logger = logging.getLogger(__name__)


def _lead_id(lead: dict[str, Any]) -> str | int | None:
    return lead.get("lead_id") or lead.get("id")


def _build_record(
    lead: dict[str, Any],
    *,
    phone: str | None,
    instance: str | None,
    message_id: str | None,
    status: str,
    reason: str | None = None,
    error: str | None = None,
    original_phone: str | None = None,
    normalized_phone: str | None = None,
    limit_override: bool = False,
) -> DispatchRecord:
    return DispatchRecord(
        lead_id=_lead_id(lead),
        full_name=lead.get("full_name"),
        phone=phone,
        instance=instance,
        message_id=message_id,
        status=status,
        reason=reason,
        error=error,
        original_phone=original_phone,
        normalized_phone=normalized_phone,
        limit_override=limit_override,
    )


def _ask_limit_override() -> bool:
    policy = str(getattr(settings, "dispatch_limit_override", "ask")).strip().lower()

    if policy == "always":
        logger.warning("Dispatch limit override enabled by configuration")
        return True

    if policy == "never":
        logger.warning("Dispatch stopped because all enabled instances reached limits")
        return False

    timeout = int(getattr(settings, "limit_override_prompt_timeout_seconds", 120))

    if not sys.stdin.isatty():
        logger.warning(
            "Dispatch limit override requires interactive terminal; stopping mailing"
        )
        return False

    print(
        "Todas as instâncias atingiram limite de envio. "
        f"Deseja continuar ultrapassando os limites nesta execução? [s/N] ({timeout}s): ",
        end="",
        flush=True,
    )

    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if not ready:
        print()
        logger.warning("Dispatch limit override prompt timed out; stopping mailing")
        return False

    answer = sys.stdin.readline().strip().lower()
    accepted = answer in {"s", "sim", "y", "yes"}

    if accepted:
        logger.warning("Dispatch limit override accepted by operator")
    else:
        logger.warning("Dispatch limit override declined by operator")

    return accepted


def _record_remaining_not_sent(
    records: list[DispatchRecord],
    leads: list[dict[str, Any]],
    *,
    start_index: int,
    reason: str = "all_instances_limit_reached",
    status: str = "not_sent_limit_reached",
) -> None:
    for lead in leads[start_index:]:
        phone = str(lead.get("phone") or "")
        phone_result = normalize_phone(
            phone,
            default_country_code=settings.default_country_code,
        )
        records.append(
            _build_record(
                lead,
                phone=phone_result.normalized or phone,
                instance=None,
                message_id=None,
                status=status,
                reason=reason,
                original_phone=phone,
                normalized_phone=phone_result.normalized,
            )
        )


def _send_whatsapp_summary(
    client: EvolutionClient,
    records: list[DispatchRecord],
) -> None:
    if not settings.report_send_whatsapp:
        return

    if not settings.report_recipient_number or not settings.report_recipient_instance:
        logger.error("Report WhatsApp summary not sent; recipient number or instance missing")
        return

    recipient_phone = normalize_phone(
        settings.report_recipient_number,
        default_country_code=settings.default_country_code,
    )
    if not recipient_phone.normalized:
        logger.error(
            "Report WhatsApp summary not sent; invalid recipient phone reason=%s",
            recipient_phone.reason,
        )
        return

    result = client.send_text(
        instance=settings.report_recipient_instance,
        number=recipient_phone.normalized,
        text=render_whatsapp_summary(records),
    )

    if result.success:
        logger.info(
            "Report WhatsApp summary sent instance=%s recipient=%s status_code=%s",
            settings.report_recipient_instance,
            mask_phone(recipient_phone.normalized),
            result.status_code,
        )
    else:
        logger.error(
            "Report WhatsApp summary failed instance=%s recipient=%s error=%s",
            settings.report_recipient_instance,
            mask_phone(recipient_phone.normalized),
            result.error,
        )


def run_dispatch():
    setup_logging()
    records: list[DispatchRecord] = []
    client = EvolutionClient()

    logger.info(
        "Starting dispatcher app=%s dry_run=%s",
        settings.app_name,
        str(settings.dry_run).lower(),
    )

    try:
        leads = fetch_leads(limit=settings.lead_limit)
        instances = load_instances_config()
        state = DispatchState()
        apply_daily_counts(
            instances,
            {instance.name: state.get_daily_count(instance.name) for instance in instances},
        )
        enabled_instances = [instance for instance in instances if instance.enabled]

        logger.info(
            "Loaded instances config path=%s enabled_instances=%s",
            settings.instances_config_path,
            len(enabled_instances),
        )

        pool = InstancePool(enabled_instances)
        limit_override = False

        if not pool.has_enabled_instances():
            logger.error("No enabled instances configured; mailing will not start")
            _record_remaining_not_sent(
                records,
                leads,
                start_index=0,
                reason="no_enabled_instances",
            )
            return records

        for index, lead in enumerate(leads):
            lead_id = _lead_id(lead)
            original_phone = str(lead.get("phone") or "")
            phone_result = normalize_phone(
                original_phone,
                default_country_code=settings.default_country_code,
            )

            if not phone_result.normalized:
                logger.info(
                    "Lead skipped lead_id=%s reason=%s",
                    lead_id,
                    phone_result.reason,
                )
                records.append(
                    _build_record(
                        lead,
                        phone=original_phone,
                        instance=None,
                        message_id=None,
                        status="skipped_invalid_phone",
                        reason=phone_result.reason,
                        original_phone=original_phone,
                    )
                )
                continue

            eligibility = check_lead_eligibility(
                {**lead, "phone": phone_result.normalized}
            )

            if not eligibility.is_eligible:
                logger.info("Lead skipped lead_id=%s reason=%s", lead_id, eligibility.reason)
                records.append(
                    _build_record(
                        lead,
                        phone=phone_result.normalized,
                        instance=None,
                        message_id=None,
                        status="skipped",
                        reason=eligibility.reason,
                        original_phone=original_phone,
                        normalized_phone=phone_result.normalized,
                    )
                )
                continue

            logger.info(
                "Lead eligible lead_id=%s phone=%s course=%s duration=%s",
                lead_id,
                mask_phone(phone_result.normalized),
                lead.get("course_interest") or "",
                lead.get("duration_interest") or "",
            )

            while True:
                instance = pool.get_available_instance(ignore_limits=limit_override)

                if instance:
                    break

                if not limit_override and pool.all_enabled_instances_at_limit():
                    if _ask_limit_override():
                        limit_override = True
                        continue

                    logger.warning(
                        "Mailing stopped; all enabled instances reached limits"
                    )
                    _record_remaining_not_sent(records, leads, start_index=index)
                    return records

                next_instance = pool.next_available_instance(ignore_limits=limit_override)
                if next_instance:
                    wait_seconds = max(1, int(next_instance.next_available_at - time.time()))
                    logger.info(
                        "No available instance; waiting next_available_instance=%s "
                        "wait_seconds=%s",
                        next_instance.name,
                        wait_seconds,
                    )
                    time.sleep(min(wait_seconds, 5))
                else:
                    logger.info("No available instance; waiting wait_seconds=1")
                    time.sleep(1)

            try:
                message_id, message = render_message(
                    {**lead, "phone": phone_result.normalized}
                )
            except Exception as exc:
                logger.exception("Message rendering failed lead_id=%s", lead_id)
                records.append(
                    _build_record(
                        lead,
                        phone=phone_result.normalized,
                        instance=instance.name,
                        message_id=None,
                        status="failed",
                        reason="message_rendering_failed",
                        error=str(exc),
                        original_phone=original_phone,
                        normalized_phone=phone_result.normalized,
                        limit_override=limit_override,
                    )
                )
                if settings.stop_on_critical_error:
                    return records
                continue

            logger.info(
                "Rendered message lead_id=%s template=%s phone=%s",
                lead_id,
                message_id,
                mask_phone(phone_result.normalized),
            )

            if settings.dry_run:
                logger.info(
                    "Dry-run enabled; message not sent lead_id=%s instance=%s phone=%s",
                    lead_id,
                    instance.name,
                    mask_phone(phone_result.normalized),
                )
                pool.mark_sent(instance)
                state.increment_daily_count(instance.name)
                records.append(
                    _build_record(
                        lead,
                        phone=phone_result.normalized,
                        instance=instance.name,
                        message_id=message_id,
                        status="sent",
                        original_phone=original_phone,
                        normalized_phone=phone_result.normalized,
                        limit_override=limit_override,
                    )
                )
            else:
                result = client.send_text(
                    instance=instance.name,
                    number=phone_result.normalized,
                    text=message,
                )
                if result.success:
                    logger.info(
                        "Message sent lead_id=%s instance=%s phone=%s status_code=%s",
                        lead_id,
                        instance.name,
                        mask_phone(phone_result.normalized),
                        result.status_code,
                    )
                    pool.mark_sent(instance)
                    state.increment_daily_count(instance.name)
                    records.append(
                        _build_record(
                            lead,
                            phone=phone_result.normalized,
                            instance=instance.name,
                            message_id=message_id,
                            status="sent",
                            original_phone=original_phone,
                            normalized_phone=phone_result.normalized,
                            limit_override=limit_override,
                        )
                    )
                else:
                    logger.error(
                        "Message failed lead_id=%s instance=%s phone=%s error=%s",
                        lead_id,
                        instance.name,
                        mask_phone(phone_result.normalized),
                        result.error,
                    )
                    records.append(
                        _build_record(
                            lead,
                            phone=phone_result.normalized,
                            instance=instance.name,
                            message_id=message_id,
                            status="failed",
                            reason="send_failed",
                            error=result.error,
                            original_phone=original_phone,
                            normalized_phone=phone_result.normalized,
                            limit_override=limit_override,
                        )
                    )
                    if settings.stop_on_critical_error:
                        return records

        return records
    except KeyboardInterrupt:
        logger.warning("Dispatcher interrupted by operator; generating partial reports")
        _record_remaining_not_sent(
            records,
            leads if "leads" in locals() else [],
            start_index=index if "index" in locals() else len(records),
            reason="operator_interrupted",
            status="interrupted",
        )
        return records
    finally:
        paths = save_reports(records)
        logger.info(
            "Reports generated %s",
            " ".join(f"{name}={path}" for name, path in paths.items()),
        )
        _send_whatsapp_summary(client, records)
