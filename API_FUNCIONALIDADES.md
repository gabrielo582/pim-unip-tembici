# API de Rastreamento e Manutenção de Bicicletas

## Visão geral

Esta API foi pensada para acompanhar bicicletas em uso, registrar manutenções e apoiar decisões de manutenção preventiva.

Na prática, ela cobre três frentes principais:

- rastreamento de deslocamento da bicicleta
- cadastro de bicicletas e componentes
- análise de uso e desgaste para manutenção

## O que a API permite fazer

### 1. Registrar a posição de uma bicicleta ao longo do tempo

A API recebe pontos de localização com latitude, longitude, altitude, velocidade e identificador do dispositivo.

Endpoint principal:

- `POST /location`

Finalidade:

- salvar a posição atual enviada por um dispositivo
- associar o ponto a uma bicicleta
- montar o histórico de deslocamento usado nos relatórios

Comportamentos importantes:

- se o novo ponto estiver muito próximo do último ponto do mesmo dispositivo, ele pode ser ignorado
- se o `bike_id` não for enviado, a API tenta reaproveitar a última bicicleta associada ao dispositivo

Também é possível consultar o histórico bruto de um dispositivo:

- `GET /locations/{device_id}`

Esse retorno traz a trilha registrada com latitude, longitude, velocidade e data de criação.

### 2. Consultar quais dispositivos já enviaram localização

Endpoint:

- `GET /devices`

Finalidade:

- listar os identificadores de dispositivos que já registraram pontos
- facilitar integrações, monitoramento e consultas posteriores

### 3. Cadastrar e gerenciar bicicletas

Endpoints:

- `POST /bikes`
- `GET /bikes`
- `GET /bikes/{bike_id}`
- `PUT /bikes/{bike_id}`
- `DELETE /bikes/{bike_id}`

Finalidade:

- criar bicicletas no sistema
- listar bicicletas existentes
- consultar detalhes de uma bicicleta
- renomear uma bicicleta
- remover uma bicicleta

Uso típico:

1. cadastrar a bicicleta
2. usar o `bike_id` ao enviar localizações
3. usar o mesmo `bike_id` para registrar manutenções e relatórios

### 4. Cadastrar e gerenciar componentes

Endpoints:

- `POST /components`
- `GET /components`
- `GET /components/{component_id}`
- `PUT /components/{component_id}`
- `DELETE /components/{component_id}`

Finalidade:

- manter o catálogo de peças e componentes monitorados
- permitir que manutenções sejam associadas ao componente correto

Diferencial funcional:

- ao consultar componentes, a API também informa a média de vida útil observada daquele componente com base nas manutenções já registradas

Campo funcional retornado:

- `average_component_life_effort`

Esse valor ajuda a entender, em termos médios, quanto esforço um componente costuma suportar antes de precisar de nova manutenção.

### 5. Registrar e gerenciar manutenções

Endpoints:

- `POST /maintenances`
- `GET /maintenances`
- `GET /maintenances/{maintenance_id}`
- `PUT /maintenances/{maintenance_id}`
- `DELETE /maintenances/{maintenance_id}`

Finalidade:

- registrar quando uma manutenção ocorreu
- associar a manutenção a uma bicicleta e a um componente
- armazenar custo, tipo e data da manutenção
- calcular automaticamente a vida útil consumida até aquela manutenção

Campos funcionais usados no cadastro:

- `bike_id`
- `bike_component_id`
- `maintenance_type`
- `maintenance_cost`
- `maintenance_start_date`

Comportamento importante:

- ao criar ou atualizar uma manutenção, a API calcula o `life_effort`
- esse cálculo representa o esforço acumulado da bicicleta para aquele componente desde a última manutenção até a data atual da manutenção

Na prática, isso transforma cada manutenção em um marco de desgaste real do componente.

### 6. Gerar relatório preditivo de manutenção

Endpoint:

- `GET /predictive-report/{bike_id}`

Finalidade:

- analisar todos os componentes cadastrados para uma bicicleta
- comparar o uso recente com a vida útil média esperada
- indicar quais componentes exigem atenção

O relatório devolve, para cada componente:

- data da última manutenção
- esforço acumulado desde a última manutenção
- média de vida útil do componente
- percentual de uso dessa vida útil
- alerta e status de criticidade
- mensagem interpretativa

Faixas de alerta:

- abaixo de 70%: situação verde
- entre 70% e 90%: atenção
- acima de 90%: situação crítica

Esse endpoint é o núcleo da manutenção preditiva da API.

### 7. Gerar relatório histórico de uso da bicicleta

Endpoint:

- `GET /bike-report/{bike}`

Finalidade:

- resumir o uso histórico de uma bicicleta a partir dos pontos de localização
- consolidar distância, velocidade média, ganho de altitude e esforço
- agrupar o histórico por dia

O relatório entrega:

- resumo total da bicicleta
- histórico diário
- esforço total estimado

Esse endpoint é útil para acompanhamento operacional e para dar contexto aos relatórios de manutenção.

## Como a API interpreta o uso da bicicleta

A API não trabalha apenas com distância percorrida.

Ela calcula um indicador chamado `effort`, que representa o esforço de uso da bicicleta levando em conta:

- distância percorrida
- velocidade entre pontos
- ganho de altitude

Isso permite que o sistema trate subidas, deslocamentos mais intensos e uso acumulado de forma mais realista do que um simples odômetro.

## Regras de negócio importantes

### Filtro de pontos muito próximos

Para evitar ruído no rastreamento, a API pode ignorar pontos quase idênticos ao último ponto salvo para o mesmo dispositivo.

### Continuidade por dispositivo

Se um dispositivo continuar enviando pontos sem repetir a bicicleta, a API tenta manter a associação da última bicicleta usada.

### Segmentação de trajetos

Os pontos de localização são agrupados em viagens contínuas.

Se houver uma pausa relevante entre dois pontos, a API entende que começou uma nova viagem. Isso evita somar esforço de trechos desconectados como se fossem um deslocamento único.

### Vida útil do componente

A API trabalha com dois conceitos complementares:

- `life_effort` de uma manutenção: esforço real acumulado até aquela manutenção
- `average_component_life_effort`: média histórica de vida útil do componente entre todas as bicicletas

Esses dois valores permitem comparar uso atual com histórico observado.

## Fluxo funcional recomendado

Um fluxo comum de uso da API é:

1. cadastrar bicicletas
2. cadastrar componentes
3. começar a enviar localizações com `POST /location`
4. registrar manutenções sempre que um componente for revisado ou trocado
5. consultar `GET /predictive-report/{bike_id}` para identificar componentes próximos do limite
6. consultar `GET /bike-report/{bike}` para entender o histórico consolidado de uso

## Resumo das funcionalidades por rota

| Rota | Função |
| --- | --- |
| `POST /location` | Registra um novo ponto de localização |
| `GET /locations/{device_id}` | Consulta o histórico de pontos de um dispositivo |
| `GET /devices` | Lista dispositivos que já enviaram localização |
| `POST /bikes` | Cadastra uma bicicleta |
| `GET /bikes` | Lista bicicletas |
| `GET /bikes/{bike_id}` | Consulta uma bicicleta |
| `PUT /bikes/{bike_id}` | Atualiza uma bicicleta |
| `DELETE /bikes/{bike_id}` | Remove uma bicicleta |
| `POST /components` | Cadastra um componente |
| `GET /components` | Lista componentes com média de vida útil |
| `GET /components/{component_id}` | Consulta um componente com média de vida útil |
| `PUT /components/{component_id}` | Atualiza um componente |
| `DELETE /components/{component_id}` | Remove um componente |
| `POST /maintenances` | Registra uma manutenção |
| `GET /maintenances` | Lista manutenções |
| `GET /maintenances/{maintenance_id}` | Consulta uma manutenção |
| `PUT /maintenances/{maintenance_id}` | Atualiza uma manutenção |
| `DELETE /maintenances/{maintenance_id}` | Remove uma manutenção |
| `GET /predictive-report/{bike_id}` | Gera o relatório preditivo de manutenção |
| `GET /bike-report/{bike}` | Gera o relatório histórico consolidado da bicicleta |

