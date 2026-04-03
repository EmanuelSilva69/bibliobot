# Analise de Requisitos do Projeto de Monografia

Projeto-base: O USO DE CHATBOTS COMO FERRAMENTAS DE RECOMENDACAO EM BIBLIOTECAS UNIVERSITARIAS  
Instituicao: UFMA - Biblioteconomia  
Recorte: Prototipo funcional de chatbot recomendador

## 1) Mapeamento de Necessidades Informacionais

Observacao metodologica: o PDF original nao foi encontrado no workspace nesta execucao. A rastreabilidade abaixo usa as secoes conceituais citadas no enunciado (Justificativa, Problematica, Objetivos e referencial teorico).

### 1.1 Transformacao Digital
- Necessidade: oferecer mediacao em ambiente digital onde a busca informacional e mais rapida, fragmentada e orientada por interfaces conversacionais.
- Implicacao de sistema: atendimento continuo, interface de linguagem natural e capacidade de converter perguntas abertas em criterios de busca objetivos.
- Source PDF: Justificativa (mudanca dos habitos de busca e uso da informacao).

### 1.2 Mediacao da Informacao
- Necessidade: substituir o modelo de resposta direta por um modelo de entrevista de referencia em ambiente eletronico.
- Implicacao de sistema: modulo de dialogo com perguntas de refinamento (tema, objetivo academico, tipo de fonte, recorte temporal).
- Source PDF: Problematica + eixo de mediacao informacional.

### 1.3 Personalizacao
- Necessidade: adequar respostas ao perfil e intencao do usuario universitario com agilidade.
- Implicacao de sistema: recomendacao baseada em conteudo com pesos para metadados (titulo, assunto, autor, resumo) e preferencia de contexto.
- Source PDF: Objetivos especificos + discussao sobre compatibilidade com habitos digitais.

### 1.4 Reducao de Barreiras
- Necessidade: reduzir friccao de acesso ao acervo e absorver duvidas recorrentes de forma clara.
- Implicacao de sistema: respostas orientativas, selecao de poucos itens de alta relevancia e explicacao dos criterios de escolha.
- Source PDF: Problematica (barreiras de acesso e sobrecarga informacional).

## 2) Tabela de Requisitos

| ID do Requisito | Descricao Tecnica | Justificativa Academica/Source PDF |
|---|---|---|
| RF-01 | Implementar fluxo de atendimento conversacional com contexto de sessao e perguntas de refinamento. | Problematica: necessidade de mediacao em ambientes eletronicos complexos; entrevista de referencia. |
| RF-02 | Implementar modulo de orientacao de usuarios com respostas em linguagem academica e proximos passos de busca. | Objetivo especifico (b): atendimento e orientacao de usuarios. |
| RF-03 | Implementar recomendacao baseada em conteudo usando metadados (titulo, assunto, autor, resumo). | Objetivo especifico (b) + base teorica de recomendacao por conteudo no dominio bibliotecario. |
| RF-04 | Implementar expansao semantica de termos (descritores e relacoes semanticas) para aumentar recuperacao relevante. | Discussao teorica: compatibilizacao entre linguagem do usuario e descritores do acervo. |
| RF-05 | Implementar filtro de relevancia e limite de resultados para reduzir sobrecarga informacional. | Problematica: sobrecarga informacional e necessidade de triagem. |
| RF-06 | Implementar mecanismo de explicabilidade por recomendacao (motivos, metadados usados e regra de ordenacao). | Eixo etico: transparencia dos algoritmos. |
| RF-07 | Implementar registro de auditoria de recomendacoes por sessao (consulta, criterio, itens sugeridos). | Objetivo especifico (c): identificar limites e desafios da recomendacao automatizada. |
| RF-08 | Implementar fallback quando motor de busca/LLM falhar, preservando orientacao basica ao usuario. | Objetivo especifico (c): mitigacao de limitacoes operacionais e de confiabilidade. |
| RF-09 | Implementar sinalizacao explicita de que o bot apoia, mas nao substitui, a curadoria bibliotecaria. | Etica profissional: preservacao do papel critico do bibliotecario. |
| RF-10 | Implementar canal de revisao humana para casos ambiguos ou de alta criticidade academica. | Objetivo especifico (c) + transparencia e responsabilizacao no uso de IA. |

## 3) Requisitos Funcionais Derivados dos Objetivos b e c

### Objetivo (b): atendimento, orientacao e recomendacao
- RF-B1: Atendimento conversacional com identificacao de necessidade informacional.
- RF-B2: Orientacao de busca com sugestao de termos, descritores e recortes.
- RF-B3: Recomendacao de conteudos por similaridade de metadados.
- RF-B4: Resposta sintetica e priorizada para favorecer tomada de decisao do usuario.

### Objetivo (c): limites e mitigacoes da automacao
- RF-C1: Transparencia de criterio de ranking por item recomendado.
- RF-C2: Detecao de baixa confianca (pouco sinal semantico) e convite ao refinamento.
- RF-C3: Escalonamento para validacao bibliotecaria quando houver ambiguidade persistente.
- RF-C4: Logs para avaliacao de vies, falhas e cobertura de recomendacao.

## 4) User Stories (UFMA)

Formato solicitado: Como usuario da UFMA, eu quero [funcionalidade] para que [valor baseado na teoria de Wilson ou Marchionini].

1. Como usuario da UFMA, eu quero descrever minha duvida em linguagem natural para que eu possa reduzir meu estado de incerteza informacional (Wilson).
2. Como usuario da UFMA, eu quero que o bot faca perguntas de refinamento para que minha necessidade real seja interpretada antes da recomendacao (Wilson + entrevista de referencia).
3. Como usuario da UFMA, eu quero receber poucas recomendacoes bem justificadas para que eu consiga navegar melhor em ambientes de busca complexos (Marchionini).
4. Como usuario da UFMA, eu quero entender por que cada item foi sugerido para que eu mantenha controle cognitivo sobre o processo de busca (Marchionini + transparencia algoritmica).
5. Como usuario da UFMA, eu quero orientacoes de proximo passo (descritores, filtros, tipo de fonte) para que eu execute uma estrategia de busca iterativa eficiente (Marchionini).
6. Como usuario da UFMA, eu quero saber quando devo consultar um bibliotecario para que eu tenha suporte especializado em casos de alta complexidade (etica e mediacao profissional).

## 5) Lista de Restricoes Eticas e Operacionais

O sistema NAO deve:
- R-01: apresentar recomendacoes sem explicitar criterio minimo de selecao.
- R-02: simular neutralidade total quando houver incerteza ou baixa cobertura de dados.
- R-03: substituir o julgamento profissional do bibliotecario em decisoes de curadoria critica.
- R-04: coletar ou expor dados pessoais sensiveis sem necessidade funcional e sem transparencia.
- R-05: maximizar quantidade de resultados em detrimento de relevancia (evitar sobrecarga informacional).
- R-06: ocultar falhas do motor de busca/LLM; deve informar indisponibilidade e oferecer alternativa.
- R-07: reforcar vies por regras opacas nao auditaveis.
- R-08: responder de forma conclusiva quando o contexto for ambiguo; deve pedir refinamento.

## 6) Matriz de Rastreabilidade Teorica (Resumo)

| Funcionalidade | Base Teorica | Efeito no Prototipo |
|---|---|---|
| Entrevista de referencia conversacional | Mediacao da informacao | Melhor interpretacao da necessidade informacional |
| Recomendacao por metadados + descritores | Recomendacao baseada em conteudo | Aderencia ao dominio bibliotecario |
| Filtro por relevancia e limite de itens | Sobrecarga informacional | Menor ruido e maior utilidade percebia |
| Log de explicabilidade | Transparencia algoritmica | Auditoria e confianca do usuario |
| Escalonamento ao bibliotecario | Etica e papel critico humano | Governanca e responsabilidade informacional |

## 7) Nota para Versao Final da Monografia

Para versao de defesa, recomenda-se complementar este documento com citacoes paginadas do PDF (autor-ano-pagina), mantendo os IDs RF para garantir consistencia entre texto teorico, implementacao e avaliacao empirica.
