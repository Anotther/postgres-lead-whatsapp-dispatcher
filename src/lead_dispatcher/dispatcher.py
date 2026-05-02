import time
from .lead_repository import fetch_leads
from .instance_pool import InstancePool, Instance
from .message_renderer import render_message


def run_dispatch():
    leads = fetch_leads(limit=50)

    pool = InstancePool([
        Instance("caixa-01", 30, 90),
        Instance("caixa-02", 45, 120),
    ])

    for lead in leads:
        while True:
            instance = pool.get_available_instance()

            if instance:
                break

            time.sleep(1)

        message = render_message(lead)

        print(f"[{instance.name}] Enviando para {lead['phone']}: {message}")

        # aqui depois entra o evolution_client

        pool.mark_sent(instance)