import os
import sys

# Adicionar diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.interface import nomeInterface

if __name__ == "__main__":
    interface = nomeInterface()
    interface.iniciar()
