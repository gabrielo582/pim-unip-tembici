import requests

api_url = "https://tembici.oliveirasousa.top/components"

componentes = [
    "Quadro", "Garfo / Suspensão", "Guidão", "Mesa / Avanço", 
    "Selim", "Canote", "Roda Dianteira", "Roda Traseira", 
    "Pneu Dianteiro", "Pneu Traseiro", "Pedais", "Pedivela", 
    "Corrente", "Cassete / Catraca", "Câmbio Traseiro", 
    "Câmbio Dianteiro", "Trocadores de Marcha", "Freio Dianteiro", 
    "Freio Traseiro", "Movimento Central", "Caixa de Direção"
]

print("Iniciando cadastro de componentes...")

for comp in componentes:
    resposta = requests.post(api_url, json={"title": comp})
    if resposta.status_code == 200:
        print(f"✅ '{comp}' cadastrado com sucesso!")
    else:
        print(f"❌ Erro ao cadastrar '{comp}': {resposta.status_code} - {resposta.text}")

print("🎉 Processo finalizado!")