from lead_dispatcher import dispatcher
from lead_dispatcher.evolution_client import InstanceStatusResult, SendMessageResult
from lead_dispatcher.instance_pool import Instance


class FakeEvolutionClient:
    instances = []

    def __init__(self):
        self.sent = []
        self.__class__.instances.append(self)

    def send_text(self, *, instance, number, text, delay=0, link_preview=False):
        self.sent.append(
            {
                "instance": instance,
                "number": number,
                "text": text,
                "delay": delay,
                "link_preview": link_preview,
            }
        )
        return SendMessageResult(
            success=True,
            instance=instance,
            number=number,
            status_code=200,
        )

    def get_instance_status(self, instance):
        return InstanceStatusResult(
            success=True,
            instance=instance,
            connected=True,
            state="open",
            status_code=200,
        )


class FakeDispatchState:
    def __init__(self):
        self.counts = {}

    def get_daily_count(self, instance_name):
        return self.counts.get(instance_name, 0)

    def increment_daily_count(self, instance_name):
        self.counts[instance_name] = self.get_daily_count(instance_name) + 1


def test_run_dispatch_generates_reports_and_sends_summary(tmp_path, monkeypatch):
    FakeEvolutionClient.instances = []
    monkeypatch.setattr(dispatcher.settings, "report_dir", str(tmp_path))
    monkeypatch.setattr(dispatcher.settings, "report_formats", "csv,json")
    monkeypatch.setattr(dispatcher.settings, "dry_run", False)
    monkeypatch.setattr(dispatcher.settings, "report_send_whatsapp", True)
    monkeypatch.setattr(dispatcher.settings, "report_recipient_number", "41995306821")
    monkeypatch.setattr(dispatcher.settings, "report_recipient_instance", "caixa-01")
    monkeypatch.setattr(dispatcher.settings, "default_country_code", "55")
    monkeypatch.setattr(dispatcher.settings, "stop_on_critical_error", False)
    monkeypatch.setattr(dispatcher.settings, "lead_limit", 10)
    monkeypatch.setattr(dispatcher, "setup_logging", lambda: None)
    monkeypatch.setattr(
        dispatcher,
        "fetch_leads",
        lambda: [
            {
                "lead_id": 1,
                "full_name": "Ana Silva",
                "phone": "41995306821",
                "opt_in_whatsapp": True,
            },
            {
                "lead_id": 2,
                "full_name": "Contato Invalido",
                "phone": "ABC",
                "opt_in_whatsapp": True,
            },
        ],
    )
    monkeypatch.setattr(
        dispatcher,
        "load_instances_config",
        lambda: [Instance("caixa-01", 1, 1, run_limit=10, daily_limit=10)],
    )
    monkeypatch.setattr(dispatcher, "DispatchState", FakeDispatchState)
    monkeypatch.setattr(dispatcher, "EvolutionClient", FakeEvolutionClient)
    monkeypatch.setattr(dispatcher, "render_message", lambda lead: ("template-1", "Oi"))

    records = dispatcher.run_dispatch()

    assert [record.status for record in records] == ["sent", "skipped_invalid_phone"]
    assert records[0].normalized_phone == "5541995306821"
    assert len(FakeEvolutionClient.instances[0].sent) == 2
    assert FakeEvolutionClient.instances[0].sent[0]["number"] == "5541995306821"
    assert FakeEvolutionClient.instances[0].sent[1]["number"] == "5541995306821"
    assert list(tmp_path.glob("send_report_*.csv"))
    assert not list(tmp_path.glob("send_report_*.json"))
    assert list(tmp_path.glob("sent_contacts_*.csv"))
    assert list(tmp_path.glob("failed_contacts_*.csv"))


def test_run_dispatch_marks_remaining_records_when_limits_are_reached(tmp_path, monkeypatch):
    monkeypatch.setattr(dispatcher.settings, "report_dir", str(tmp_path))
    monkeypatch.setattr(dispatcher.settings, "report_formats", "csv")
    monkeypatch.setattr(dispatcher.settings, "dry_run", True)
    monkeypatch.setattr(dispatcher.settings, "report_send_whatsapp", False)
    monkeypatch.setattr(dispatcher.settings, "default_country_code", "55")
    monkeypatch.setattr(dispatcher.settings, "lead_limit", 10)
    monkeypatch.setattr(dispatcher, "setup_logging", lambda: None)
    monkeypatch.setattr(
        dispatcher,
        "fetch_leads",
        lambda: [
            {"lead_id": 1, "full_name": "Ana", "phone": "41995306821"},
            {"lead_id": 2, "full_name": "Bruno", "phone": "41995306822"},
        ],
    )
    monkeypatch.setattr(
        dispatcher,
        "load_instances_config",
        lambda: [Instance("caixa-01", 1, 1, run_limit=1)],
    )
    monkeypatch.setattr(dispatcher, "DispatchState", FakeDispatchState)
    monkeypatch.setattr(dispatcher, "EvolutionClient", FakeEvolutionClient)
    monkeypatch.setattr(dispatcher, "render_message", lambda lead: ("template-1", "Oi"))
    monkeypatch.setattr(dispatcher, "_ask_limit_override", lambda: False)

    records = dispatcher.run_dispatch()

    assert [record.status for record in records] == ["sent", "not_sent_limit_reached"]
    assert records[1].reason == "all_instances_limit_reached"
    assert list(tmp_path.glob("failed_contacts_*.csv"))


def test_run_dispatch_handles_keyboard_interrupt_while_waiting(tmp_path, monkeypatch):
    monkeypatch.setattr(dispatcher.settings, "report_dir", str(tmp_path))
    monkeypatch.setattr(dispatcher.settings, "report_formats", "csv")
    monkeypatch.setattr(dispatcher.settings, "dry_run", True)
    monkeypatch.setattr(dispatcher.settings, "report_send_whatsapp", False)
    monkeypatch.setattr(dispatcher.settings, "default_country_code", "55")
    monkeypatch.setattr(dispatcher.settings, "lead_limit", 10)
    monkeypatch.setattr(dispatcher, "setup_logging", lambda: None)
    monkeypatch.setattr(
        dispatcher,
        "fetch_leads",
        lambda: [
            {"lead_id": 1, "full_name": "Ana", "phone": "41995306821"},
            {"lead_id": 2, "full_name": "Bruno", "phone": "41995306822"},
        ],
    )
    monkeypatch.setattr(
        dispatcher,
        "load_instances_config",
        lambda: [Instance("caixa-01", 30, 30)],
    )
    monkeypatch.setattr(dispatcher, "DispatchState", FakeDispatchState)
    monkeypatch.setattr(dispatcher, "EvolutionClient", FakeEvolutionClient)
    monkeypatch.setattr(dispatcher, "render_message", lambda lead: ("template-1", "Oi"))

    def interrupt(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(dispatcher.time, "sleep", interrupt)

    records = dispatcher.run_dispatch()

    assert [record.status for record in records] == ["sent", "interrupted"]
    assert records[1].reason == "operator_interrupted"
    assert list(tmp_path.glob("failed_contacts_*.csv"))


def test_run_dispatch_uses_lead_limit_as_send_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(dispatcher.settings, "report_dir", str(tmp_path))
    monkeypatch.setattr(dispatcher.settings, "report_formats", "csv")
    monkeypatch.setattr(dispatcher.settings, "dry_run", True)
    monkeypatch.setattr(dispatcher.settings, "report_send_whatsapp", False)
    monkeypatch.setattr(dispatcher.settings, "default_country_code", "55")
    monkeypatch.setattr(dispatcher.settings, "lead_limit", 1)
    monkeypatch.setattr(dispatcher, "setup_logging", lambda: None)
    monkeypatch.setattr(
        dispatcher,
        "fetch_leads",
        lambda: [
            {"lead_id": 1, "full_name": "Ana", "phone": "41995306821"},
            {"lead_id": 2, "full_name": "Bruno", "phone": "41995306822"},
            {"lead_id": 3, "full_name": "Carla", "phone": "41995306823"},
        ],
    )
    monkeypatch.setattr(
        dispatcher,
        "load_instances_config",
        lambda: [Instance("caixa-01", 1, 1, run_limit=10)],
    )
    monkeypatch.setattr(dispatcher, "DispatchState", FakeDispatchState)
    monkeypatch.setattr(dispatcher, "EvolutionClient", FakeEvolutionClient)
    monkeypatch.setattr(dispatcher, "render_message", lambda lead: ("template-1", "Oi"))

    records = dispatcher.run_dispatch()

    assert [record.status for record in records] == [
        "sent",
        "not_sent_limit_reached",
        "not_sent_limit_reached",
    ]
    assert records[1].reason == "lead_limit_reached"


def test_estimate_dispatch_seconds_uses_average_delay_for_single_instance():
    instance = Instance("caixa-01", 45, 120, run_limit=10)

    assert dispatcher._estimate_dispatch_seconds(4, [instance]) == 247.5


def test_run_dispatch_stops_when_instance_is_not_connected(tmp_path, monkeypatch):
    class OfflineEvolutionClient(FakeEvolutionClient):
        def get_instance_status(self, instance):
            return InstanceStatusResult(
                success=True,
                instance=instance,
                connected=False,
                state="close",
                status_code=200,
            )

    OfflineEvolutionClient.instances = []
    monkeypatch.setattr(dispatcher.settings, "report_dir", str(tmp_path))
    monkeypatch.setattr(dispatcher.settings, "report_formats", "csv")
    monkeypatch.setattr(dispatcher.settings, "dry_run", False)
    monkeypatch.setattr(dispatcher.settings, "report_send_whatsapp", False)
    monkeypatch.setattr(dispatcher.settings, "default_country_code", "55")
    monkeypatch.setattr(dispatcher.settings, "lead_limit", 10)
    monkeypatch.setattr(dispatcher, "setup_logging", lambda: None)
    monkeypatch.setattr(
        dispatcher,
        "fetch_leads",
        lambda: [
            {"lead_id": 1, "full_name": "Ana", "phone": "41995306821"},
            {"lead_id": 2, "full_name": "Bruno", "phone": "41995306822"},
        ],
    )
    monkeypatch.setattr(
        dispatcher,
        "load_instances_config",
        lambda: [Instance("caixa-01", 1, 1, run_limit=10)],
    )
    monkeypatch.setattr(dispatcher, "DispatchState", FakeDispatchState)
    monkeypatch.setattr(dispatcher, "EvolutionClient", OfflineEvolutionClient)

    records = dispatcher.run_dispatch()

    assert [record.status for record in records] == [
        "not_sent_limit_reached",
        "not_sent_limit_reached",
    ]
    assert records[0].reason == "instance_not_connected"
    assert OfflineEvolutionClient.instances[0].sent == []


def test_run_dispatch_logs_single_delay_wait(tmp_path, monkeypatch, caplog):
    FakeEvolutionClient.instances = []
    monkeypatch.setattr(dispatcher.settings, "report_dir", str(tmp_path))
    monkeypatch.setattr(dispatcher.settings, "report_formats", "csv")
    monkeypatch.setattr(dispatcher.settings, "dry_run", True)
    monkeypatch.setattr(dispatcher.settings, "report_send_whatsapp", False)
    monkeypatch.setattr(dispatcher.settings, "default_country_code", "55")
    monkeypatch.setattr(dispatcher.settings, "lead_limit", 10)
    monkeypatch.setattr(dispatcher, "setup_logging", lambda: None)
    monkeypatch.setattr(
        dispatcher,
        "fetch_leads",
        lambda: [
            {"lead_id": 1, "full_name": "Ana", "phone": "41995306821"},
            {"lead_id": 2, "full_name": "Bruno", "phone": "41995306822"},
        ],
    )
    monkeypatch.setattr(
        dispatcher,
        "load_instances_config",
        lambda: [Instance("caixa-01", 30, 30)],
    )
    monkeypatch.setattr(dispatcher, "DispatchState", FakeDispatchState)
    monkeypatch.setattr(dispatcher, "EvolutionClient", FakeEvolutionClient)
    monkeypatch.setattr(dispatcher, "render_message", lambda lead: ("template-1", "Oi"))

    def interrupt(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(dispatcher, "_sleep_quietly", interrupt)

    with caplog.at_level("INFO"):
        records = dispatcher.run_dispatch()

    delay_logs = [
        record for record in caplog.records
        if "Instance in delay" in record.getMessage()
    ]

    assert [record.status for record in records] == ["sent", "interrupted"]
    assert len(delay_logs) == 1
