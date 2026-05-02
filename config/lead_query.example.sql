/*
Query exemplo para buscar leads elegíveis para contato.

Copie este arquivo para:
config/lead_query.sql

Ajuste nomes de tabelas, colunas e status conforme a base real.

Contrato esperado pelo Python:
- lead_id
- full_name
- phone
- email
- course_interest
- created_at

Regras recomendadas:
- telefone obrigatório
- opt-in/base legal para WhatsApp
- sem venda iniciada
- sem matrícula realizada
- ordenação pelos leads mais antigos ou prioridade comercial
*/

SELECT
    l.id AS lead_id,
    l.full_name,
    l.phone,
    l.email,
    l.course_interest,
    l.created_at
FROM leads l
LEFT JOIN sales_opportunities so
    ON so.lead_id = l.id
    AND so.status IN (
        'started',
        'in_progress',
        'won'
    )
LEFT JOIN enrollments e
    ON e.lead_id = l.id
    AND e.status IN (
        'active',
        'completed'
    )
WHERE
    l.phone IS NOT NULL
    AND l.phone <> ''
    AND l.opt_in_whatsapp = true
    AND so.id IS NULL
    AND e.id IS NULL
ORDER BY
    l.created_at ASC
LIMIT %(lead_limit)s;