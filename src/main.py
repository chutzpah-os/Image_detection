import os
import sys

# Adicionar diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.interface import CPMCInterface

if __name__ == "__main__":
    interface = CPMCInterface()
    interface.iniciar()
