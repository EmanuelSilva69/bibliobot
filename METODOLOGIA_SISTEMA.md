# METODOLOGIA_SISTEMA

## Transparencia Algoritmica

[Rastreabilidade: source 58, 74, 101]
A recomendacao e explicada em duas camadas: (1) motivos por item no ranking (termo no titulo, assunto, autor, resumo, relacao semantica) e (2) nota consolidada de criterios exibida na resposta ao usuario.

[Rastreabilidade: source 58, 101]
Objetivo pratico: permitir compreensao, auditoria e contestacao dos resultados sem caixa-preta total.

## Etica na Automacao

[Rastreabilidade: source 58, 74, 101]
O bot nao substitui o bibliotecario. Ele atua como apoio ao processo de referencia, especialmente nas fases iniciais de identificacao de necessidade informacional e triagem de fontes. Em casos de ambiguidade, orienta validacao humana.

## Fluxo Metodologico do Sistema

[Rastreabilidade: source 31, 43, 46, 58]
1. Captura da necessidade: usuario descreve a demanda.
2. Entrevista de referencia curta: sistema coleta contexto adicional.
3. Busca inicial: recuperacao ampla via SearXNG.
4. Normalizacao: conversao para metadados padronizados.
5. Rankeamento: recomendacao baseada em conteudo.
6. Corte de ruido: filtro de relevancia para reduzir sobrecarga.
7. Resposta mediada: LLM local redige orientacao final com nota de transparencia.

## Preservacao do Papel Critico do Bibliotecario

[Rastreabilidade: source 58, 74, 101]
A arquitetura foi desenhada para incorporar curadoria humana como instancia final de qualidade: os criterios ficam explicitos e os resultados podem ser revistos, ajustados e complementados por profissionais da informacao.
