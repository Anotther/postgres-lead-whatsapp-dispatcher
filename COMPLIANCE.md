# Compliance

Este projeto processa dados pessoais de leads para envio operacional via WhatsApp. Use as orientações abaixo como requisitos mínimos antes de executar disparos reais.

## Dados pessoais

- Trate nome, telefone, e-mail, curso de interesse e histórico comercial como dados pessoais.
- Colete e processe apenas os campos necessários para selecionar leads elegíveis, montar mensagens e gerar relatórios operacionais.
- Não versionar bases reais, exports, relatórios com dados pessoais ou arquivos locais de configuração.

## Opt-in e elegibilidade

- Envie mensagens apenas para leads com opt-in/base legal válida para contato por WhatsApp.
- Exclua leads com venda iniciada, matrícula realizada, envio anterior ou qualquer restrição comercial equivalente.
- Mantenha a query em `config/lead_query.sql` alinhada às regras reais da base de origem.

## Segredos e configurações locais

- Use `.env` para credenciais e configurações de ambiente.
- Não versionar `.env`, `config/instances.yml`, `config/messages.yml` ou `config/lead_query.sql`.
- Rotacione chaves da Evolution API se houver suspeita de exposição.

## Logs e relatórios

- Mantenha `LOG_MASK_PHONE=true` em ambientes com dados reais.
- Mascarar telefones em logs, CSV, JSON e Markdown sempre que os arquivos puderem ser compartilhados.
- Trate qualquer arquivo em `reports/` como sensível, pois relatórios podem conter telefones, instâncias, motivos de falha e identificadores de leads.
- Não publique logs, relatórios ou exports gerados em execuções reais. O repositório deve manter apenas `.gitkeep` e exemplos sem dados pessoais.
- Armazene relatórios pelo menor tempo operacional necessário e remova arquivos antigos conforme a política da organização.

## Evolution API

- Restrinja a chave de API ao ambiente necessário.
- Evite usar nomes reais de instâncias em arquivos versionados.
- Valide limites de envio por instância antes de ativar execução real.

## Operação segura

- Execute primeiro com `DRY_RUN=true` para validar query, elegibilidade, templates, logs e relatórios.
- Revise uma amostra dos leads selecionados antes do primeiro disparo real.
- Só altere para `DRY_RUN=false` quando a base, as mensagens, o opt-in e os limites operacionais estiverem conferidos.
