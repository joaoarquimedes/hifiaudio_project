# SubBass HW2 — proposta de mute e estado de fabricação

16/10/2026. Esta revisão acrescenta o comparador U6 para detectar rapidamente o colapso de qualquer trilho. Os resultados abaixo são de modelos locais em ngspice; não equivalem a modelos oficiais completos nem à validação do circuito físico.

## Resultado da avaliação

**25 cenários SPICE concluíram com `FUNCTIONAL_PASS_WITH_LIMITATIONS`; isso não aprova o hardware para fabricação.** O circuito lógico passou pelos critérios funcionais codificados, mas a modelagem da resposta temporal do novo comparador é idealizada. A PCB está em estudo de posicionamento A0, com contorno e footprints, mas sem roteamento elétrico validado; o DRC identifica 87 itens sem conexão. A arquitetura modular e o pinout estão em [arquitetura_modular.md](arquitetura_modular.md).

| Ensaio | Resultado no modelo atual |
|---|---|
| Rampas simultâneas de 10 ms | Libera em 309,133 ms; bloqueia em 611,270 ms |
| Partida, após mute | Pico absoluto de ~51,95 µV |
| Desligamento, após mute (615–650 ms) | Pico absoluto de ~59,54 µV |
| Áudio nominal, após mute | 2,491762 Vp em 20 Hz para entrada de 2,828 Vp |
| Pacote de carga imposto ±680 pC | Excursões de aproximadamente −6,36 mV / +7,24 mV |
| Corner de 50 nA, RON=16,5 Ω e acoplamento 13 pF | Maior saída com entrada zero de ~0,549 mV |
| Pico na saída logo após a falha abrupta de +V / −V | 25,738 mV / 25,929 mV no modelo sem atraso temporal |
| Corrente máxima em R16 no mesmo ensaio | 3,634 mA nos dois casos modelados |

**Limite crucial:** o subcircuito `TLV1702_FAST_STUDY` é uma função estática suave de limiar, sem atraso de propagação. Foi usado porque a simulação temporal com o modelo OPA1656 não convergiu de forma robusta com as versões dinâmicas tentadas. Assim, as excursões de ~26 mV representam uma hipótese ideal de desligamento instantâneo; não demonstram que o comparador real cortará o áudio nesse nível. O datasheet da TI informa 560 ns típicos a 100 mV de overdrive, sem máximo garantido nessa condição. O atraso na amplitude real de falha, no circuito e com variação de processo/temperatura, ainda precisa de análise conservadora e medida em bancada.

O resultado de HW1 com supervisor apenas previa excursões de −2,102 V / +1,765 V em ensaio semelhante. Isso motivou U6; não deve ser comparado como prova quantitativa de melhoria, porque os dois resultados usam modelos diferentes. O OPA1656 fora da alimentação normal também torna esses transitórios exploratórios. Não conectar fones supondo proteção contra colapso abrupto.

ERC do esquemático: zero ocorrências com as regras do projeto. A lista de posições compradas aumentou para 20. Alguns novos itens têm MPN definido, mas os passivos originais R8–R16 e C7–C10 ainda não têm código comercial fechado. Portanto, BOM e footprints continuam precisando de conferência com itens efetivamente comprados. A placa `hifi_audio.kicad_pcb` contém footprints e `Edge.Cuts`, mas não possui roteamento válido. O DRC de posicionamento encontra zero violações geométricas e 87 itens sem conexão; não liberar fabricação.

## Componentes e folha

A folha `subbass.kicad_sch` mantém U1A/U1B e as redes dos filtros. Sua filha `mute_subbass.kicad_sch` contém o mute e o corte rápido de falha:

- U4: **LTC2909ITS8-2.5#TRMPBF**, TSOT-23-8, com referência interna e supervisão positiva/negativa.
- U5: **ADG5412FBRUZ**, TSSOP-16, usando o canal 1 em série. A entrada protegida S1 recebe o sinal de U1B; o dreno D1 entrega o sinal a R16. Os três canais restantes ficam desativados e aterrados; FF fica aberto.
- U6: **TLV1702AIDGKR**, VSSOP-8. Compara os sensores dos trilhos com metade da referência e conecta as saídas open-collector em wired-OR com RST de U4. O circuito pretende remover CTRL_PASSA sem aguardar o timer de partida. A resposta dinâmica ainda não foi qualificada.
- R17/R18 criam metade de REF; C11 desacopla U6. R9/C7 alimentam o supervisor pelo shunt interno. R10/R11 observam +V; R12/R13 deslocam a leitura de −V com a referência de 1 V. D1 externo protege essa entrada quando +V está ausente.
- R14 puxa o reset para a própria alimentação de U4. R15 mantém o controle baixo sem energia.
- R16=680 Ω, **no dreno**, isola C10 e limita o retorno de corrente quando um trilho desaparece. C10=100 nF reduz o degrau produzido por uma carga injetada na saída. R8=10 kΩ mantém uma carga/descarga definida.

A pinagem dos símbolos segue os encapsulamentos citados, não as versões DFN/LFCSP. O terra do modelo SPICE se chama ZREF para evitar colisão com o nó global reservado `GND` do modo de compatibilidade. Isso não altera os pinos físicos de terra.

BOM: [CSV](bom_mute.csv) e [JSON](bom_mute.json), com 20 posições compradas e TP1/TP2 como pads de teste fora da contagem. Os códigos de U4/U5/U6 e D1 estão definidos. Os MPNs para R8–R16 e C7–C10 ainda devem ser escolhidos e verificados contra disponibilidade, tolerância, potência, tensão e encapsulamento antes de liberar compras/montagem.

## Dimensionamento próprio

| Elemento | Valor e requisito |
|---|---|
| R9 | 4,99 kΩ, 0,1%, 0805, 0,125 W |
| R10 / R11 | 249 kΩ / 10 kΩ, 0,1%, 0805 |
| R12 / R13 | 10 kΩ / 261 kΩ, 0,1%, 0805 |
| R14 / R15 | 10 kΩ / 100 kΩ, 1%, 0805 |
| R16 | 680 Ω, 1%, 1206, 0,25 W; exigir capacidade de pulso de pelo menos 15 µJ |
| R8 | 10 kΩ, 1%, 0805 |
| C7/C8/C9 | 100 nF, X7R, 50 V, 0805 |
| C10 | 100 nF, C0G, 5%, 50 V, 1206 |
| D1 | BAT54WS-7-F, SOD-323; pad 1 cátodo em ADJ_NEG, pad 2 ânodo em GND |

Limiar positivo nominal: `0,5 × (1 + 249k/10k) = +12,95 V`.

Limiar negativo nominal em módulo: `(261k/10k) × 1 − (1 + 261k/10k) × 0,5 = 12,55 V`.

Com as tolerâncias de referência/limiar tratadas independentemente e divisores de 0,1%, o envelope conservador calculado fica próximo de **12,73–13,17 V** no positivo e **11,93–13,17 V** em módulo no negativo, antes do pequeno erro de corrente de entrada. Não é uma distribuição estatística. A maior dispersão no negativo resulta do deslocamento pela referência e já foi considerada na escolha do limiar; ambos ficam abaixo de 13,5 V, o extremo inferior de uma alimentação ±15 V com tolerância de 10%.

O shunt de U4 recebe aproximadamente 1,7 mA através de R9 em +15 V e VCC_SUP próximo de 6,5 V. O modelo usa um orçamento conservador de 250 µA para o circuito interno/referência; o pull-up durante reset consome cerca de 0,65 mA. A dissipação de R9 fica na ordem de 15 mW nessa condição.

Para R16, mesmo tomando uma tensão retida de 16,5 V e desprezando a queda do clamp, `16,5 / (680 × 0,99) = 24,51 mA`. A energia máxima aproximada em C10 de 105 nF é `0,5 × 105n × 16,5² = 14,29 µJ`. O resistor deve suportar esse pulso, além da potência contínua; não basta selecionar apenas a potência nominal.

A resistência série nominal é 680 + 10 = **690 Ω**, considerando o RON adotado no modelo de U5. A perda calculada em baixa frequência é **0,58 dB com 10 kΩ** e **2,57 dB com 2 kΩ**. A carga de 2 kΩ é um ensaio de estresse, não a interface nominal. O próximo estágio deve ter entrada de pelo menos **100 kΩ**; em paralelo com R8 isso mantém a perda perto de 0,64 dB. A cadeia de ganho deve considerar essa perda na integração com o OPA1622.

C10 com a resistência série introduz um polo acima de 2 kHz com carga nominal, muito acima da faixa útil de 10–40 Hz. Ele não substitui nem redefine os filtros existentes.

## Comportamento e mudanças frente ao estudo ideal

- SEL de U4 fica **aberto**; TMR fica em GND. A liberação usa o timeout interno nominal de 200 ms, com faixa de 150–260 ms.
- Este modo não conserva a histerese artificial de 1 V do estudo EV1. Usa os limiares dos divisores, a filtragem do supervisor e a necessidade de novo timeout após uma falha.
- O reset é open-drain: controle alto permite áudio; controle baixo bloqueia. U6 adiciona um caminho lógico rápido, mas seu macromodelo atual não inclui propagação temporal. Não há conclusão quantitativa válida sobre o tempo real de corte.
- A chave real tem RON e vazamento. Portanto, os números de 1 Ω, 1 GΩ e 11 µV da revisão ideal não são especificações desta implementação física.
- A chave possui proteção no lado **Sx**. Os drenos não têm a mesma proteção; a posição de R16 depois de D1 do CI foi escolhida para limitar a descarga de C10 pelos clamps internos durante uma queda abrupta.

## O que as simulações verificam

A comparação dos atrasos de detecção e das alternativas R16/C10 está registrada em [Estudo do pulso na queda abrupta](estudo_pulso_falha.md). O resultado favorece investigar uma inibição rápida independente do atraso modelado; aumentar R16/C10 reduz o pico, mas degrada a resposta de 10–40 Hz.

`tools/verify_subbass.py` exporta o esquema atual, verifica os valores dos filtros e usa o macromodelo TI do OPA1656 junto dos modelos locais de U4/U5/D1. As netlists de ensaio são geradas fora do projeto, sem alterar os esquemas. São avaliados rampas, ordens de alimentação, trilhos ausentes, falhas durante áudio, quedas abruptas, recuperação, tolerâncias de timeout/limiar, carga capacitiva, DC, AC e vazamento.

O estudo de injeção aplica deliberadamente uma carga de ±680 pC na saída. Trata-se de uma perturbação imposta para avaliar C10, não de uma simulação fiel dos mecanismos internos da chave. A estimativa simples `680 pC / 100 nF = 6,8 mV` mostra por que a comutação ainda precisa ser medida. Um bloqueio durante sinal pode cortar a onda fora do zero, independentemente dessa carga injetada.

Os modelos não incluem ruído, curva completa de RON com sinal, THD da chave, comportamento térmico completo nem todas as proteções. A filtragem interna de U4 é aproximada por atraso; o timer interno por um equivalente RC. As curvas fora da alimentação normal do OPA1656 são exploratórias. Queda abrupta pode expor a saída durante o tempo de detecção, seguido da descarga de C10: o estudo não autoriza afirmar bloqueio sem qualquer pulso em toda falha.

Os testes não qualificam inversão da alimentação, sobretensões fora da faixa do projeto ou trilhos flutuantes como se fossem fontes fixadas em zero. O clamp de ADJ_NEG precisa ter sua tensão verificada em temperatura; o modelo simples de D1 não garante a curva fria do componente comprado.

## Repetição

Na raiz do repositório:

```bash
python3 tools/verify_subbass.py --output /tmp/subbass-hw2
uv run tools/plot_subbass.py /tmp/subbass-hw2 --output /tmp/subbass-hw2-graficos
```

Usa KiCad CLI, Python padrão e a biblioteca ngspice do KiCad, ou o caminho indicado por `NGSPICE_LIBRARY`. O simulador é configurado em Gear. Os casos comuns usam passo máximo de 20 µs; as falhas de trilho usam 50 µs para manter convergência. Esses passos não validam o atraso do comparador, ausente no modelo. Logs, CSV e netlists permitem auditar também falhas de convergência. Uma execução interrompida não conta como aprovação.

No KiCad, as fontes permanecem nominais em DC ±15 V e senoide de 20 Hz. Para observar uma partida, use os estímulos pulsados documentados ou o verificador; o ponto de operação DC já representa o sistema energizado. O workbook mantém controle e saídas acessíveis.

## Roteiro de bancada antes de aprovar fabricação

1. Conferir pad 1, orientação dos CIs/diodo e continuidade com o esquema. Montar inicialmente sem fones nem OPA1622 conectado. Alimentar com fontes simétricas limitadas em corrente.
2. Sem sinal, medir VCC_SUP, referência, ADJ1/ADJ2 e CTRL_PASSA. Em ±15 V, esperar aproximadamente 6–6,9 V, 1 V, 0,579 V, 0,410 V e um controle alto compatível com U5. Medir também o nível baixo do controle.
3. Varrer um trilho de cada vez para medir os limiares, reinício e timeout. Repetir as duas ordens de partida/desligamento e ausência de cada trilho. Registrar tempo de detecção; comparar com as condições do datasheet, sem assumir atraso independente da amplitude.
4. Aplicar 20 Hz / 2 Vrms e medir entrada, saída antes do mute e saída final. Conferir perda de inserção, resposta normalizada de 10–40 Hz e ausência de oscilação. Repetir com 10 kΩ e cargas capacitivas pertinentes. Usar 2 kΩ somente como estresse controlado.
5. Capturar a comutação com entrada zero e com áudio em várias fases; medir pico e duração dos pulsos. Ensaiar a descarga de C10 e a corrente por R16 nas quedas abruptas. Avaliar se o resultado exige outra chave ou uma solução de fade antes de conectá-lo ao amplificador de fones.
6. Medir THD+N e ruído com instrumentos adequados, comparando bypass e mute em passagem. O estudo atual não fornece uma aprovação desses números.
7. Repetir a condição +V ausente/−V presente e medir diretamente ADJ_NEG, inclusive nos extremos de temperatura escolhidos para o produto. Manter margem ao limite absoluto de −0,3 V.
8. Escolher os códigos comerciais dos passivos conforme a BOM, validar a capacidade de pulso de R16 e aprovar os footprints contra os componentes comprados. Consolidar resultados reais antes do layout/fabricação definitiva.

## Fontes primárias

- [LTC2909 — página oficial](https://www.analog.com/en/products/ltc2909.html) e [datasheet, Rev. B](https://www.analog.com/media/en/technical-documentation/data-sheets/2909fb.pdf): configuração de polaridade, pinagem TS8, referência, shunt, limiares e timeout.
- [ADG5412F — página oficial](https://www.analog.com/en/products/adg5412f.html) e [datasheet, Rev. C](https://www.analog.com/media/en/technical-documentation/data-sheets/ADG5412F_5413F.pdf): pinagem TSSOP, proteção do source, limites do drain, RON e carga injetada.
- [BAT54WS — Diodes Incorporated](https://www.diodes.com/datasheet/download/BAT54WS.pdf): encapsulamento, polaridade e características do clamp.

O esquema tem valores e critérios de teste definidos, mas a PCB está apenas na etapa de posicionamento e a fonte/OPA1622 ainda não têm módulos implementados. Para fabricação, faltam fechar a interface com o módulo OPA1622, definir conectores e pinagem do produto, requisitos de sinal/carga, envelope e fixação mecânicos, MPNs de todos os passivos, modelo temporal conservador, medições de bancada (transientes, THD+N, ruído e temperatura), roteamento, DRC aprovado e arquivos Gerber/fabricação.
