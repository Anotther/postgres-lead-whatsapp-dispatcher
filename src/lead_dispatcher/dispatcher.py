from __future__ import annotations

import logging
import time

from .eligibility import check_lead_eligibility
from .evolution_client import EvolutionClient
from .instance_pool import InstancePool, load_instances_config
from .lead_repository import fetch_leads
from .logging_config import setup_logging
from .message_renderer import render_message
from .settings import settings
from .utils import mask_phone

logger = logging.getLogger(__name__)


def run_dispatch():
    setup_logging()

    logger.info(
        "Starting dispatcher app=%s dry_run=%s",
        settings.app_name,
        str(settings.dry_run).lower(),
    )

    leads = fetch_leads(limit=settings.lead_limit)
    instances = load_instances_config()
    enabled_instances = [instance for instance in instances if instance.enabled]

    logger.info(
        "Loaded instances config path=%s enabled_instances=%s",
        settings.instances_config_path,
        len(enabled_instances),
    )

    pool = InstancePool(enabled_instances)
    client = EvolutionClient()

    for lead in leads:
        lead_id = lead.get("lead_id") or lead.get("id")
        phone = str(lead.get("phone") or "")
        eligibility = check_lead_eligibility(lead)

        if not eligibility.is_eligible:
            logger.info("Lead skipped lead_id=%s reason=%s", lead_id, eligibility.reason)
            continue

        logger.info(
            "Lead eligible lead_id=%s phone=%s course=%s duration=%s",
            lead_id,
            mask_phone(phone),
            lead.get("course_interest") or "",
            lead.get("duration_interest") or "",
        )

        while True:
            instance = pool.get_available_instance()

            if instance:
                break

            logger.info("No available instance; waiting wait_seconds=1")
            time.sleep(1)

        message_id, message = render_message(lead)

        logger.info(
            "Rendered message lead_id=%s template=%s phone=%s",
            lead_id,
            message_id,
            mask_phone(phone),
        )

        if settings.dry_run:
            logger.info(
                "Dry-run enabled; message not sent lead_id=%s instance=%s phone=%s",
                lead_id,
                instance.name,
                mask_phone(phone),
            )
        else:
            result = client.send_text(
                instance=instance.name,
                number=phone,
                text=message,
            )
            if result.success:
                logger.info(
                    "Message sent lead_id=%s instance=%s phone=%s status_code=%s",
                    lead_id,
                    instance.name,
                    mask_phone(phone),
                    result.status_code,
                )
            else:
                logger.error(
                    "Message failed lead_id=%s instance=%s phone=%s error=%s",
                    lead_id,
                    instance.name,
                    mask_phone(phone),
                    result.error,
                )

        pool.mark_sent(instance)
