# Estudo do pulso na queda abrupta dos trilhos

16/10/2026. Continuação exploratória da simulação HW1. Varia somente o atraso do detector no macromodelo e, em separado, R16/C10. Netlists e dados temporários usados neste estudo ficam em `/tmp/subbass_hardware_cupoj0uk/sweep`; não fazem parte do circuito aprovado nem de uma qualificação de hardware.

## O que domina o pulso

Com R16=680 Ω e C10=100 nF, reduzi o atraso `TPD` do modelo LTC2909 e medi a saída no intervalo de 0,8 ms após cada trilho colapsar em 1 µs, durante um seno de 20 Hz:

| Atraso imposto ao detector | Queda de +V | Queda de −V |
|---:|---:|---:|
| 0 µs (limite ideal) | −25,7 mV | −25,9 mV |
| 10 µs | −360 mV | +227 mV |
| 50 µs | −1,242 V | +0,950 V |
| 150 µs | −1,929 V | +1,611 V |
| 500 µs | −2,102 V | +1,765 V |

O resultado aponta o atraso até abrir a chave como fator dominante nesta simulação: o limite ideal quase elimina o pulso; dezenas de microssegundos já deixam excursões grandes. O modelo usa atraso fixo e o OPA1656 fica fora das condições normais quando um trilho some. Portanto, a tabela ajuda a estabelecer a investigação seguinte, mas não prediz a resposta real nem demonstra que um detector comercial atingirá o mesmo resultado.

## Alternativa passiva explorada

Também variei R16 e C10. Valores são picos absolutos na mesma janela de falha, seguidos da resposta AC do caminho completo com carga de 10 kΩ:

| R16 | C10 | Pico +V | Pico −V | 10 Hz | 20 Hz | 40 Hz |
|---:|---:|---:|---:|---:|---:|---:|
| 680 Ω | 100 nF | 2,102 V | 1,765 V | −3,571 dB | −1,101 dB | −3,556 dB |
| 680 Ω | 470 nF | 1,562 V | 1,410 V | — | — | — |
| 1 kΩ | 470 nF | 1,282 V | 1,138 V | −3,831 dB | −1,370 dB | −3,862 dB |
| 2,2 kΩ | 470 nF | 0,834 V | 0,559 V | −4,739 dB | −2,305 dB | −4,902 dB |

O aumento de R16/C10 reduz o pulso, mas adiciona perda variável na faixa do subwoofer. Mesmo a opção de 1 kΩ/470 nF não leva o pulso abaixo de 1 V e já perde 0,27 dB adicionais a 20 Hz; 2,2 kΩ/470 nF reduz mais o pico, com perda adicional de cerca de 1,2 dB a 20 Hz. A resposta também depende da carga do estágio seguinte, que ainda não está conectada. Não recomendo alterar R16/C10 com base só neste modelo.

## Próximo trabalho de circuito

Manter a proposta atual e estudar um caminho de inibição rápido, independente do temporizador de partida do LTC2909, que atue diretamente no controle da chave quando qualquer trilho cruza o limiar. A seleção precisa considerar o atraso máximo do comparador no overdrive real, a lógica de combinação dos dois trilhos, comportamento com alimentação parcial e a faixa lógica de U5. Em seguida, repetir estes ensaios com modelos que representem esses tempos e com o estágio real de saída conectado. A bancada deve confirmar a forma de onda antes de qualquer aprovação para uso com fones.
