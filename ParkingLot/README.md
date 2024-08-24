# Estrutura e Fluxo do Sistema de Estacionamento

# Especificação do Projeto

## Sistema de Gerenciamento de Vagas

**Manager:**
- **Função:** Manter visão geral das vagas e registro das estações ativas.
- **Implementação:**
  - NAO REALIZA NADA. Apenas observa e registra.
  - Registrar as estações ativas e suas vagas (recebe informações das estações).
  - Quando uma estação falha, envia mensagem para quem disparou a eleição contendo as vagas da estação falha.
  - Definir como zmq vai funcionar para comunicação entre as estações.

**Middleware (Estação):**
- **Função:** Gerenciar vagas locais e atender solicitações de carros.
- **Implementação:**
  - Estabelece comunicação broadcast com todas as estações.
  - Estabelece comunicação com o gerente.
  - Registrar vagas locais, se necessario, informar quais vagas sobraram para a estação que solicitou e atualizar o gerente.
  - Realizar ping constante para entre si e em caso de falha, disparar eleição.
  - Na eleição:
    - a estação com menos vagas deve assumir as vagas da estação falha
  - Alocar vagas para carros (threads)
    - Se possui vagas disponiveis locais, alocar para o carro. (será um dicionario com id do carro e vaga alocada)
    - Se não possui vagas disponiveis, solicitar vagas adicionais para as outras estações (informar a outra estação que a vaga foi alocada).
    - Quando a vaga é liberada, informar a estação que a vaga foi liberada. 
  - Implementar comunicação eficiente entre estações (usar zmq ?).

## Fluxo do Sistema

### Inicialização
- O Gerente começa com todas as N vagas disponíveis e printa um txt com o nome ip e porta de cada estação.
- Estações são inicializadas com zero vagas e estão todas inativas

### Registro
- Quando uma estação inicia, ocorre a distribuição de vagas por broadcast das informações entre middlewares
- Quando as vagas sao alocadas, o gerente é informado das alocações (alem da station que acabou de ser ativada, quem cedeu as vagas também é informado)
- As vagas efetivamente de cada estação ficam no controle local alem das conexoes com as outras estações ativas

### Alocação de Vagas
- Quando um carro chega à estação, a estação tenta alocar uma vaga de sua própria reserva.
- Se não houver vagas disponíveis, a estação solicita vagas adicionais aos middlewares vizinhos.
- A vaga da outra estação é alocada para o carro e a estação vizinha é informada da alocação, mas continua sendo uma vaga da outra estação.
- Se não houver vagas disponíveis, o carro deve esperar, iniciando um temporizador (sistema que não deve ter starvations).
- A medida que as vagas são liberadas, os carros que chegarão primeiro devem ser alocados primeiro.
- O passo mais crítico é uma boa comunicação entre as estações para que a alocação de vagas seja eficiente.

### Balanceamento de Carga (Eleição) 
- O gerente é um mero observador e não interfere na alocação de vagas
- Existe um sistema de ping constante feito por broadcast para verificar se as estações estão ativas.
  - Definir o Tempo de tolarancia e quem dispara a eleição.
- O balanceamento deve ser feito baseado em eleições.
  - Se uma estação falhar (tolerancia a falhas), a estação com menos vagas deve assumir as vagas da estação falha (se possível).
  - Se uma nova estação for adicionada, pegar as duas estações com mais vagas e dividir igualmente entre as três.
  - Ex: o sistema inicia com 10 vagas e 3 estações inativas. Quando a primeira estação ativa, passa a controlar as 10 vagas. Quando a segunda estação ativa, a primeira estação passa a controlar 5 vagas e a segunda 5 também. Quando a terceira ativa, como quem cede é quem tem mais e nesse caso há empate, a primeira estação que for encontrada cede N // 2 vagas para a nova estação.
