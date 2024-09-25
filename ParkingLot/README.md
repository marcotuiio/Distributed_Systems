# Estrutura e Fluxo do Sistema de Estacionamento
### Marco Túlio Alves de Barros - 202100560105

# Visão Geral
  Este projeto simula um sistema de estacionamento distribuído onde várias estações gerenciam vagas de estacionamento e se comunicam entre si para alocar, emprestar e liberar vagas. O sistema é composto por três componentes principais:

**Gerente (Manager):** Supervisiona todo o sistema, mantém o controle do status de todas as estações e lida com operações de alto nível.
**Estação (Station):** Gerencia um número definido de vagas de estacionamento e se comunica com outras estações para emprestar ou pegar emprestado vagas.
**Aplicativo (App):** Fornece uma interface para que requisições externas interajam com o sistema.

# Componentes

## Gerente
  O componente Manager é responsável por supervisionar todo o sistema. Ele mantém o controle do status de todas as estações e lida com operações de alto nível, como imprimir o status de todas as estações em um arquivo.

  - Inicialização: Configura o contexto e o socket ZeroMQ, dando bind na porta 5555 e esperando que todas as estações se conectem.
  - Manipulação de Requisições: Escuta requisições das estações e as processa, sendo essencial para backup das estação se falahrem, retornar quantas vagas o estacionamento possui e informar quais são as estações ativas.

## Estação
  O componente Station gerencia um número definido de vagas de estacionamento e se comunica com outras estações para emprestar ou pegar emprestado vagas. Cada estação opera de forma independente e pode lidar com múltiplas requisições simultaneamente (apesar de estar limitado ao tempo de escalonamento de threads do sistema operacional).

  - Inicialização: Configura o contexto e os sockets ZeroMQ, inicializa as vagas de estacionamento e inicia as threads de trabalho (receber mensagens externas, processar mensagens externas, receber mensagens internas e processar mensagens internas e ping).
  - Manipulação de Mensagens: Processa diferentes tipos de mensagens, como requisições de carros, requisições de empréstimo e requisições de liberação.
  - Empréstimo de Vagas: Envia requisições para outras estações para pegar vagas emprestadas e espera por confirmações.
  - Liberação de Vagas: Lida com a liberação de vagas e atualiza o gerente.

## Aplicativo
  O componente App fornece uma interface para que requisições externas interajam com o sistema. Ele escuta requisições recebidas e as encaminha para a estação apropriada.

  - Inicialização: Configura o contexto e o socket ZeroMQ.
  - Manipulação de Requisições: Escuta requisições recebidas e as encaminha para a estação apropriada.

# Fluxo de Mensagens

## Ativação de Estação
  - Estação: Recebe mensagem de ativação.
  - Preparação: Descobrir quantas estações estão ativas, solicitando essa informação ao gerente.
  - Caso 1: Se for a primeira estação ativa, ela pede ao gerente a quantidade total de vagas e aloca todas para si.
  - Caso 2: Se houver outras estações ativas, a estação envia brroadcast a todas as ativas para conhecer a quantidade de vagas de cada uma, então pede a lista da estação com mais vagas e divide igualmente entre as duas.
  - Encerramento: Após concluir as ativações deve informar por mensagens as novas listas de vagas (estação que cedeu vagas), enviar broadcast para as ativas da nova lista de estações ativas e infromar ao gerente.
  - Problema: Se as estações começarem a ativar ao mesmo tempo, pode haver problema de concorrencia ao solicitar para o gerente e acabar replicando vagas.
  - Alternativa não implementada: utilizar o gerente para distribuir as vagas RUIM -> sistema centralizado!!! Nao faz sentido eu deixar que o gerente escolha isso sem troca de mensagens entre as estações.

## Requisição de Vaga por Carro
  - App: Recebe uma mensagem de requisição de vaga por carro e a encaminha para a estação apropriada e responde direto ao Controle para não travar a socket.
  - Estação: Processa a requisição e aloca uma vaga se disponível. Se não houver vagas disponíveis, envia uma requisição de empréstimo para outras estações.
  - Outras Estações: Recebem a requisição de empréstimo e respondem com o status da requisição (sucesso ou falha).
  - Estação Original: Recebe a resposta e se for sucesso de empréstimo, a vaga ja foi alocada na outra estação mesmo.

## Liberação de Vaga por Carro
  - App: Recebe uma mensagem de liberação de vaga por carro e a encaminha para a estação apropriada e responde direto ao Controle para não travar a socket.
  - Estação: Processa a requisição de liberação, primeiro busca pelo carro na sua propria lista, depois na sua fila e por fim envia um boadcast para todas as outras estações para que busquem o carro e liberem a vaga.
  - PROBLEMA: Se a estação falhou, ainda nao detectou a falha e chega requisição de liberação para aquele carro, a vaga fica pra sempre ocupada e da outros problemas

## Ping
  - Estação: Envia pings constantes, em um intervalo de tempo, para todas as outras estações para verificar se estão ativas. Se uma estação falhar, dispara uma eleição para redistribuir as vagas.
  - Outras Estações: Recebem os pings e adicionam na fila de ping para serem processados.
  - Existem retrys e timeouts para garantir que a eleição seja disparada apenas quando necessário.

## Eleição em caso de falha
  - Estação: Apos exceder os timeouts e tentativas de ping, dispara uma eleição para redistribuir as vagas.
  - Outras Estações: Recebem a mensagem de eleição e respondem com a quantidade de vagas que cada uma gerencia.
  - Critérios de Eleição: A estação com menos vagas deve assumir as vagas da estação falha (se possível).
  - Backup: Solicita ao gerente as vagas da estação falha para que elas passem a ser controladas pela estação que venceu segundo o critério de eleição.
  - Encerramento: Após concluir a eleição deve informar por mensagens as novas listas de vagas (estação que herdou vagas), enviar broadcast para as ativas da nova lista de estações ativas e infromar ao gerente.
  - Problema: Caso várias estações disparem eleição ao mesmo tempo, quando solicitam as vagas da falha ao manager ele deve limpar a lista desta e assim evitar replicação de vagas.

## Estrutura de Threads
  1. Gerente: apenas 1 thread que recebe e processa requisições das estações conectadas.
  2. Estação:
    - 1 thread para receber mensagens externas.
    - 1 thread para processar mensagens externas.
    - 1 thread para receber mensagens internas.
    - 1 thread para processar mensagens internas.
    - 1 thread para ping constante entre as outras estações
  3. Aplicativo: apenas 1 thread que recebe e encaminha requisições para as estações.

## Script de Inicialização
  - O script de inicialização deve ser executado em ordem para garantir que o sistema funcione corretamente.
  - Primeiro, o gerente deve ser iniciado.
  - Em seguida, o aplicativo deve ser iniciado.
  - Por fim, as estações devem ser iniciadas.
  - O gerente armazena as informações de todas as estações de forma util ao debug e manutenção, assim, quando o gerente inicia, ele escreve um arquivo para que o Controle possa ler.
  - Para start up sincronizado, esse mesmo arquivo gerado pelo gerente é lido no script e as informações de cada estação sao passadas por parametro de cli.
  - No setup de cada estação, como usa-se uma linha de broadcast (re nao por anel de encaminhamento), deve existir um bind prévio da porta de cada estação possível de se comunicar.
  - No arquivo, a porta de cada estação é na verdade a porta interna dela, sendo assim a porta que comunica com o Controle pe porta - 1 e a porta que comunica App <-> Estação é porta -2, mas tudo isso é gerenciado automaticamente pelos scripts.
  - Dessa forma, basta verificar quais portas deseja usar e editar no manager.py (recomenda-se um intervalo de 10 entre cada estação) e rodar o script de inicialização (python3 start_up.py)
  - O sistema gera logs para cada estação+app e para o gerente, além de ter um arquivo especial logs/debug.txt em que deve ser escrito o que deseja debugar em tempo de execução como:
  ```py
    with open("../Distributed_Systems/ParkingLot/logs/debug.txt", "a") as f:
      f.write("\nDEBUG MESSAGE\n")
  ```