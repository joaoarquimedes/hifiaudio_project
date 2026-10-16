# SubBass e mute automático — conclusão do estudo funcional

Revisão de 16/10/2026. Escopo aprovado: concluir o filtro SubBass e o mute automático em SPICE; a implementação física e a integração com o OPA1622 pertencem às próximas etapas.

**Resultado: 18 cenários aprovados.** O esquema hierárquico foi atualizado diretamente, os filtros existentes foram preservados e o pulso V4 foi substituído pelo supervisor U4. O projeto continua como estudo mono com fontes ideais; não é um projeto de fabricação aprovado.

## Circuito e interfaces

| Bloco | Implementação atual |
|---|---|
| U1A | OPA1656, Sallen-Key passa-baixas, ganho unitário, ~40 Hz; R3/R4=28,1 kΩ, C3=100 nF, C4=200 nF |
| U1B | OPA1656, Sallen-Key passa-altas, ganho unitário, ~10 Hz; R6=11,3 kΩ, R7=22,6 kΩ, C5/C6=1 µF |
| Alimentação | +15 V, GND e −15 V; desacoplamento C1/C2=100 nF |
| Supervisor U4 | Modelo funcional `SUBBASS_MUTE_CTRL`, em `spice/SubBass/subbass_mute.lib` |
| Chave S1 | Modelo funcional `SUBBASS_MUTE_SWITCH`; série, 1 Ω em passagem e 1 GΩ em bloqueio |
| Carga nominal | R8=10 kΩ após S1; ensaio AC adicional com 2 kΩ |

Sinais da folha `subbass`:

- `VIN_SUB`: entrada do passa-baixas, ligada à fonte de teste V3.
- `VOUT_SUB`: saída do passa-baixas / entrada do subsônico.
- `VOUT_HP_SUB`: saída dos filtros antes do mute.
- `VOUT_SUB_MUTE`: saída do módulo após o mute, com R8 para GND.
- `CTRL_PASSA`: 0 V bloqueia; 5 V permite passagem.
- `RAIL_OK` (TP1): indica a condição dos dois trilhos antes da temporização.
- `MUTE_TIMER` (TP2): tensão do capacitor de qualificação, em volts.

U4, S1, TP1/TP2 e as fontes V1/V2/V3 estão excluídos da PCB e da BOM. A biblioteca personalizada é registrada em `sym-lib-table`. O sinal de áudio e os diagnósticos usam rótulos locais; sua interface física / estéreo será definida na integração.

## Critérios e funcionamento do mute

1. U4 observa o menor valor entre `V(+V)` e `-V(-V)`, preservando o sinal correto dos trilhos. Um trilho ausente ou com polaridade invertida impede a liberação.
2. Ambos devem superar **13 V em módulo** para qualificar a alimentação.
3. Uma queda de qualquer trilho abaixo de **12 V em módulo** bloqueia o áudio. A faixa de 12–13 V fornece histerese; durante a recuperação é necessário superar novamente 13 V.
4. Com os trilhos qualificados, RDELAY=200 kΩ e CDELAY=1 µF carregam o temporizador. O limiar de 3,160602794 V corresponde a aproximadamente **200 ms** depois da qualificação.
5. Na falha, o controle cai sem espera programada e o capacitor é descarregado por uma chave com 1 Ω, com constante de tempo nominal de 1 µs. A recuperação reinicia o atraso; não há liberação imediata com o retorno dos trilhos.

Os limites de 13/12 V e o atraso de 200 ms são parâmetros escolhidos para este estudo em ±15 V. Não constituem especificações de um supervisor físico selecionado. A referência de controle é limitada a 0–5 V e depende do trilho positivo no modelo.

## Resultados medidos

Ensaio de referência: V3=0 V DC; V1/V2=`PULSE(0 15 100m 10m 10m 500m 4)`, com orientações simétricas; controle automático, sem V4.

| Verificação | Resultado |
|---|---|
| Fim da rampa de partida | 110 ms |
| Dois trilhos ultrapassam 13 V | ~108,67 ms |
| Liberação automática | **308,668 ms** |
| Bloqueio automático na queda | **612,000 ms**, antes da excursão de desligamento |
| Pico de partida antes / após mute | −1,101640 V / −11,016 µV |
| Pico de desligamento antes / após mute | −1,100158 V / −11,001 µV |
| Maior residual com entrada zero durante passagem | ~+0,4974 mV, proveniente do offset dos estágios |
| Falha de +V / −V durante áudio | Bloqueio em ~452 ms; recuperação em ~708,667 ms, após novo atraso |
| Entrada nominal de 20 Hz, 2,828 Vp (~2 Vrms) | Saída após mute de **2,663514 Vp** em regime permanente |
| Entrada DC de 1 V | Residual de ~0,4958 mV após o subsônico/mute em regime permanente |
| Perda da chave em passagem, 10 kΩ / 2 kΩ | ~0,00087 dB / ~0,00434 dB |

Os ~100 dB de atenuação em bloqueio decorrem do divisor ideal 1 GΩ/10 kΩ; isso não é uma especificação de isolamento de um componente real. Com entrada DC zero, a saída durante passagem é próxima de zero, mas preserva o offset residual.

A análise AC usa 100 pontos/década de 0,1 Hz a 1 kHz; 19,95 e 39,81 Hz são os pontos próximos de 20 e 40 Hz dessa malha.

| Frequência | Ganho da cascata após mute, 10 kΩ |
|---:|---:|
| 1 Hz | −39,930 dB |
| 10 Hz | −2,993 dB |
| 19,95 Hz | −0,522 dB |
| 39,81 Hz | −2,977 dB |
| 100 Hz | −16,008 dB |
| 1 kHz | −55,897 dB |

A carga de 2 kΩ preservou a resposta nominal dentro dos critérios funcionais do ensaio. Não foi realizada medição de THD, ruído ou estabilidade com carga capacitiva.

## Cobertura dos ensaios

O arquivo `resultados.json` contém os dados numéricos, estados e hashes das fontes. Foram aprovados:

- partida e desligamento simultâneos, com comparação entre passos máximos de 20 µs e 10 µs;
- partida com positivo primeiro e com negativo primeiro;
- ausência do positivo, ausência do negativo e ausência dos dois;
- perda de cada trilho durante áudio, bloqueio e recuperação com novo atraso;
- interrupção breve durante a qualificação, reiniciando a espera;
- histerese na faixa de 12–13 V e recuperação após subtensão;
- rampa lenta, subtensão permanente e polaridade incorreta;
- passagem de áudio nominal e rejeição de DC;
- resposta AC com cargas de 10 kΩ e 2 kΩ.

Nos testes de falha durante áudio, a senoide de teste começa aos 150 ms, depois da rampa inicial. Isso evita excitar o macromodelo com áudio antes de haver alimentação. O sinal permanece presente durante a falha posterior.

## Repetir os testes

Requisitos: `kicad-cli` e Python 3 com biblioteca compartilhada ngspice. O verificador usa apenas a biblioteca padrão do Python, exporta novamente o **esquemático real** e altera somente as fontes / carga nas netlists de ensaio. Não edita os esquemas.

Na raiz do repositório:

```bash
python3 tools/verify_subbass.py --output /tmp/subbass-verificacao
uv run tools/plot_subbass.py /tmp/subbass-verificacao --output /tmp/subbass-graficos
```

O segundo comando instala / usa Matplotlib em ambiente isolado do `uv`. Para outra instalação de ngspice, defina `NGSPICE_LIBRARY` com o caminho absoluto da biblioteca; os code models são procurados no subdiretório `ngspice` ao lado dela. Neste ambiente foi usada a ngspice **45.2** incluída no KiCad **10.0.7**.

O verificador exige término em 1 s, dados finitos, bloqueio com trilhos inválidos, atraso e recuperação corretos, limites para vazamento, amplitude de áudio e resposta AC. Uma interrupção do simulador faz o teste falhar, mesmo quando a API retorna código zero.

Arquivos gerados: netlists `.cir`, curvas `.csv`, logs `.log`, saída dos processos e `results.json`. As curvas completas são mantidas fora do repositório; os resultados compactos e gráficos estão nesta pasta.

## Uso no simulador do KiCad

A configuração nominal foi preservada: V1/V2 em 15 V DC e V3 em 20 Hz, 2,828 Vp, AC=1. Nesse caso, o ponto de operação já representa alimentação estabelecida: o mute começa liberado. Para observar a partida, é necessário usar fontes que partam de zero, como as dos ensaios automatizados.

O workbook agora exibe os trilhos, `CTRL_PASSA`, a saída antes e após o mute no transiente; em AC, exibe também o ganho após o mute. A diretiva `.options method=gear` está na folha. O transiente usa `.tran 100u 1 0 20u`, sem UIC.

O método padrão apresentou falha de convergência na exploração anterior. Com Gear e passo máximo de 20 µs, os 18 cenários terminaram. O ensaio principal foi repetido com 10 µs; o instante de liberação permaneceu consistente dentro de 50 µs.

Na instalação usada, uma chave `SW` nativa simples permaneceu aberta em AC mesmo com controle DC de 5 V. S1 usa agora um modelo equivalente por condutância comportamental, que foi validado em DC, TRAN e AC. A detecção com histerese interna de U4 continua usando `SW`; os testes de temporização e recuperação são transientes.

ERC: **zero ocorrências com as regras atuais do projeto**. A regra de modelos SPICE estava desabilitada no projeto original; foi também habilitada numa cópia independente, sem erros de modelo. Uma revisão com as regras antes ignoradas revela footprints ainda não atribuídos, compatíveis com o estágio de estudo. Não foram ocultadas novas violações para aprovar a folha.

## Encerramento e próximos módulos

Esta revisão conclui a validação **funcional em SPICE** do filtro atual e do mute automático. Os transitórios previstos pelo macromodelo durante alimentação muito baixa são exploratórios, não amplitudes garantidas em bancada.

Para o projeto físico ainda será necessário escolher e dimensionar supervisor, referência, temporizador e elemento de mute reais; verificar consumo, tolerâncias, tempos, comutação sob áudio, carga capacitiva, distorção e partida/desligamento reais; e coordenar a proteção com o OPA1622. O estudo não implementa proteção contra DC gerado com os trilhos saudáveis, nem garante comutação sem estalo em qualquer fase do áudio.

Referências de implementação do simulador: [documentação oficial do ngspice](https://ngspice.sourceforge.io/docs.html) e [API da biblioteca compartilhada](https://github.com/ngspice/ngspice/blob/master/src/include/ngspice/sharedspice.h). O macromodelo TI usado permanece em `spice/OPA1656/sbomaw6c/OPA1656_DUAL.LIB`.
