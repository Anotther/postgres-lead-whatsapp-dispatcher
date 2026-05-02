import random


MESSAGES = [
    "Olá {name}, tudo bem?",
    "Oi {name}, vi seu interesse em cursos superiores.",
    "Olá {name}, posso te ajudar com sua inscrição?"
]


def render_message(lead: dict) -> str:
    template = random.choice(MESSAGES)
    return template.format(name=lead["name"].split()[0])