# Arquitetura modular proposta — SubBass

## Decisão de partição

A arquitetura mais viável é separar o produto por função e manter o caminho de áudio de baixa frequência curto:

1. **Fonte simétrica externa**: módulo independente que fornece `+15 V`, `GND` e `−15 V`.
2. **Processador SubBass**: uma placa com filtros passa-alta (~10 Hz) e passa-baixa (~40 Hz), supervisor e mute automático. O mute fica nesta placa para supervisionar localmente os trilhos e evitar um cabo adicional no sinal já filtrado.
3. **Amplificador de saída**: placa futura para OPA1622 e sua interface de carga/conector. A saída do processador é nível de linha; não conectar fones diretamente nela.

Esta divisão permite testar e substituir os módulos separadamente. Para o protótipo, a interligação será por chicotes curtos com conectores polarizados. Em integração futura, pode-se substituir chicotes por conectores placa-a-placa se o empilhamento e o envelope mecânico forem definidos.

## Interfaces elétricas

| Porta na placa SubBass | Conector | Pino | Sinal |
|---|---|---:|---|
| Alimentação J1 | JST-XH, 3 vias, passo 2,50 mm | 1 | +15 V nominal |
|  |  | 2 | GND comum |
|  |  | 3 | −15 V nominal |
| Entrada J2 | JST-XH, 2 vias, passo 2,50 mm | 1 | Áudio de entrada, referenciado a GND |
|  |  | 2 | GND de sinal |
| Saída J3 | JST-XH, 2 vias, passo 2,50 mm | 1 | Áudio filtrado após mute, para entrada do amplificador de saída |
|  |  | 2 | GND de sinal |

A saída seguinte deve apresentar impedância de entrada alta; o estudo do mute recomenda pelo menos 100 kΩ. A ordem de pinos e polaridade devem ser mantidas nos cabos e documentadas na serigrafia do produto. JST-XH é uma escolha de protótipo para chicote de baixa corrente, não uma especificação final de produto ou de segurança.

## Estado do projeto e viabilidade

A folha de alimentação existente contém somente o conector de entrada da alimentação simétrica; não implementa retificação, regulação ou proteção de uma fonte. A hierarquia atual também não contém o circuito/PCB do OPA1622. Portanto, as duas placas externas estão definidas como interfaces e ainda precisam ser projetadas antes de existir um produto completo.

A placa `hifi_audio.kicad_pcb` é uma **revisão A0 de posicionamento**, gerada a partir dos footprints atribuídos aos símbolos. Tem 100 × 64 mm, quatro furos de montagem M3 e 38 footprints de componentes do esquema. O ERC do esquema e o DRC geométrico dessa colocação reportam zero violações. No entanto, há 87 itens sem conexão porque não existe roteamento elétrico validado. Um autorroteador experimental produziu curtos e violações e foi descartado; não se deve usar essa saída para fabricação.

Assim, a partição e as interfaces são viáveis para prototipagem, mas **nenhuma PCB está liberada para fabricação**. Antes de liberar a placa SubBass, faltam roteamento revisado, DRC sem erros/desconexões, revisão dos footprints e BOM contra componentes comprados, validação da alimentação/chicotes, documentação de montagem e ensaios de bancada. Também faltam as placas reais da fonte e do OPA1622, além da validação temporal e analógica do mute já descrita neste repositório.

## Próximos passos de engenharia

1. Confirmar os componentes físicos e footprints, especialmente passivos e a orientação de cada CI/diodo.
2. Fazer o layout por blocos, mantendo trilhas dos filtros e da saída afastadas dos nós de comutação e dos cabos de alimentação.
3. Roteá-la com regras do fabricante escolhido, revisar retorno de GND, desacoplamento, largura de trilhas e afastamentos.
4. Completar e validar esquemático/PCB do regulador simétrico e do amplificador OPA1622; conferir consumo, conectores e proteção contra ligação invertida.
5. Validar protótipos em bancada antes de preparar Gerbers, arquivos de furação e pacote de montagem.

A PCB de posicionamento pode ser regenerada com `tools/build_subbass_module_board.py`, executando o Python empacotado pelo KiCad desta instalação.
