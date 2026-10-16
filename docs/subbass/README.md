# SubBass — filtros concluídos e proposta física HW1 do mute

Os filtros Sallen-Key com OPA1656 foram preservados: passa-baixas de aproximadamente 40 Hz e subsônico passa-altas de aproximadamente 10 Hz. O mute ideal EV1 foi substituído no esquema ativo por componentes reais em uma folha filha.

```text
hifi_audio.kicad_sch
└── subbass.kicad_sch
    └── mute_subbass.kicad_sch — LTC2909 + ADG5412F
```

**Avaliação atual: 26 cenários funcionais concluídos com limitações; hardware não aprovado.** As rampas são bloqueadas, mas o modelo de queda abrupta de 1 µs mostrou excursões de até 2,10 V. Esse caso requer bloqueio mais rápido ou coordenação com o estágio de saída e confirmação em bancada.

A revisão física inclui os divisores e a alimentação do supervisor, clamp de entrada, chave de áudio, desacoplamento, terminação, capacitor de saída e resistor no dreno para limitar sua corrente de descarga. U4/U5 têm símbolos com pinagem real e footprints atribuídos; TP1/TP2 são pads de medição.

**Esta é uma proposta para protótipo, com modelos SPICE locais aproximados; não é aprovação de THD, ausência de estalos ou fabricação.** Os filtros continuam concluídos em nível de esquema e validação funcional. A integração com o OPA1622 fica para o módulo de saída.

- [Dimensionamento, fontes e roteiro de bancada](hardware/README.md)
- [BOM do mute, com tolerâncias e encapsulamentos](hardware/bom_mute.csv)
- [Resultados atuais](resultados.json)
- [Histórico do estudo ideal EV1](funcional_ev1.md), aprovado no commit 099b307; seus números não são especificações do mute físico.

A proposta usa limiares nominais de +12,95 V e −12,55 V, com timeout interno de 200 ms típicos (150–260 ms). Ela substitui a histerese artificial de 1 V do estudo anterior pela filtragem e temporização do supervisor real. Com R16=680 Ω e RON modelado de 10 Ω, a perda nominal calculada é cerca de 0,58 dB com carga de 10 kΩ; essa perda precisa entrar no orçamento de ganho da integração.

Para repetir a verificação sem alterar os esquemas:

```bash
python3 tools/verify_subbass.py --output /tmp/subbass-hw1
uv run tools/plot_subbass.py /tmp/subbass-hw1 --output /tmp/subbass-hw1-graficos
```

Os artefatos e a conclusão numérica são atualizados após uma execução completa. O relatório de hardware explica a cobertura e as limitações dos modelos. As fontes nominais do KiCad são preservadas; o verificador gera os estímulos de falha nas netlists de teste.
