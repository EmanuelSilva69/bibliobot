# BiblioBot-UFMA

Chatbot de recomendacao academica via WhatsApp, usando RAG + LLM local (Ollama) e Evolution API.

## Requisitos

- Docker e Docker Compose
- Ollama rodando no host (http://localhost:11434)
- Modelo de LLM (ver "Baixar o Modelo" abaixo)

## Baixar o Modelo

O bot usa um modelo 7B quantizado (Q4_K_M, ~4.7GB). Escolha um:

```bash
# Recomendado (leve e rapido)
ollama pull alibayram/mimo-7b-rl:latest

# Alternativo (mais preciso, ~8GB)
ollama pull hf.co/jedisct1/MiMo-7B-RL-GGUF:Q8_0
```

O modelo de embeddings e baixado automaticamente na primeira execucao.

## Configuracao

1. Copie o arquivo de ambiente:
   ```bash
   cp .env.example .env
   ```

2. Edite `.env` com suas configuracoes:
   ```env
   EVOLUTION_API_KEY=sua-chave-evolution-api
   ALLOWED_GROUP_JID=120363416054057157@g.us
   BOT_JID=559891339574@s.whatsapp.net
   ALLOWED_NUMBERS=559891118303@s.whatsapp.net
   OLLAMA_MODEL=alibayram/mimo-7b-rl:latest
   ```

### Variaveis de Ambiente

| Variavel | Descricao | Obrigatorio |
|---|---|---|
| `EVOLUTION_API_KEY` | Chave de autenticacao da Evolution API | Sim |
| `ALLOWED_GROUP_JID` | Grupo do WhatsApp que o bot atende | Opcional |
| `BOT_JID` | JID do bot (numero@s.whatsapp.net) | Opcional (para mencao) |
| `ALLOWED_NUMBERS` | Numeros privados permitidos (separados por virgula) | Opcional |
| `OLLAMA_MODEL` | Modelo Ollama a ser usado | Opcional |
| `MAX_RECOMMENDATIONS` | Maximo de recomendacoes (padrao: 3) | Opcional |
| `HTTP_TIMEOUT` | Timeout para chamadas LLM em segundos (padrao: 60) | Opcional |

## Executar

```bash
# Construir e iniciar todos os servicos
docker compose up --build -d

# Verificar se esta rodando
curl http://localhost:18000/health
# Resposta: {"status":"ok","service":"bibliobot-ufma"}
```

### Servicos iniciados

| Servico | Porta (host) | Descricao |
|---|---|---|
| Bibliobot | 18000 | API do chatbot |
| Evolution API | 8088 | Interface WhatsApp |
| SearXNG | 18081 | Busca na web (opcional) |

## Conectar o WhatsApp

1. Acesse http://localhost:8088/manager
2. Crie uma instancia chamada `bibliobot`
3. Escaneie o QR Code com o WhatsApp
4. Configure o webhook para http://bibliobot:8000/webhook

Ou use o script auxiliar:
```bash
python get_qr.py
```

## Uso

### No grupo permitido

Mencione o bot com @numero para receber recomendacoes:
```
@559891339574 recomende livros de matematica
```

### No privado (numeros permitidos)

Envie a mensagem diretamente:
```
recomende livros cristaos
```

### API REST

```bash
curl -X POST http://localhost:18000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u01","message":"livros de calculo"}'
```

## Estrutura do Projeto

```
├── app/
│   ├── main.py              # API FastAPI e webhook
│   ├── engine.py            # Motor RAG + LLM
│   ├── rag_core.py          # Busca vetorial ChromaDB
│   ├── evolution_client.py  # Integracao Evolution API
│   ├── prompts.py           # Prompts do sistema
│   └── data/acervo.json     # Catalogo de livros (100 obras)
├── docker-compose.yml       # Orquestracao dos servicos
├── Dockerfile               # Imagem do bot
└── .env.example             # Template de configuracao
```
