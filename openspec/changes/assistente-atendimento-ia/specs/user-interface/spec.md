# Spec Delta

## Purpose

Fornece interfaces para operação do assistente de atendimento ao cliente, abrangendo uma interface de linha de comando (CLI) obrigatória e uma interface web demonstrativa para testes visuais.

## ADDED Requirements

### Requirement: Interface de linha de comando (CLI) completa
O sistema MUST disponibilizar uma CLI interativa e parametrizável via terminal para controle total das operações do assistente, permitindo execução de comandos com suporte a flags de configuração.

#### Scenario: Comando de geração de conteúdo via CLI
- **WHEN** o usuário executar o comando de geração especificando a entrada do cliente, o perfil e o tipo de conteúdo desejado
- **THEN** a CLI SHALL exibir a resposta formatada no terminal e informar o status de persistência e uso de cache

#### Scenario: Comando de comparação de versões via CLI
- **WHEN** o usuário executar o comando de comparação passando o caso de teste e as versões de prompt
- **THEN** a CLI SHALL apresentar uma tabela comparativa com as notas da rubrica oficial e o veredito de desempenho

#### Scenario: Listagem de perfis disponíveis via CLI
- **WHEN** o usuário acionar o comando de listagem de perfis
- **THEN** a CLI SHALL exibir todos os perfis JSON configurados com seus identificadores, nomes e características centrais

### Requirement: Tratamento de erros e feedback amigável na CLI
A CLI MUST interceptar exceções (como chaves de API ausentes, arquivos inexistentes ou falhas de conexão) e apresentar mensagens de erro compreensíveis com código de saída apropriado.

#### Scenario: Execução da CLI sem configuração de API key
- **WHEN** um comando de geração for disparado sem que a variável de ambiente com a chave de API esteja configurada
- **THEN** a CLI SHALL alertar o usuário sobre a ausência da credencial e sugerir a configuração no arquivo .env

### Requirement: Interface web demonstrativa para visualização
O sistema MUST oferecer uma interface web leve e acessível localmente para demonstração das capacidades do assistente e visualização rica dos fluxogramas e comparações.

#### Scenario: Acesso à interface web local
- **WHEN** o servidor da interface web for iniciado
- **THEN** a aplicação SHALL carregar visualmente opções para seleção de perfil de cliente, entrada de mensagem, abas para os quatro conteúdos e renderização gráfica de diagramas
