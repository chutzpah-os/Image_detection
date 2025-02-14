import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import glob

def limpar_registros_antigos(pasta_registros):
    LIMITE_TAMANHO = 1 * 1024 * 1024 * 1024  # 1GB em bytes
    
    tamanho_total = sum(os.path.getsize(os.path.join(pasta_registros, f)) 
                       for f in os.listdir(pasta_registros) 
                       if os.path.isfile(os.path.join(pasta_registros, f)))
    
    if tamanho_total > LIMITE_TAMANHO:
        arquivos_jpg = sorted(
            glob.glob(os.path.join(pasta_registros, "*.jpg")),
            key=os.path.getctime
        )
        arquivos_txt = sorted(
            glob.glob(os.path.join(pasta_registros, "*.txt")),
            key=os.path.getctime
        )
        
        for arquivo in arquivos_jpg[:10] + arquivos_txt[:10]:
            try:
                os.remove(arquivo)
            except:
                pass

class MonitoramentoHandler(FileSystemEventHandler):
    def __init__(self, pasta_registros):
        self.pasta_registros = pasta_registros
        
    def on_created(self, event):
        if event.is_directory:
            return
        
        if event.src_path.endswith('.txt'):
            limpar_registros_antigos(self.pasta_registros)

def iniciar_monitoramento(pasta_registros):
    event_handler = MonitoramentoHandler(pasta_registros)
    observer = Observer()
    observer.schedule(event_handler, pasta_registros, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    # Ajustando o caminho para a pasta de registros
    PASTA_REGISTROS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "registros")
    
    # Certifique-se de que a pasta existe
    if not os.path.exists(PASTA_REGISTROS):
        os.makedirs(PASTA_REGISTROS)
    
    iniciar_monitoramento(PASTA_REGISTROS)