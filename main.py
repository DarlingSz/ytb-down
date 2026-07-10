import os
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import urllib.request
from io import BytesIO
from PIL import Image, ImageTk

# Interface moderna e estável
import customtkinter as ctk
from yt_dlp import YoutubeDL

# Paleta de Cores Oficial Premium (YouTube Cinematic Dark)
COR_FUNDO_REAL = "#0F0F0F"       
COR_CARD_GRAFITE = "#212121"     
COR_VERMELHO_YTB = "#FF0000"     
COR_HOVER_VERMELHO = "#CC0000"
COR_TEXTO_PRINCIPAL = "#F1F1F1"  
COR_TEXTO_MUTED = "#AAAAAA"      

ctk.set_appearance_mode("Dark")

class YoutubeDownloaderPremium:
    # Inicializa a classe, configurando as duas janelas (para aparecer na barra de tarefas) e monta o layout da interface
    def __init__(self, root):
        self.root = root
        
        # --- ARQUITETURA DE JANELA DUPLA (BARRA DE TAREFAS FIXADA) ---
        # Janela invisível para garantir o registro do ícone no Windows
        self.root.title("YouTube Studio Downloader")
        self.root.geometry("0x0")
        self.root.attributes("-alpha", 0.0)
        
        # Janela customizada real sem a barra padrão do Windows
        self.main_win = ctk.CTkToplevel(self.root)
        self.main_win.title("YouTube Studio Downloader")
        self.main_win.geometry("700x680")
        self.main_win.configure(fg_color=COR_FUNDO_REAL)
        self.main_win.overrideredirect(True) 
        
        # Sincroniza fechamento e minimização entre a janela oculta e a real
        self.main_win.protocol("WM_DELETE_WINDOW", self.fechar_aplicativo)
        self.root.bind("<Unmap>", lambda e: self.main_win.withdraw())
        self.root.bind("<Map>", lambda e: self.main_win.deiconify())

        # Variáveis para armazenar a posição do mouse ao arrastar a janela
        self._start_x = 0
        self._start_y = 0

        # Configurações iniciais de caminhos e dados
        self.pasta_destino = os.path.join(os.path.expanduser("~"), "Downloads")
        self.timer_busca = None
        self.thumbnail_tk = None
        self.imagem_original_pil = None
        self.titulo_atual = "thumbnail"

        # --- BARRA DE TÍTULO CUSTOMIZADA ---
        self.barra_superior = ctk.CTkFrame(self.main_win, fg_color=COR_FUNDO_REAL, height=35, corner_radius=0)
        self.barra_superior.pack(side="top", fill="x")
        self.barra_superior.pack_propagate(False)
        
        self.barra_superior.bind("<ButtonPress-1>", self.iniciar_arrastar)
        self.barra_superior.bind("<B1-Motion>", self.arrastar_janela)

        # Botões de controle no topo (Fechar e Minimizar)
        self.btn_fechar = ctk.CTkButton(
            self.barra_superior, text="x", font=("Arial", 12, "bold"),
            fg_color="transparent", hover_color="#E50914", text_color="#FFFFFF",
            width=35, height=35, corner_radius=0, command=self.fechar_aplicativo
        )
        self.btn_fechar.pack(side="right")

        self.btn_minimizar = ctk.CTkButton(
            self.barra_superior, text="-", font=("Arial", 12, "bold"),
            fg_color="transparent", hover_color="#2A2A2A", text_color="#FFFFFF",
            width=35, height=35, corner_radius=0, command=self.minimizar_janela
        )
        self.btn_minimizar.pack(side="right")

        # --- CABEÇALHO BRANDING ---
        self.frame_header = ctk.CTkFrame(self.main_win, fg_color="transparent")
        self.frame_header.pack(pady=(10, 10), fill="x", padx=40)
        
        self.lbl_logo_icon = ctk.CTkLabel(self.frame_header, text=">", font=("Arial", 28), text_color=COR_VERMELHO_YTB)
        self.lbl_logo_icon.pack(side="left", padx=(0, 10))
        
        self.lbl_logo_texto = ctk.CTkLabel(self.frame_header, text="YouTube", font=("YouTube Sans", 24, "bold"), text_color=COR_TEXTO_PRINCIPAL)
        self.lbl_logo_texto.pack(side="left")
        
        self.lbl_logo_sub = ctk.CTkLabel(self.frame_header, text="Downloader Pro", font=("Segoe UI", 14, "italic"), text_color=COR_TEXTO_MUTED)
        self.lbl_logo_sub.pack(side="left", padx=8, pady=(6, 0))

        # --- SELEÇÃO DE PASTA DE DESTINO ---
        self.frame_pasta = ctk.CTkFrame(self.main_win, fg_color=COR_CARD_GRAFITE, corner_radius=10, height=45)
        self.frame_pasta.pack(pady=5, fill="x", padx=40)
        self.frame_pasta.pack_propagate(False)
        
        self.lbl_pasta = ctk.CTkLabel(
            self.frame_pasta, 
            text=f"Local de destino: {self.pasta_destino}", 
            font=("Segoe UI", 11), 
            text_color=COR_TEXTO_MUTED,
            anchor="w"
        )
        self.lbl_pasta.pack(side="left", padx=15, fill="x", expand=True)
        
        self.btn_mudar_pasta = ctk.CTkButton(
            self.frame_pasta, text="Alterar", font=("Segoe UI", 11, "bold"),
            fg_color="#2F2F2F", hover_color="#3F3F3F", text_color=COR_TEXTO_PRINCIPAL,
            width=75, height=28, corner_radius=15, command=self.escolher_pasta
        )
        self.btn_mudar_pasta.pack(side="right", padx=15)
        
        # --- ENTRADA DA URL ---
        self.entry_url = ctk.CTkEntry(
            self.main_win, placeholder_text="Cole a URL do video aqui...", 
            width=620, height=42, font=("Segoe UI", 13),
            fg_color="#121212", border_color="#333333", border_width=1,
            text_color=COR_TEXTO_PRINCIPAL, corner_radius=6
        )
        self.entry_url.pack(pady=10, padx=40)
        self.entry_url.bind("<KeyRelease>", self.agendar_busca_info)
        
        # --- BLOCÓ DE INFÓRMAÇÕES E PREVIEW ---
        self.frame_info = ctk.CTkFrame(self.main_win, fg_color=COR_CARD_GRAFITE, corner_radius=12)
        self.frame_info.pack(pady=10, fill="both", expand=True, padx=40)
        
        self.lbl_titulo_video = ctk.CTkLabel(
            self.frame_info, text="Insira um link para carregar o estudio de download", 
            font=("Segoe UI", 13, "bold"),  wraplength=560, text_color=COR_TEXTO_MUTED
        )
        self.lbl_titulo_video.pack(pady=12, padx=20)
        
        self.lbl_thumbnail = ctk.CTkLabel(
            self.frame_info, text="", fg_color="#121212", corner_radius=8, width=384, height=216
        )
        self.lbl_thumbnail.pack(pady=(0, 10), expand=True)
        
        self.progress_bar = ctk.CTkProgressBar(self.frame_info, width=384, height=4, fg_color="#121212", progress_color=COR_VERMELHO_YTB)
        self.progress_bar.pack(pady=(0, 12))
        self.progress_bar.set(0)
        
        # --- OPÇÕES DE FORMATO (RADIO BUTTONS) ---
        self.var_formato_dl = tk.StringVar(value="mp3")
        self.frame_opcoes = ctk.CTkFrame(self.main_win, fg_color="transparent")
        self.frame_opcoes.pack(pady=5)
        
        self.rb_mp3 = ctk.CTkRadioButton(
            self.frame_opcoes, text="Converter em Audio (MP3 HQ)", variable=self.var_formato_dl, value="mp3", 
            font=("Segoe UI", 11, "bold"), text_color=COR_TEXTO_PRINCIPAL, border_color="#555555", hover_color=COR_VERMELHO_YTB, fg_color=COR_VERMELHO_YTB
        )
        self.rb_mp3.grid(row=0, column=0, padx=20)
        
        self.rb_mp4 = ctk.CTkRadioButton(
            self.frame_opcoes, text="Baixar Video Completo (MP4 HD)", variable=self.var_formato_dl, value="mp4", 
            font=("Segoe UI", 11, "bold"), text_color=COR_TEXTO_PRINCIPAL, border_color="#555555", hover_color=COR_VERMELHO_YTB, fg_color=COR_VERMELHO_YTB
        )
        self.rb_mp4.grid(row=0, column=1, padx=20)
        
        # --- BOTÕES DE DOWNLOAD ---
        self.frame_botoes = ctk.CTkFrame(self.main_win, fg_color="transparent")
        self.frame_botoes.pack(pady=(10, 30))
        
        self.btn_download = ctk.CTkButton(
            self.frame_botoes, text="Download Midia", font=("Segoe UI", 13, "bold"),
            fg_color=COR_VERMELHO_YTB, hover_color=COR_HOVER_VERMELHO, text_color="#FFFFFF",
            height=40, width=170, corner_radius=20, state="disabled", command=self.iniciar_download_thread
        )
        self.btn_download.grid(row=0, column=0, padx=15)
        
        self.btn_download_thumb = ctk.CTkButton(
            self.frame_botoes, text="Salvar Capa (JPG)", font=("Segoe UI", 13, "bold"),
            fg_color="#2F2F2F", hover_color="#3F3F3F", text_color=COR_TEXTO_PRINCIPAL,
            height=40, width=170, corner_radius=20, state="disabled", command=self.salvar_thumbnail
        )
        self.btn_download_thumb.grid(row=0, column=1, padx=15)

    # Captura as coordenadas iniciais do clique do mouse para arrastar a janela
    def iniciar_arrastar(self, event):
        self._start_x = event.x
        self._start_y = event.y

    # Calcula a nova posicao da janela baseado no movimento do mouse
    def arrastar_janela(self, event):
        x = self.main_win.winfo_x() - self._start_x + event.x
        y = self.main_win.winfo_y() - self._start_y + event.y
        self.main_win.geometry(f"+{x}+{y}")

    # Força a ocultação da barra clássica se a janela for restaurada em segundo plano
    def ao_mapear_janela(self, event):
        self.main_win.update_idletasks()
        self.main_win.overrideredirect(True)

    # Minimiza a janela invisível do Windows (fazendo sumir e ficar guardado na barra de tarefas)
    def minimizar_janela(self):
        self.root.iconify()

    # Fecha completamente todas as janelas do programa e encerra o script do Python
    def fechar_aplicativo(self):
        self.root.destroy()

    # Abre a caixa de diálogo do Windows para o usuário escolher a pasta destino dos downloads
    def escolher_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de destino")
        if pasta:
            self.pasta_destino = pasta
            self.lbl_pasta.configure(text=f"Local de destino: {self.pasta_destino}")

    # Cria um atraso (debounce) após o usuário digitar na URL para não sobrecarregar requisições consecutivas
    def agendar_busca_info(self, event):
        if self.timer_busca:
            self.main_win.after_cancel(self.timer_busca)
        self.timer_busca = self.main_win.after(800, lambda: threading.Thread(target=self.buscar_dados_youtube, daemon=True).start())

    # Conecta à API do YouTube, puxa metadados do vídeo (título e URL da capa) e renderiza na tela
    def buscar_dados_youtube(self):
        url = self.entry_url.get().strip()
        if not url or ("youtube.com" not in url and "youtu.be" not in url):
            return
        try:
            self.progress_bar.start()
            self.lbl_titulo_video.configure(text="Sincronizando dados com o servidor do YouTube...", text_color=COR_VERMELHO_YTB)
            ydl_opts = {
                'skip_download': True,
                'extractor_args': {'youtube': {'player_client': ['web', 'default']}}
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                self.titulo_atual = info.get('title', 'Sem titulo')
                thumbnail_url = info.get('thumbnail')
                self.lbl_titulo_video.configure(text=self.titulo_atual, text_color=COR_TEXTO_PRINCIPAL)
                if thumbnail_url:
                    req = urllib.request.Request(thumbnail_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as u:
                        raw_data = u.read()
                    self.imagem_original_pil = Image.open(BytesIO(raw_data))
                    im_copia = self.imagem_original_pil.copy()
                    im_copia = im_copia.resize((384, 216), Image.Resampling.LANCZOS)
                    self.thumbnail_tk = ImageTk.PhotoImage(im_copia)
                    self.lbl_thumbnail.configure(image=self.thumbnail_tk, text="")
                self.progress_bar.stop()
                self.progress_bar.set(100)
                self.btn_download.configure(state="normal")
                self.btn_download_thumb.configure(state="normal")
        except Exception as e:
            self.progress_bar.stop()
            self.progress_bar.set(0)
            self.lbl_titulo_video.configure(text="Falha de conexao. Verifique o link inserido.", text_color="#FF4444")
            self.lbl_thumbnail.configure(image="", text="")
            self.btn_download.configure(state="disabled")
            self.btn_download_thumb.configure(state="disabled")

    # Salva localmente a imagem bruta da Thumbnail que está guardada na memória RAM como um arquivo JPEG
    def salvar_thumbnail(self):
        if self.imagem_original_pil:
            try:
                nome_valido = "".join([c for c in self.titulo_atual if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                caminho_thumb = os.path.join(self.pasta_destino, f"{nome_valido}_thumbnail.jpg")
                self.imagem_original_pil.convert("RGB").save(caminho_thumb, "JPEG", quality=95)
                messagebox.showinfo("Sucesso", f"Capa em alta definicao exportada!\nSalva em: {nome_valido}_thumbnail.jpg")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possivel exportar a imagem:\n{e}")

    # Cria e inicia uma thread paralela para executar o download do vídeo/áudio sem travar a interface gráfica
    def iniciar_download_thread(self):
        self.btn_download.configure(state="disabled")
        threading.Thread(target=self.executar_download_youtube, daemon=True).start()

    # Passa os parâmetros de configuração selecionados para o yt_dlp e baixa os arquivos de mídia do YouTube
    def executar_download_youtube(self):
        url = self.entry_url.get().strip()
        formato = self.var_formato_dl.get()
        base_opts = {
            'outtmpl': os.path.join(self.pasta_destino, '%(title)s.%(ext)s'),
            'extractor_args': {'youtube': {'player_client': ['web', 'default']}}
        }
        if formato == "mp3":
            base_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192',
                }],
            })
        else:
            base_opts.update({
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            })
        try:
            self.lbl_titulo_video.configure(text="Download ativo... Aguarde a finalizacao dos pacotes.", text_color="#FFBB00")
            self.progress_bar.start()
            with YoutubeDL(base_opts) as ydl:
                ydl.download([url])
            self.progress_bar.stop()
            self.progress_bar.set(100)
            messagebox.showinfo("Sucesso", "Download de midia concluido!")
        except Exception as e:
            self.progress_bar.stop()
            self.progress_bar.set(0)
            messagebox.showerror("Erro", f"Ocorreu um erro no pipeline:\n{e}")
        self.btn_download.configure(state="normal")
        threading.Thread(target=self.buscar_dados_youtube, daemon=True).start()

if __name__ == "__main__":
    root = ctk.CTk()
    app = YoutubeDownloaderPremium(root)
    root.mainloop()