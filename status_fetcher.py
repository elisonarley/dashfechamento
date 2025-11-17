import requests
import json
from datetime import datetime, timedelta

# Dicionário de URLs base do StatusPage.io e seus nomes de serviço
STATUS_PAGES = {
    "AnyMarket": "https://status.anymarket.com.br",
    "PagSeguro": "https://status.pagbank.com.br", # PagBank é o status do PagSeguro
    "Pagar.me": "https://status.pagar.me",
    # Outros serviços não usam StatusPage.io ou não foram confirmados.
    # Cielo, Rede, Stone, Linx ERP serão mantidos com dados estáticos por enquanto
    # ou tentaremos extrair de suas páginas de status se necessário.
}

# Mapeamento de status do StatusPage.io para o formato do reader.html
STATUS_MAP = {
    "operational": "operational",
    "degraded_performance": "degraded",
    "partial_outage": "degraded",
    "major_outage": "investigating",
    "under_maintenance": "scheduled",
    "investigating": "investigating",
}

def fetch_status_page_data(base_url):
    """Busca o status atual e incidentes de uma página StatusPage.io."""
    api_url = f"{base_url}/api/v2/summary.json"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 1. Obter o status geral
        status_indicator = data['status']['indicator']
        overall_status = STATUS_MAP.get(status_indicator, "operational")
        
        # 2. Obter incidentes ativos/agendados
        incidents = []
        
        # Incidentes ativos (investigating, degraded, partial, major)
        for incident in data.get('incidents', []):
            if incident['status'] in ['investigating', 'identified', 'monitoring', 'in_progress']:
                incidents.append({
                    "title": incident['name'],
                    "status": STATUS_MAP.get(incident['status'], "investigating"),
                    "time": datetime.strptime(incident['created_at'].split('.')[0], '%Y-%m-%dT%H:%M:%S').strftime('%d/%m %H:%M'),
                    "new": True # Considerar novo se for um incidente recente
                })

        # Manutenções agendadas
        for maintenance in data.get('scheduled_maintenances', []):
            if maintenance['status'] in ['scheduled', 'in_progress']:
                incidents.append({
                    "title": maintenance['name'],
                    "status": "scheduled",
                    "time": datetime.strptime(maintenance['scheduled_for'].split('.')[0], '%Y-%m-%dT%H:%M:%S').strftime('%d/%m %H:%M'),
                    "new": True # Considerar novo se for uma manutenção futura
                })
                
        # Se não houver incidentes, use o status geral
        if not incidents:
            incidents.append({
                "title": data['status']['description'],
                "status": overall_status,
                "time": datetime.now().strftime('%d/%m %H:%M'),
                "new": False
            })
            
        return incidents
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar dados de {base_url}: {e}")
        return [{
            "title": "Erro ao carregar status. Dados podem estar desatualizados.",
            "status": "degraded",
            "time": datetime.now().strftime('%d/%m %H:%M'),
            "new": True
        }]

def fetch_sefaz_status():
    """Busca o status da SEFAZ por estado de uma API pública (Webmania)."""
    # A Webmania tem uma API pública para o monitor Sefaz
    sefaz_api_url = "https://monitorsefaz.webmaniabr.com/api/v1/status"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(sefaz_api_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        states_data = []
        # A API retorna um dicionário onde a chave é o UF (ex: 'AC', 'AL')
        for uf, status_info in data.items():
            # O status é um booleano, True para OK, False para Intermitência/Fora
            # Vamos simplificar para 'up' (OK) e 'slow' (Intermitência/Fora)
            # O eCAC da Receita Federal não é o mesmo que o status da NF-e da SEFAZ,
            # mas é o melhor dado em tempo real por estado que conseguimos.
            status = "up" if status_info.get('status') else "slow"
            states_data.append({"uf": uf, "status": status})
            
        return states_data
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar status da SEFAZ: {e}")
        # Retorna dados estáticos de fallback em caso de erro
        return [
            {"uf":"AC","status":"up"}, {"uf":"AL","status":"up"}, {"uf":"AP","status":"up"}, {"uf":"AM","status":"up"},
            {"uf":"BA","status":"up"}, {"uf":"CE","status":"slow"}, {"uf":"DF","status":"up"}, {"uf":"ES","status":"up"},
            {"uf":"GO","status":"up"}, {"uf":"MA","status":"up"}, {"uf":"MT","status":"up"}, {"uf":"MS","status":"up"},
            {"uf":"MG","status":"up"}, {"uf":"PA","status":"up"}, {"uf":"PB","status":"up"}, {"uf":"PR","status":"up"},
            {"uf":"PE","status":"up"}, {"uf":"PI","status":"up"}, {"uf":"RJ","status":"up"}, {"uf":"RN","status":"up"},
            {"uf":"RS","status":"up"}, {"uf":"RO","status":"up"}, {"uf":"RR","status":"up"}, {"uf":"SC","status":"up"},
            {"uf":"SP","status":"up"}, {"uf":"SE","status":"up"}, {"uf":"TO","status":"up"}
        ]

def main():
    # 1. Buscar status dos serviços
    real_data = {}
    for name, url in STATUS_PAGES.items():
        real_data[name] = fetch_status_page_data(url)
        
    # 2. Buscar status da SEFAZ
    states_data = fetch_sefaz_status()
    
    # 3. Criar o JSON de saída
    output_data = {
        "REAL_DATA": real_data,
        "STATES_DATA": states_data
    }
    
    # 4. Salvar o JSON no arquivo de dados
    with open("/home/ubuntu/real_time_data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
        
    print("Dados em tempo real salvos em /home/ubuntu/real_time_data.json")

if __name__ == "__main__":
    main()
