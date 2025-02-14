import os
import json
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyperclip
from PIL import Image
import io
from selenium.common.exceptions import TimeoutException
import pyautogui


class RegistrosHandler(FileSystemEventHandler):
    """
    Classe que gerencia o monitoramento de arquivos e envio de mensagens no WhatsApp
    Herda de FileSystemEventHandler para detectar mudanças nos arquivos
    """
    def __init__(self, config_path=None):
        # Inicialização das variáveis da classe
        self.ultima_msg = None  # Armazena timestamp da última mensagem enviada
        self.intervalo_msgs = 5  # Intervalo mínimo entre mensagens (5 segundos)
        self.max_tentativas = 2  # Número máximo de tentativas para enviar mensagem
        self.driver = None  # Driver do Selenium para controlar o navegador
        
        # Define o caminho do arquivo de configuração
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config_whatsapp.json')
        
        # Carrega configurações e inicializa o WhatsApp
        self.carregar_config(config_path)
        self.inicializar_whatsapp()

    def carregar_config(self, config_path):
        """Carrega as configurações do arquivo JSON"""
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print(f"Erro: Arquivo de configuração não encontrado em: {config_path}")
            raise

    def inicializar_whatsapp(self):
        """Inicializa o navegador e faz login no WhatsApp Web"""
        try:
            # Configura as opções do Chrome
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")  # Maximiza a janela
            options.add_argument("--disable-notifications")  # Desativa notificações
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36")
            
            # Inicia o navegador Chrome
            self.driver = webdriver.Chrome(options=options)
            
            # Abre o WhatsApp Web
            self.driver.get("https://web.whatsapp.com")
            print("Aguarde o QR Code ser escaneado...")
            
            # Aguarda até 120 segundos para o scan do QR Code
            wait = WebDriverWait(self.driver, 120)
            
            # Procura a caixa de pesquisa
            search_box = wait.until(EC.presence_of_element_located((
                By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'
            )))
            
            print("WhatsApp Web carregado, procurando grupo...")
            
            # Procura e seleciona o grupo configurado
            search_box.clear()
            search_box.send_keys(self.config['grupo_destino'])
            time.sleep(3)
            
            # Tenta diferentes seletores para encontrar o grupo
            grupo = None
            seletores = [
                f'//span[@title="{self.config["grupo_destino"]}"]',
                f'//div[@title="{self.config["grupo_destino"]}"]',
                f'//div[contains(@title, "{self.config["grupo_destino"]}")]'
            ]
            
            # Tenta cada seletor até encontrar o grupo
            for seletor in seletores:
                try:
                    grupo = wait.until(EC.element_to_be_clickable((By.XPATH, seletor)))
                    break
                except:
                    continue
            
            if grupo is None:
                raise Exception(f"Não foi possível encontrar o grupo: {self.config['grupo_destino']}")
            
            # Clica no grupo e aguarda
            grupo.click()
            time.sleep(2)
            
            # Envia a última detecção ao inicializar
            print("Enviando última detecção...")
            self.enviar_ultima_deteccao()
            
        except Exception as e:
            print(f"Erro ao inicializar WhatsApp: {str(e)}")
            if hasattr(self, 'driver'):
                self.driver.quit()
            raise

    def enviar_ultima_deteccao(self):
        """Envia a última detecção encontrada na pasta de registros"""
        try:
            pasta_registros = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'registros')
            print(f"Verificando pasta: {pasta_registros}")
            
            # Listar todos os arquivos jpg com seus timestamps
            arquivos_jpg = []
            for arquivo in os.listdir(pasta_registros):
                if arquivo.endswith('.jpg'):
                    caminho_completo = os.path.join(pasta_registros, arquivo)
                    timestamp = os.path.getmtime(caminho_completo)  # Pegar timestamp de modificação
                    arquivos_jpg.append((arquivo, timestamp))
            
            print(f"Total de imagens encontradas: {len(arquivos_jpg)}")
            
            if not arquivos_jpg:
                print("Nenhuma imagem encontrada na pasta registros")
                return
            
            # Ordenar por timestamp e pegar o mais recente
            arquivos_jpg.sort(key=lambda x: x[1], reverse=True)  # Ordenar do mais recente para o mais antigo
            ultima_foto, timestamp = arquivos_jpg[0]
            
            # Converter timestamp para data legível
            data_modificacao = datetime.fromtimestamp(timestamp)
            print(f"Última imagem: {ultima_foto}")
            print(f"Data de modificação: {data_modificacao}")
            
            caminho_foto = os.path.join(pasta_registros, ultima_foto)
            
            # Verificar se o arquivo existe e pode ser aberto
            try:
                with Image.open(caminho_foto) as img:
                    print(f"Imagem válida: {img.format} {img.size}")
                    print(f"Caminho completo: {caminho_foto}")
            except Exception as e:
                print(f"Erro ao abrir imagem: {str(e)}")
                return
            
            # Procurar arquivo de texto correspondente
            caminho_txt = caminho_foto.replace('.jpg', '.txt')
            
            mensagem = "!! ALERTA: Mudança Identificada !!\n"
            if os.path.exists(caminho_txt):
                with open(caminho_txt, 'r') as f:
                    mensagem += f"\nDetalhes:\n{f.read()}"
            
            # Enviar mensagem e imagem
            if self.enviar_mensagem_whatsapp(mensagem):
                print("Mensagem enviada, aguardando para enviar imagem...")
                time.sleep(2)
                
                if self.enviar_arquivo(caminho_foto):
                    print("Imagem enviada com sucesso")
                else:
                    print("Falha ao enviar imagem")
            else:
                print("Falha ao enviar mensagem")
            
        except Exception as e:
            print(f"Erro ao enviar última detecção: {str(e)}")
            import traceback
            traceback.print_exc()
    
    '''def enviar_arquivo(self, caminho_arquivo):
        try:
            wait = WebDriverWait(self.driver, 20)
            
            # 1. Clicar no botão de anexo
            attach_button = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, 'span[data-testid="clip"]'
            )))
            attach_button.click()
            print("Botão de anexo clicado")
            time.sleep(2)
            
            # 2. Encontrar e clicar no input de imagem
            file_input = wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, 'input[accept="image/*,video/mp4,video/3gpp,video/quicktime"]'
            )))
            
           
            # 3. Enviar o caminho da última imagem
            caminho_absoluto = os.path.abspath(caminho_arquivo)
            file_input.send_keys(caminho_absoluto)
            print(f"Imagem selecionada: {caminho_absoluto}")
            
            time.sleep(2)  # Aguardar carregar
            
            # 4. Clicar no botão enviar
            send_button = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, 'span[data-icon="send"]'
            )))
            send_button.click()
            print("Imagem enviada")
            
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"Erro ao enviar arquivo: {str(e)}")
            print(f"Caminho do arquivo: {caminho_arquivo}")
            return False'''
    
    def enviar_arquivo(self, caminho_arquivo):
        try:
            # Aumenta o tempo de espera para garantir que o botão de anexo apareça
            print("Aguardando o botão de anexo aparecer...")
            wait = WebDriverWait(self.driver, 30)  # Aumenta o tempo de espera para até 30 segundos

            try:
                # 1. Tentar encontrar o botão de anexo com o seletor original
                attach_button = wait.until(EC.element_to_be_clickable((
                    By.CSS_SELECTOR, 'button[title="Anexar"]'
                # Seletor original do botão de anexo
                )))
                print("Botão de anexo encontrado com seletor original.")

            except:
                try:
                    # 2. Se o seletor original falhar, tentar um seletor alternativo
                    attach_button = wait.until(EC.element_to_be_clickable((
                        By.CSS_SELECTOR, 'span[data-icon="plus"]'
                    # Seletor alternativo
                    )))
                    print("Botão de anexo encontrado com seletor alternativo.")
                except:
                    print("Erro: Não foi possível encontrar o botão de anexo.")
                    return False  # Se o botão não for encontrado, retorna False

            # 2. Clicar no botão de anexo
            attach_button.click()
            print("Botão de anexo clicado")

            # 3. Esperar o campo de input de arquivo de imagem aparecer
            file_input = wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, 'input[accept="image/*,video/mp4,video/3gpp,video/quicktime"]'  # Campo para enviar arquivos
            )))

            # Verificar se o arquivo existe antes de enviá-lo
            caminho_absoluto = os.path.abspath(caminho_arquivo)
            if not os.path.exists(caminho_absoluto):
                print(f"Erro: Arquivo não encontrado: {caminho_absoluto}")
                return False  # Se o arquivo não existir, retorna False

            # 4. Enviar o caminho absoluto do arquivo
            file_input.send_keys(caminho_absoluto)
            print(f"Imagem selecionada: {caminho_absoluto}")

            # 5. Aguardar o botão de envio ficar visível e clicável
            send_button = wait.until(EC.element_to_be_clickable((
                By.CSS_SELECTOR, 'span[data-icon="send"]'  # Botão de envio
            )))
            send_button.click()
            print("Imagem enviada com sucesso")

            # Espera um pouco para garantir que a imagem foi enviada antes de retornar
            time.sleep(2)
            return True  # Retorna True se a imagem foi enviada com sucesso

        except Exception as e:
            # Captura qualquer erro e exibe a mensagem no log
            print(f"Erro ao enviar arquivo: {str(e)}")
            print(f"Caminho do arquivo: {caminho_arquivo}")
        return False  # Se houve erro, retorna False



    def enviar_mensagem_whatsapp(self, mensagem, tentativa=0):
        if tentativa >= self.max_tentativas:
            print("Número máximo de tentativas excedido")
            return False
        
        try:
            wait = WebDriverWait(self.driver, 10)
            
            # Tentar diferentes seletores para o campo de mensagem
            seletores_mensagem = [
                "//div[@contenteditable='true'][@data-tab='10']",  # Campo de mensagem principal
                "//div[@contenteditable='true'][@data-tab='6']",   # Campo alternativo
                "//div[@title='Digite uma mensagem']",             # Por título
                "//footer//div[@contenteditable='true']",          # Por localização
                "//div[contains(@class, 'selectable-text')][@contenteditable='true']"  # Por classe
            ]
            
            message_box = None
            for seletor in seletores_mensagem:
                try:
                    message_box = wait.until(EC.presence_of_element_located((By.XPATH, seletor)))
                    print(f"Campo de mensagem encontrado com seletor: {seletor}")
                    break
                except:
                    continue
            
            if message_box is None:
                raise Exception("Campo de mensagem não encontrado")
            
            # Garantir que o campo está focado
            message_box.click()
            time.sleep(1)
            
            # Enviar mensagem
            message_box.clear()
            # Enviar linha por linha para evitar problemas com quebras de linha
            for linha in mensagem.split('\n'):
                message_box.send_keys(linha)
                message_box.send_keys(Keys.SHIFT + Keys.ENTER)
            
            # Enviar a mensagem
            message_box.send_keys(Keys.ENTER)
            print("Mensagem enviada com sucesso")
            
            return True
            
        except Exception as e:
            print(f"Erro ao enviar mensagem (tentativa {tentativa + 1}): {str(e)}")
            if tentativa < self.max_tentativas - 1:
                time.sleep(5)
                return self.enviar_mensagem_whatsapp(mensagem, tentativa + 1)
            return False

    def on_created(self, event):
        if event.is_directory:
            return

        # Aguardar um pouco para garantir que o arquivo foi completamente escrito
        time.sleep(1)
        
        agora = datetime.now()
        if (self.ultima_msg and 
            (agora - self.ultima_msg).total_seconds() < self.intervalo_msgs):
            return

        # Se for arquivo de texto, ler conteúdo
        if event.src_path.endswith('.txt'):
            print(f"Novo arquivo detectado: {event.src_path}")
            
            with open(event.src_path, 'r') as f:
                conteudo = f.read()
            
            # Procurar arquivo de imagem correspondente
            caminho_foto = event.src_path.replace('.txt', '.jpg')
            print(f"Procurando imagem: {caminho_foto}")
            
            if os.path.exists(caminho_foto):
                print(f"Imagem encontrada: {caminho_foto}")
                
                mensagem = "!! ALERTA: Mudança Identificada !!\n"
                mensagem += f"Data/Hora: {agora.strftime('%d/%m/%Y %H:%M:%S')}\n"
                mensagem += f"\nDetalhes:\n{conteudo}"
                
                if self.enviar_mensagem_whatsapp(mensagem):
                    time.sleep(2)
                    if self.enviar_arquivo(caminho_foto):
                        print(f"Alerta e imagem enviados para o grupo: {self.config['grupo_destino']}")
                        self.ultima_msg = agora
                    else:
                        print("Falha ao enviar imagem")
                else:
                    print("Falha ao enviar mensagem")
            else:
                print(f"Imagem não encontrada: {caminho_foto}")

def monitorar_registros(pasta_registros=None):
    if pasta_registros is None:
        pasta_registros = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'registros')
    
    event_handler = RegistrosHandler()
    observer = Observer()
    observer.schedule(event_handler, pasta_registros, recursive=False)
    observer.start()

    print(f"Monitorando pasta: {pasta_registros}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if hasattr(event_handler, 'driver'):
            event_handler.driver.quit()
        print("\nMonitoramento finalizado.")
    
    observer.join()

if __name__ == "__main__":
    monitorar_registros()
    