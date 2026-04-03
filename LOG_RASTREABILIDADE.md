# LOG_RASTREABILIDADE

[Rastreabilidade: source 1, 12]
Mapa tecnico de funcionalidades do BiblioBot-UFMA para sua base teorica no projeto de pesquisa.

| Componente | Funcionalidade | Base teorica (source) | Evidencia |
|---|---|---|---|
| app/prompts.py | Persona mediadora | source 12, 31, 58 | BOT_PERSONA define mediacao e entrevista de referencia |
| app/prompts.py | Transparencia textual | source 58, 74, 101 | TRANSPARENCY_TEMPLATE explicita criterios |
| app/main.py | Entrevista de referencia no fluxo | source 31, 43, 58 | /chat gera interview_prompt e usa contexto historico |
| app/main.py | Integracao com LLM local | source 21, 74 | generate_llm_answer consulta Ollama |
| app/main.py | Busca ampla + filtro posterior | source 43, 58, 95 | query_searxng + recomendacao local |
| app/recommendation_engine.py | Modelo de metadados | source 46, 75, 95 | DocumentMetadata com titulo/autor/assunto/resumo |
| app/recommendation_engine.py | Score por conteudo | source 46, 58, 95 | score_document pondera campos bibliograficos |
| app/recommendation_engine.py | Mitigacao de sobrecarga | source 58, 63 | filter_relevant_recommendations |
| app/recommendation_engine.py | Transparencia algoritmica | source 58, 74, 101 | build_transparency_log |
| Dockerfile | Reprodutibilidade de ambiente | source 21, 74 | Build padronizado para execucao do prototipo |
| docker-compose.yml | Inovacao operacional integrada | source 21, 58, 74 | Orquestra API + SearXNG + Ollama |

## Nota sobre citacoes teoricas

[Rastreabilidade: source 58, 101]
As etiquetas source representam pontos de fundamentacao do documento de pesquisa utilizados para justificar decisoes de software no prototipo.
