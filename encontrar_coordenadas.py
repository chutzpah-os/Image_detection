import pyautogui
import time

print("INSTRUÇÕES:")
print("1. Mova o mouse para o botão de anexar e aguarde 3 segundos")
print("2. Depois mova para o botão 'Fotos e vídeos' e aguarde 3 segundos")
print("3. Por fim, mova para o botão enviar e aguarde 3 segundos")
print("4. O programa mostrará as coordenadas em tempo real")
print("\nIniciando em 3 segundos...")
time.sleep(3)

try:
    while True:
        x, y = pyautogui.position()
        # Obtém a cor do pixel atual
        pixel = pyautogui.screenshot().getpixel((x, y))
        posicao = f"X: {str(x).ljust(4)} Y: {str(y).ljust(4)} RGB: {pixel}"
        print(posicao, end='\r')
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nPronto!")