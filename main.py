import requests
import pandas as pd
from PIL import Image, ImageTk
from io import BytesIO
import time
import tkinter as tk
from tkinter import filedialog, Scrollbar, Canvas, Frame

# Chaves e URLs da API
subscription_key = '6eZi825I9Re3BG66v541jXtiUnweH8fGNTE7KNqj5er6RYPHW80MJQQJ99ALACZoyfiXJ3w3AAAFACOGZ8AT'
analyze_url = 'https://felipesegundodealexandremonteiro.cognitiveservices.azure.com/vision/v3.2/read/analyze'

# Função para converter imagem para JPEG
def convert_to_jpeg(image):
    with BytesIO() as output:
        image.save(output, format="JPEG")
        return output.getvalue()

# Função para redimensionar a imagem para o tamanho da tela
def resize_image(image, max_width, max_height):
    # Calcular a proporção para ajustar a imagem
    width_percent = (max_width / float(image.size[0]))
    height_percent = (max_height / float(image.size[1]))
    # Usar a menor proporção para garantir que a imagem caiba na tela
    percent = min(width_percent, height_percent)
    
    new_width = int(float(image.size[0]) * percent)
    new_height = int(float(image.size[1]) * percent)
    
    return image.resize((new_width, new_height), Image.LANCZOS)

# Função para extrair texto e caixas delimitadoras da imagem usando a API do Azure
def extract_text_and_boxes(image_bytes):
    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/octet-stream"
    }
    response = requests.post(analyze_url, headers=headers, data=image_bytes)
   
    if response.status_code != 202:
        print(f"Erro na solicitação: {response.status_code} - {response.text}")
        return None
       
    operation_url = response.headers["Operation-Location"]
   
    analysis = {}
    while not "analyzeResult" in analysis:
        response_final = requests.get(operation_url, headers=headers)
        analysis = response_final.json()
       
        if response_final.status_code != 200:
            print(f"Erro na solicitação final: {response_final.status_code} - {response_final.text}")
            return None
       
        time.sleep(3)  # Aumentar o tempo de espera para 3 segundos
   
    return analysis

# Inicializar a tabela de dados
descricao = pd.DataFrame(columns=["Textos Detectados"])

# Função para desenhar a caixa delimitadora na imagem
def draw_bbox(event):
    global bbox_start, bbox_end, rect
    canvas_yview = canvas.yview()
    scroll_y = canvas_yview[0] * canvas.winfo_height()

    if bbox_start is None:
        bbox_start = (event.x, event.y + scroll_y)
    else:
        bbox_end = (event.x, event.y + scroll_y)
        if rect:
            canvas.coords(rect, bbox_start[0], bbox_start[1], bbox_end[0], bbox_end[1])
        else:
            rect = canvas.create_rectangle(bbox_start[0], bbox_start[1], bbox_end[0], bbox_end[1], outline='green')

# Função principal para carregar e processar a imagem
def main():
    global canvas, bbox_start, bbox_end, rect, descricao, root

    # Criar uma janela Tkinter
    root = tk.Tk()
    root.title("Seleção de Caixa Delimitadora")
   
    # Abrir a caixa de diálogo para selecionar o arquivo
    file_path = filedialog.askopenfilename(title="Selecione um arquivo JPG", filetypes=[("JPG files", "*.jpg")])
   
    if not file_path:
        print("Nenhum arquivo selecionado.")
        return
   
    try:
        with open(file_path, 'rb') as uploaded_file:
            image_bytes = uploaded_file.read()
       
        # Converter a imagem para JPEG
        image = Image.open(BytesIO(image_bytes))
        
        # Obter o tamanho da tela
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        # Redimensionar a imagem para caber na tela
        image = resize_image(image, max_width=screen_width, max_height=screen_height)  
        image_bytes = convert_to_jpeg(image)
       
        # Criar um frame com barra de rolagem
        frame = Frame(root)
        frame.pack(fill=tk.BOTH, expand=1)
       
        # Adicionar canvas ao frame
        canvas = Canvas(frame)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
       
        # Adicionar barra de rolagem ao canvas
        scrollbar = Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
       
        # Configurar o canvas com a barra de rolagem
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
       
        # Adicionar um frame dentro do canvas
        inner_frame = Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor="nw")
       
        # Exibir a imagem carregada
        tk_image = ImageTk.PhotoImage(image)
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_image)
       
        # Variáveis para armazenar as coordenadas da caixa delimitadora
        bbox_start = None
        bbox_end = None
        rect = None
       
        canvas.bind("<Button-1>", draw_bbox)
       
        # Botão para confirmar a seleção da caixa delimitadora
        def confirm_bbox():
            if bbox_start and bbox_end:
                bbox = (bbox_start[0], bbox_start[1], bbox_end[0] - bbox_start[0], bbox_end[1] - bbox_start[1])
                process_image(image, bbox, root)  # Passar root para a função
                reset_bbox()
            else:
                print("Selecione uma área da imagem.")
       
        confirm_button = tk.Button(inner_frame, text="Confirmar Seleção", command=confirm_bbox)
        confirm_button.pack()
       
        # Botão para desfazer a última caixa delimitadora
        def undo_bbox():
            global rect
            if rect:
                canvas.delete(rect)
                reset_bbox()
       
        undo_button = tk.Button(inner_frame, text="Desfazer Seleção", command=undo_bbox)
        undo_button.pack()
       
        # Botão para baixar a tabela como XLSX
        def download_xlsx():
            save_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
            if save_path:
                descricao.to_excel(save_path, index=False)
                print(f"Tabela salva como {save_path}")
       
        download_button = tk.Button(inner_frame, text="Baixar Tabela como XLSX", command=download_xlsx)
        download_button.pack()
       
        root.mainloop()
   
    except FileNotFoundError:
        print("Arquivo não encontrado. Verifique o caminho e tente novamente.")

# Função para processar a imagem e extrair texto
def process_image(image, bbox, root):
    global descricao
    cropped_image = image.crop((bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]))
    cropped_image = resize_image(cropped_image, max_width=root.winfo_screenwidth(), max_height=root.winfo_screenheight())  # Redimensionar a imagem recortada
    cropped_image_bytes = convert_to_jpeg(cropped_image)
   
    result = extract_text_and_boxes(cropped_image_bytes)
   
    if result:
        if 'analyzeResult' in result:
            detected_texts = []
            for page in result['analyzeResult']['readResults']:
                for line in page['lines']:
                    detected_texts.append(line['text'])
            if detected_texts:
                print("Textos detectados:")
                column_name = f"Textos Detectados {len(descricao.columns) + 1}"
                if column_name not in descricao.columns:
                    descricao[column_name] = ""
                for i, text in enumerate(detected_texts):
                    if i < len(descricao):
                        descricao.at[i, column_name] = text
                    else:
                        new_row = pd.Series({column_name: text})
                        descricao = pd.concat([descricao, new_row.to_frame().T], ignore_index=True)
               
                # Preencher linhas vazias com valores nulos
                max_rows = descricao.shape[0]
                for col in descricao.columns:
                    if descricao[col].isnull().sum() < max_rows:
                        descricao[col] = descricao[col].reindex(range(max_rows))
               
                # Mostrar a tabela atualizada
                print(descricao)
            else:
                print("Nenhum texto detectado na imagem recortada.")
        else:
            print("A resposta da API não contém a chave 'analyzeResult'. Verifique o endpoint e os dados retornados pela API.")
    else:
        print("Não foi possível obter o resultado da API.")

def reset_bbox():
    global bbox_start, bbox_end, rect
    bbox_start = None
    bbox_end = None
    rect = None

if __name__ == "__main__":
    main()
