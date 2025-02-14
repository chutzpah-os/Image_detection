import cv2
import numpy as np
import datetime
import os
import time

class CPMCMonitoramento:
    def __init__(self, pasta_registros='../registros', rosto_cascade_path='assets/haarcascade_frontalface_default.xml'):
        # Usar caminho relativo para pasta registros na raiz
        pasta_registros = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'registros')
        os.makedirs(pasta_registros, exist_ok=True)
        self.pasta_registros = pasta_registros
        
        # Carregar os classificadores
        cascade_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), rosto_cascade_path)
        self.rosto_cascade = cv2.CascadeClassifier(cascade_path)
        
        if self.rosto_cascade.empty():
            raise ValueError(f"Erro ao carregar o arquivo Haar Cascade em: {cascade_path}")
        
        # Adicionar detector HOG para corpo inteiro
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        
        # Ajustar parâmetros
        self.area_minima_objeto = 2500
        self.area_minima_pessoa = 3000    # Área mínima para considerar pessoa
        self.limiar_movimento = 25
        self.min_movimento = 20
        self.historia_movimento = 30
        self.skip_frames = 2
        self.margem_pessoa = 40
        self.confianca_pessoa = 0.2       # Reduzir para detectar mais pessoas
        self.min_movimento_pessoa = 20
        self.tamanho_buffer = 3
        self.frame_count = 0
        self.ultimo_frame = None
        self.buffer_deteccoes = []        # Buffer para estabilizar detecções
        self.frame_atual = None
        self.modo_automatico = False
        self.modo_manual = False
        self.ultima_detecao = None
        self.monitorando = False
        self.intervalo_fotos = 5  # intervalo em segundos entre fotos
        
        self.fundo_subtrator = cv2.createBackgroundSubtractorMOG2(
            detectShadows=False,
            history=self.historia_movimento,
            varThreshold=self.limiar_movimento
        )

    def verificar_horario_operacao(self):
        # Se estiver em modo manual, sempre permitir operação
        if self.modo_manual:
            return True
        
        # Se estiver em modo automático, verificar horário
        if self.modo_automatico:
            agora = datetime.datetime.now().time()
            return (agora >= datetime.time(9, 0) or agora < datetime.time(8, 0))
            
        return False  # Se não estiver em nenhum modo, não operar

    def detectar_movimento_significativo(self, frame):
        frame_pequeno = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        cinza = cv2.cvtColor(frame_pequeno, cv2.COLOR_BGR2GRAY)
        cinza = cv2.GaussianBlur(cinza, (11, 11), 0)  # Reduzir kernel do blur
        
        if self.ultimo_frame is None:
            self.ultimo_frame = cinza
            return False, [], cinza
        
        # Detectar movimento
        diff_frame = cv2.absdiff(self.ultimo_frame, cinza)
        self.ultimo_frame = cinza
        
        # Threshold mais sensível
        thresh = cv2.threshold(diff_frame, self.limiar_movimento, 255, cv2.THRESH_BINARY)[1]
        kernel = np.ones((3,3), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=3)  # Aumentar iterações
        
        contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        contornos_significativos = []
        for c in contornos:
            area = cv2.contourArea(c) * 4
            if area > self.area_minima_objeto:
                # Verificar movimento na região
                x, y, w, h = cv2.boundingRect(c)
                roi = thresh[y:y+h, x:x+w]
                if np.mean(roi) > self.min_movimento:
                    c = c * 2  # Ajustar para tamanho original
                    contornos_significativos.append(c)
        
        return len(contornos_significativos) > 0, contornos_significativos, thresh

    def estabilizar_deteccoes(self, deteccoes_atuais, tipo='objeto'):
        if not deteccoes_atuais:
            return []
            
        self.buffer_deteccoes.append(deteccoes_atuais)
        if len(self.buffer_deteccoes) > self.tamanho_buffer:
            self.buffer_deteccoes.pop(0)
        
        return deteccoes_atuais  # Retornar detecções sem estabilização por enquanto

    def detectar_pessoas(self, frame, mascara_movimento):
        pessoas_detectadas = []
        
        # 1. Primeiro tentar detectar rostos
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cinza = cv2.equalizeHist(cinza)
        
        rostos = self.rosto_cascade.detectMultiScale(
            cinza,
            scaleFactor=1.2,
            minNeighbors=4,
            minSize=(25, 25),
            maxSize=(150, 150)
        )
        
        # 2. Detectar corpos (sempre)
        corpos, weights = self.hog.detectMultiScale(
            frame,
            winStride=(4, 4),
            padding=(8, 8),
            scale=1.05
        )
        
        # Processar detecções de corpo primeiro
        for (x, y, w, h), peso in zip(corpos, weights):
            if peso > self.confianca_pessoa:
                area = w * h
                if area > self.area_minima_pessoa:
                    # Verificar movimento na região
                    roi = mascara_movimento[y:y+h, x:x+w]
                    if roi.size > 0 and np.mean(roi) > self.min_movimento_pessoa:
                        # Procurar rosto próximo
                        rosto_encontrado = False
                        for (rx, ry, rw, rh) in rostos:
                            if (rx > x - w//4 and rx < x + w and
                                ry > y - h//4 and ry < y + h):
                                pessoas_detectadas.append({
                                    'corpo': (x, y, w, h),
                                    'rosto': (rx, ry, rw, rh)
                                })
                                rosto_encontrado = True
                                break
                        
                        # Se não encontrou rosto, mas detectou corpo em movimento
                        if not rosto_encontrado:
                            # Criar área estimada do rosto
                            rosto_y = max(0, y + h//4)
                            rosto_h = h//4
                            rosto_w = w//3
                            rosto_x = x + (w - rosto_w)//2
                            
                            pessoas_detectadas.append({
                                'corpo': (x, y, w, h),
                                'rosto': (rosto_x, rosto_y, rosto_w, rosto_h)
                            })
        
        # 3. Processar rostos que não foram associados a corpos
        for (x, y, w, h) in rostos:
            ja_detectado = False
            for pessoa in pessoas_detectadas:
                rx, ry, rw, rh = pessoa['rosto']
                if abs(x - rx) < w and abs(y - ry) < h:
                    ja_detectado = True
                break
            
            if not ja_detectado:
                roi_rosto = mascara_movimento[y:y+h, x:x+w]
                if roi_rosto.size > 0 and np.mean(roi_rosto) > self.min_movimento_pessoa:
                    # Expandir área para corpo
                    y2 = min(frame.shape[0], y + h * 3)
                    x1 = max(0, x - w//2)
                    x2 = min(frame.shape[1], x + w + w//2)
                    
                    pessoas_detectadas.append({
                        'corpo': (x1, y, x2-x1, y2-y),
                        'rosto': (x, y, w, h)
                    })
        
        return pessoas_detectadas

    def verificar_sobreposicao(self, det1, det2):
        x1, y1, w1, h1 = det1
        x2, y2, w2, h2 = det2
        
        # Verificar sobreposição com margem maior
        return (abs(x1 - x2) < (w1 + w2)/2 + 50 and
                abs(y1 - y2) < (h1 + h2)/2 + 50)

    def mesclar_deteccoes(self, deteccoes):
        if not deteccoes:
            return []
        
        # Mesclar detecções sobrepostas
        deteccoes_mescladas = []
        deteccoes = sorted(deteccoes, key=lambda x: x[2] * x[3], reverse=True)
        
        while deteccoes:
            atual = deteccoes.pop(0)
            x1, y1, w1, h1 = atual
            
            # Verificar sobreposição com outras detecções
            i = 0
            while i < len(deteccoes):
                x2, y2, w2, h2 = deteccoes[i]
                
                # Se houver sobreposição significativa
                if (x1 < x2 + w2 and x1 + w1 > x2 and
                    y1 < y2 + h2 and y1 + h1 > y2):
                    # Usar a maior área
                    x1 = min(x1, x2)
                    y1 = min(y1, y2)
                    w1 = max(x1 + w1, x2 + w2) - x1
                    h1 = max(y1 + h1, y2 + h2) - y1
                    deteccoes.pop(i)
                else:
                    i += 1
            
            deteccoes_mescladas.append((x1, y1, w1, h1))
        
        return deteccoes_mescladas

    def desenhar_deteccoes(self, frame, pessoas, contornos):
        objetos_validos = []
        
        # Primeiro, processar as pessoas detectadas
        areas_pessoas = []
        for pessoa in pessoas:
            rx, ry, rw, rh = pessoa['rosto']
            cx, cy, cw, ch = pessoa['corpo']
            
            # Desenhar retângulo do corpo
            cv2.rectangle(frame, (cx, cy), (cx + cw, cy + ch), (0, 0, 255), 2)
            cv2.putText(frame, "Pessoa em movimento", (cx, cy-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # Guardar área da pessoa para comparação
            areas_pessoas.append((cx, cy, cw, ch))
        
        # Depois, processar os contornos de movimento
        for contorno in contornos:
            x, y, w, h = cv2.boundingRect(contorno)
            area_objeto = w * h
            
            # Filtrar objetos muito pequenos ou muito grandes
            area_minima = frame.shape[0] * frame.shape[1] * 0.001  # 0.1% da imagem
            area_maxima = frame.shape[0] * frame.shape[1] * 0.5    # 50% da imagem
            
            if area_minima < area_objeto < area_maxima:
                # Verificar sobreposição com pessoas
                sobrepoe_pessoa = False
                for px, py, pw, ph in areas_pessoas:
                    x_overlap = max(0, min(x + w, px + pw) - max(x, px))
                    y_overlap = max(0, min(y + h, py + ph) - max(y, py))
                    area_overlap = x_overlap * y_overlap
                    
                    if area_overlap > 0.3 * min(area_objeto, pw * ph):
                        sobrepoe_pessoa = True
                        break
                
                # Se não sobrepõe com pessoa, marcar como objeto
                if not sobrepoe_pessoa:
                    objetos_validos.append((x, y, w, h))
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, "Objeto em movimento", (x, y-10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return objetos_validos, pessoas

    def salvar_deteccoes(self, frame, movimento_detectado, pessoas, objetos):
        agora = datetime.datetime.now()
        
        if len(pessoas) > 0 or len(objetos) > 0:
            if (not self.ultima_detecao or 
                (agora - self.ultima_detecao).total_seconds() > self.intervalo_fotos):
                
                prefixo = agora.strftime("%Y%m%d_%H%M%S")
                caminho_foto = os.path.join(self.pasta_registros, f'{prefixo}_movimento.jpg')
                cv2.imwrite(caminho_foto, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                # Log mais detalhado
                with open(os.path.join(self.pasta_registros, f'{prefixo}_movimento.txt'), 'w') as f:
                    f.write(f"Detecção em: {agora}\n")
                    if len(pessoas) > 0:
                        f.write(f"Pessoas detectadas: {len(pessoas)}\n")
                    if len(objetos) > 0:
                        f.write(f"Objetos detectados: {len(objetos)}\n")
                
                self.ultima_detecao = agora
                print(f"Detecção salva em: {caminho_foto}")

    def iniciar_monitoramento(self):
        try:
            # Tentar diferentes backends e índices de câmera
            cap = None
            backends = [
                cv2.CAP_ANY,      # Deixar OpenCV escolher
                cv2.CAP_DSHOW,    # DirectShow
                cv2.CAP_MSMF      # Media Foundation
            ]
            
            for backend in backends:
                for camera_index in range(2):
                    try:
                        print(f"Tentando câmera {camera_index} com backend {backend}")
                        cap = cv2.VideoCapture(camera_index + backend)
                        if cap is not None and cap.isOpened():
                            print(f"Câmera {camera_index} aberta com sucesso usando backend {backend}")
                            break
                    except Exception as e:
                        print(f"Erro ao tentar câmera {camera_index} com backend {backend}: {str(e)}")
                        continue
                
                if cap is not None and cap.isOpened():
                    break

            if cap is None or not cap.isOpened():
                raise Exception("Não foi possível acessar nenhuma câmera. Verifique se a câmera está conectada e funcionando.")

            # Configurar parâmetros da câmera
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            
            # Verificar se as configurações foram aplicadas
            largura_atual = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            altura_atual = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps_atual = int(cap.get(cv2.CAP_PROP_FPS))
            
            print("\nConfiguração da câmera:")
            print(f"Resolução: {largura_atual}x{altura_atual}")
            print(f"FPS: {fps_atual}")
            
            self.monitorando = True
            self.frame_atual = None
            
            print("Câmera iniciada com sucesso")
            print(f"Resolução: {largura_atual}x{altura_atual}")
            print(f"FPS: {fps_atual}")

            while self.monitorando:
                ret, frame = cap.read()
                if not ret:
                    print("Erro ao ler frame da câmera")
                    break
                
                if self.modo_automatico:
                    frame_exibicao = frame.copy()
                    
                    # Detectar movimento e pessoas
                    movimento_detectado, contornos, mascara_movimento = self.detectar_movimento_significativo(frame)
                    pessoas = self.detectar_pessoas(frame, mascara_movimento)
                    
                    # Desenhar detecções
                    objetos_validos, pessoas_detectadas = self.desenhar_deteccoes(frame_exibicao, pessoas, contornos)
                    
                    # Salvar se houver detecções
                    if len(pessoas_detectadas) > 0 or len(objetos_validos) > 0:
                        self.salvar_deteccoes(frame_exibicao, movimento_detectado, pessoas_detectadas, objetos_validos)
                    
                    cv2.imshow('CPMC - Monitoramento', frame_exibicao)
                else:
                    cv2.imshow('CPMC - Monitoramento', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('s'):
                    break
                
                time.sleep(0.01)

        except Exception as e:
            print(f"Erro ao iniciar monitoramento: {str(e)}")
        finally:
            if cap is not None:
                cap.release()
            cv2.destroyAllWindows()
            print("Monitoramento finalizado.")


