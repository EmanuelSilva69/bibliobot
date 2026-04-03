# METODOLOGIA_TECNICA

## Relacao Teoria-Pratica

[Rastreabilidade: source 1, 12, 31]
Este documento descreve como conceitos da Ciencia da Informacao foram traduzidos para componentes de software no prototipo BiblioBot-UFMA.

## Mediacao Informacional e Entrevista de Referencia

[Rastreabilidade: source 31, 43, 58]
A entrevista de referencia e simulada no fluxo do endpoint /chat por meio de memoria de curto prazo e perguntas de refinamento. O sistema nao assume que a primeira mensagem representa a necessidade final: ele recontextualiza a consulta com base no historico recente.

[Rastreabilidade: source 31, 43]
Implementacao pratica:
- Funcao build_reference_interview_prompt em app/prompts.py.
- Armazenamento SESSION_MEMORY em app/main.py para preservar contexto imediato.

## Sistema de Recomendacao Baseado em Conteudo

[Rastreabilidade: source 46, 75, 95]
A escolha por recomendacao baseada em conteudo e aderente ao dominio bibliotecario porque privilegia metadados curados (titulo, assunto, autor e resumo). Esse modelo e coerente com catalogacao e indexacao, reduzindo dependencia de historico massivo de interacoes.

[Rastreabilidade: source 46, 95]
Implementacao pratica:
- Estrutura DocumentMetadata em app/recommendation_engine.py.
- Funcao score_document para pontuar correspondencia lexical e semantica.
- Funcao recommend_content para ranquear itens por relevancia.

## Comportamento Informacional e Incerteza do Usuario

[Rastreabilidade: source 43, 58, 63]
O dialogo orientado reduz incerteza ao converter pedidos vagos em criterios observaveis. Em vez de retornar listas extensas, o sistema limita resultados e apresenta justificativas curtas, reduzindo sobrecarga cognitiva.

[Rastreabilidade: source 58, 63]
Implementacao pratica:
- Funcao filter_relevant_recommendations com limiar minimo de score.
- Limite de exibicao por MAX_RECOMMENDATIONS.

## Etica, Transparencia e Curadoria Humana

[Rastreabilidade: source 58, 74, 101]
O prototipo explicita criterios de recomendacao e registra nota de transparencia para cada resposta. Essa abordagem favorece auditoria do processo e preserva o papel critico do bibliotecario como instancia de validacao e curadoria final.

[Rastreabilidade: source 58, 101]
Implementacao pratica:
- Funcao build_transparency_log em app/recommendation_engine.py.
- Template TRANSPARENCY_TEMPLATE em app/prompts.py.
