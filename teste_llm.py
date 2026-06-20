import requests
import json

# Configuração da URL do seu Ollama (mapeado no docker-compose na 21435)
OLLAMA_URL = "http://localhost:21435/api/generate"

# O novo modelo exato que você está baixando
OLLAMA_MODEL = "alibayram/mimo-7b-rl:latest"

# A "Alma" do Bot - O System Prompt
SYSTEM_PROMPT = """Você é o Bibliobot, um assistente virtual especializado, gentil e objetivo de uma biblioteca universitária. 
Seu papel é ajudar os usuários a encontrar livros, dar dicas de pesquisa acadêmica e responder dúvidas gerais de forma clara e educada. 
Nunca invente informações. Se não souber algo, oriente o usuário a procurar um bibliotecário presencialmente."""

def test_novo_modelo_ollama():
    print(f"\n[*] Testando conexão com OLLAMA usando o modelo:\n    {OLLAMA_MODEL}...")
    
    # Payload formatado para a API do Ollama
    payload = {
        "model": OLLAMA_MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": "Olá! Estou fazendo uma consulta rápida. Quem é você e como pode me ajudar hoje?",
        "stream": False,
        "options": {
            "temperature": 0.3 # Temperatura baixa para ele ser mais objetivo e não "viajar" muito
        }
    }
    
    try:
        # Timeout aumentado para 60s, pois a primeira vez que o modelo carrega na VRAM pode demorar
        response = requests.post(OLLAMA_URL, json=payload, timeout=80)
        response.raise_for_status()
        data = response.json()
        print("\n✅ SUCESSO! OLLAMA CONECTADO E RESPONDENDO:")
        print("──────────────────────────────────────────────────")
        print(f"🤖 Bibliobot respondeu:\n\n{data.get('response', '').strip()}")
        print("──────────────────────────────────────────────────")
    except requests.exceptions.ConnectionError:
        print("\n❌ ERRO DE CONEXÃO: O Ollama não está respondendo na porta 21435.")
    except Exception as e:
        print(f"\n❌ ERRO: {e}")

if __name__ == "__main__":
    test_novo_modelo_ollama()