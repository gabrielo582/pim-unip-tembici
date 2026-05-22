import requests
import random
import time
import uuid

# URL atualizada com o endpoint correto
API_URL = "https://tembice-oficial.oliveirasousa.top/location"

def gerar_pontos_mock(quantidade=30):
    pontos = []
    
    # Coordenadas iniciais baseadas no seu exemplo
    lat = -23.5672103
    lon = -46.6941766
    
    # Usando o mesmo device_id para testar o rastreamento contínuo
    device_id = str(uuid.uuid4())
    bike_id = 2
    
    for _ in range(quantidade):
        # 0.0001 graus de latitude equivale a ~11 metros.
        # Adicionamos entre 0.0001 e 0.0002 para garantir que o ponto 
        # passe no seu filtro 'dist < 5'
        lat += random.uniform(0.0001, 0.0002)
        lon += random.uniform(0.0001, 0.0002)
        
        # Removidos os campos "id" e "created_at"
        ponto = {
            "device_id": device_id,
            "bike_id": bike_id,
            "latitude": round(lat, 7),
            "longitude": round(lon, 7),
            "accuracy": round(random.uniform(3.0, 5.0), 7),
            "altitude": round(random.uniform(715.0, 735.0), 7),
            "altitude_accuracy": round(random.uniform(5.0, 30.0), 7),
            "heading": round(random.uniform(0.0, 360.0), 7),
            "speed": round(random.uniform(1.0, 3.5), 7)
        }
        pontos.append(ponto)
        
    return pontos

def inserir_na_api(pontos):
    print(f"Iniciando a inserção de {len(pontos)} pontos no endpoint /location...")
    
    for idx, ponto in enumerate(pontos, 1):
        try:
            response = requests.post(API_URL, json=ponto)
            
            # Tratando a resposta no formato que a sua API devolve
            if response.status_code == 200:
                resposta_json = response.json()
                status = resposta_json.get("status")
                
                if status == "ok":
                    db_id = resposta_json.get("id")
                    print(f"[{idx}/{len(pontos)}] Inserido! Status: OK | ID Banco: {db_id}")
                elif status == "ignored":
                    print(f"[{idx}/{len(pontos)}] Ignorado! Motivo: Ponto muito próximo (< 5m).")
                else:
                    print(f"[{idx}/{len(pontos)}] Resposta desconhecida: {resposta_json}")
            else:
                print(f"[{idx}/{len(pontos)}] Erro HTTP: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"[{idx}/{len(pontos)}] Falha de conexão: {e}")
            
        # Espera meio segundo entre as requisições para não travar seu servidor
        time.sleep(0.5)

if __name__ == "__main__":
    novos_dados = gerar_pontos_mock(quantidade=30)
    inserir_na_api(novos_dados)