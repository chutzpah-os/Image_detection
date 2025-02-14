import tkinter as tk
from tkinter import messagebox
from src.monitoramento import CPMCMonitoramento

class CPMCInterface:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CPMC - Monitoramento")
        self.root.geometry("400x300")
        
        self.monitoramento = CPMCMonitoramento()
        self.criar_interface_principal()

    def criar_interface_principal(self):
        # Limpar janela atual
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Título
        titulo = tk.Label(self.root, text="CPMC - Sistema de Monitoramento", font=('Arial', 14, 'bold'))
        titulo.pack(pady=20)
        
        # Botões
        btn_manual = tk.Button(self.root, text="Modo Manual", command=self.iniciar_modo_manual,
                             width=20, height=2)
        btn_manual.pack(pady=10)
        
        btn_automatico = tk.Button(self.root, text="Modo Automático", command=self.iniciar_modo_automatico,
                                 width=20, height=2)
        btn_automatico.pack(pady=10)
        
        btn_instrucoes = tk.Button(self.root, text="Instruções", command=self.mostrar_instrucoes,
                                 width=20, height=2)
        btn_instrucoes.pack(pady=10)
        
        btn_sair = tk.Button(self.root, text="Sair", command=self.root.quit,
                            width=20, height=2)
        btn_sair.pack(pady=10)

    def mostrar_instrucoes(self):
        # Limpar janela atual
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Título
        titulo = tk.Label(self.root, text="Instruções de Uso", font=('Arial', 14, 'bold'))
        titulo.pack(pady=20)
        
        # Frame para texto com scroll
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Texto das instruções
        texto = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set, height=10)
        texto.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        instrucoes = """Instruções do Sistema de Monitoramento:

1. Modos de Operação:
   - Modo Manual: Monitoramento contínuo sem restrições de horário
   - Modo Automático: Monitoramento com detecção de movimento e pessoas
   
2. Durante o Monitoramento:
   - Pressione 'S' para sair do modo de monitoramento
   - O sistema detecta e diferencia entre pessoas e objetos em movimento
   - Pessoas são marcadas em azul
   - Objetos em movimento são marcados em verde
   
3. Registros:
   - Fotos e logs são salvos automaticamente na pasta 'registros'
   - Intervalo mínimo entre registros: 10 segundos
   
4. Horário de Operação (Modo Automático):
   - Funciona entre 21:00 e 08:00
   - Fora desse horário, o sistema fica em espera

5. Dicas:
   - Mantenha a câmera em posição estável
   - Evite mudanças bruscas de iluminação
   - Certifique-se de que a área monitorada está bem iluminada"""
        
        texto.insert(tk.END, instrucoes)
        texto.config(state=tk.DISABLED)  # Torna o texto somente leitura
        
        scrollbar.config(command=texto.yview)
        
        # Botão Voltar
        btn_voltar = tk.Button(self.root, text="Voltar", command=self.criar_interface_principal,
                              width=20, height=2)
        btn_voltar.pack(pady=20)

    def iniciar_modo_manual(self):
        self.monitoramento.modo_manual = True
        self.monitoramento.modo_automatico = False
        self.monitoramento.iniciar_monitoramento()
        
    def iniciar_modo_automatico(self):
        self.monitoramento.modo_manual = False
        self.monitoramento.modo_automatico = True
        self.monitoramento.iniciar_monitoramento()

    def iniciar(self):
        self.root.mainloop()


