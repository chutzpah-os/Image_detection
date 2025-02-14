import os
import sys

# Adicionar diretório raiz ao PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def main():
    from src.monitoramento import CPMCMonitoramento
    
    # Inicializar o monitoramento
    monitor = CPMCMonitoramento()
    monitor.modo_automatico = True
    
    print("\nIniciando monitoramento da pasta registros...")
    print("Pressione 's' para sair")
    
    # Monitorar a pasta registros
    pasta_registros = os.path.join(current_dir, 'registros')
    if not os.path.exists(pasta_registros):
        os.makedirs(pasta_registros)
        print(f"Pasta {pasta_registros} criada")
    
    print(f"Monitorando pasta: {pasta_registros}")
    monitor.iniciar_monitoramento()

if __name__ == "__main__":
    main()