import requests
import base64

# Configurações
BASE_URL = "http://localhost:8088"
API_KEY = "evolution-test-token"
INSTANCE_NAME = "bibliobot"

HEADERS = {"apikey": API_KEY}

def get_new_qr():
    print(f"[*] Solicitando novo QR Code para '{INSTANCE_NAME}'...")
    url = f"{BASE_URL}/instance/connect/{INSTANCE_NAME}"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        
        qr_base64 = data.get("base64")
        
        if qr_base64:
            html = f"""
            <html>
            <body style="background:#111; color:white; display:flex; flex-direction:column; align-items:center; margin-top:50px; font-family:sans-serif;">
                <h2>QR Code Atualizado - ESCANEIE RÁPIDO!</h2>
                <img src="{qr_base64}" style="background:white; padding:20px; border-radius:10px; width:300px;" />
            </body>
            </html>
            """
            with open("qrcode.html", "w") as f:
                f.write(html)
            print("\n[+] SUCESSO! Novo QR Code salvo. ABRA O HTML E ESCANEIE AGORA!")
        else:
            print("[-] A API não retornou o QR. Talvez o WhatsApp já esteja conectado ou o Baileys travou de novo.")
            print("Estado atual:", data)
            
    except requests.exceptions.RequestException as e:
        print(f"[-] Erro de comunicação: {e}")

if __name__ == "__main__":
    get_new_qr()