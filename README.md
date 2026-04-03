# BiblioBot-UFMA

[Rastreabilidade: source 1, 12, 21]
Projeto de prototipo academico vinculado ao Curso de Biblioteconomia da Universidade Federal do Maranhao (UFMA), periodo 2026.1, inspirado no estudo de Veronica Lima Costa, orientacao do Prof. Dr. Roosewelt Lins Silva.

## Visao Geral

[Rastreabilidade: source 31, 43, 58]
O BiblioBot-UFMA implementa um chatbot de recomendacao que atua como mediador informacional, conduzindo entrevista de referencia, refinando a necessidade do usuario e retornando indicacoes com explicacao de criterio.

## Justificativa Tecnologica

[Rastreabilidade: source 21, 58, 74]
O uso de Docker oferece replicabilidade do experimento, isolamento de dependencias e facilidade de implantacao em laboratorio academico. O uso de LLM local com Ollama reforca autonomia institucional e permite inovacao operacional sem dependencia obrigatoria de servicos externos. A integracao com SearXNG amplia cobertura de busca e viabiliza filtragem posterior para reduzir sobrecarga informacional.

## Arquitetura

[Rastreabilidade: source 21, 46, 58]
- API: FastAPI em app/main.py.
- Motor de recomendacao: app/recommendation_engine.py.
- Camada de compatibilidade: app/engine.py.
- Persona e prompts: app/prompts.py.
- Infraestrutura: Dockerfile e docker-compose.yml.

## Mapeamento de Objetivos Especificos

[Rastreabilidade: source 12, 31, 46, 58, 95]
| Objetivo especifico | Funcionalidade implementada | Evidencia tecnica |
|---|---|---|
| a) Simular mediacao informacional | Entrevista de referencia no endpoint /chat | build_reference_interview_prompt + memoria curta de historico |
| b) Recomendar recursos relevantes | Recomendacao baseada em conteudo por metadados | score_document + recommend_content |
| c) Reduzir sobrecarga e aumentar transparencia | Corte por relevancia e nota de criterio | filter_relevant_recommendations + build_transparency_log |

## Guia Rapido de Execucao

[Rastreabilidade: source 21, 74]
1. Construir e subir servicos:
   - docker compose up --build
2. Opcional: baixar modelo no Ollama (se nao estiver presente):
   - docker exec -it ollama-local ollama pull llama3.1:8b
3. Testar saude da API:
   - GET http://localhost:8000/health
4. Enviar requisicao de chat:
   - POST http://localhost:8000/chat

Exemplo de payload:

```json
{
  "user_id": "u01",
  "message": "Preciso de artigos sobre chatbots em bibliotecas universitarias",
  "subjects": ["biblioteconomia", "chatbot"],
  "authors": []
}
```

## Limites e Papel do Bibliotecario

[Rastreabilidade: source 58, 74, 101]
O sistema e um apoio a mediacao e nao substitui curadoria humana. A recomendacao usa heuristicas de metadados e relacoes semanticas simples, devendo ser validada por profissional da informacao em cenarios de alta criticidade academica.
