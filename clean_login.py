import os
import time
import requests
import base64

# Configurações alinhadas com o docker-compose
BASE_URL = "http://localhost:8088"
API_KEY = "evolution-test-token"
INSTANCE_NAME = "bibliobot"

HEADERS = {
    "Content-Type": "application/json",
    "apikey": API_KEY
}

def create_instance():
    print(f"[*] Solicitando criação da instância '{INSTANCE_NAME}'...")
    url = f"{BASE_URL}/instance/create"
    payload = {
        "instanceName": INSTANCE_NAME,
        "integration": "WHATSAPP-BAILEYS",
        "qrcode": True
    }
    
    response = requests.post(url, json=payload, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def save_qr_html(base64_data):
    html = f"""
    <html>
    <body style="background:#111; color:white; display:flex; flex-direction:column; align-items:center; margin-top:50px; font-family:sans-serif;">
        <h2>Escaneie o QR Code</h2>
        <img src="{base64_data}" style="background:white; padding:20px; border-radius:10px; width:300px;" />
    </body>
    </html>
    """
    with open("qrcode.html", "w") as f:
        f.write(html)
    print("\n[+] SUCESSO! QR Code salvo em 'qrcode.html'. Abra no navegador para escanear.")

def main():
    try:
        data = create_instance()
        
        # A v2.3.7 retorna o QR code dentro do objeto "qrcode" -> "base64"
        qr_base64 = data.get("qrcode", {}).get("base64")
        
        if qr_base64:
            save_qr_html(qr_base64)
        else:
            print("[-] A instância foi criada, mas a API não retornou o base64 imediatamente.")
            print("Resposta da API:", data)
            
    except requests.exceptions.RequestException as e:
        print(f"[-] Erro de comunicação com a API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print("Detalhes do erro:", e.response.text)

if __name__ == "__main__":
    main()