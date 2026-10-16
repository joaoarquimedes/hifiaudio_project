# SubBass — filtros e proposta de mute HW2

Os filtros Sallen-Key com OPA1656 permanecem dimensionados para passa-baixas de aproximadamente 40 Hz e passa-altas subsônico de aproximadamente 10 Hz. A folha filha `mute_subbass.kicad_sch` inclui o supervisor LTC2909, a chave ADG5412F e um comparador TLV1702 para sinalizar falha em qualquer trilho.

**Estado: proposta de circuito revisada e 25 cenários SPICE concluídos sob modelos locais; não pronta para fabricação.** O teste do comparador usa uma aproximação estática sem atraso temporal. Portanto, os picos baixos nas falhas abruptas são limites idealizados da simulação, não evidência de proteção real. O CI especifica 560 ns típicos a 100 mV de overdrive, sem máximo garantido nessa condição; o circuito ainda precisa ser caracterizado em bancada.

O PCB do projeto está vazio: não há footprints, cobre, contorno ou conectores, e o DRC acusa falta de contorno. Também falta fechar a fronteira física com o estágio OPA1622, conectores e requisitos mecânicos/elétricos. A aprovação de hardware permanece negada. Não fabricar nem conectar fones com base apenas nestas simulações.

- [Dimensionamento, BOM, limites e roteiro de bancada](hardware/README.md)
- [BOM do mute](hardware/bom_mute.csv)
- [Últimos resultados SPICE](resultados.json)
- [Estudo ideal EV1](funcional_ev1.md), histórico; seus resultados não especificam a implementação física.
- [Esquema atualizado do mute](hardware/esquema_mute.png) · [partida e desligamento](mute_automatico.png) · [resposta AC](resposta_ac.png) · [falhas de trilhos](falhas_trilhos.png)

O verificador reproduz as simulações sem alterar os esquemas:

```bash
python3 tools/verify_subbass.py --output /tmp/subbass-hw2
uv run tools/plot_subbass.py /tmp/subbass-hw2 --output /tmp/subbass-hw2-graficos
```
