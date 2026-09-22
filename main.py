
import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
from tkinter import ttk
from datetime import datetime, date, timedelta
import threading, time
import queue
import sqlite3
import logging
import database as db
import importar as imp

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Paleta de cores
C_FUNDO    = "#517485"
C_CARD     = "#3f5f6f"
C_SIDEBAR  = "#08364d"
C_BORDA    = "#7fa6b8"
C_BORDA2   = "#3a6f8c"
C_TEXTO    = "#f5f7fa"
C_TEXTO2   = "#e8edf2"
C_AZUL     = "#08364d"
C_CIZ_CLR  = "#b7c3cc"
C_VERDE    = "#2ea043"
C_VERDE_CLR= "#3fb950"
C_VERM     = "#da3633"
C_AMAR     = "#d29922"
C_ROXO     = "#6e40c9"
C_LARJ     = "#e36209"
C_ACENTO   = "#353f4d"

# Cores de linha alternada para tabelas
C_ROW_A    = "#62748d"
C_ROW_B    = "#1c2128"

# Cores sólidas por setor (sem hex-alpha)
C_SETOR = {
    "Picote":           ("#1f6aa5", "#0a1929"),
    "Saco para Lixo":   ("#2ea043", "#0a1f0d"),
    "Sacoleira":        ("#6e40c9", "#13092e"),
    "Corte Solda":      ("#d29922", "#2a1f00"),
    "Fora de Maquina":  ("#e36209", "#2a1200"),
}

SETORES = ["Picote", "Saco para Lixo", "Sacoleira", "Corte Solda"]
TURNOS  = {1: "1\u00ba Turno (06:00\u201315:00)",
            2: "2\u00ba Turno (14:50\u201323:50)",
            3: "3\u00ba Turno (00:00\u201306:00)"}
DIAS    = ["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira",
           "Sexta-feira","Sábado","Domingo"]
HORARIOS = {1:(6,0,15,0), 2:(14,50,23,50), 3:(0,0,6,0)}

usuario_atual = {"id":None,"nome":"","nivel":"operador"}


def turno_atual():
    m = datetime.now().hour*60 + datetime.now().minute
    if 360 <= m < 900: return 1
    if 890 <= m < 1430: return 2
    return 3

def progresso_turno(t):
    m = datetime.now().hour*60 + datetime.now().minute
    ih,im,fh,fm = HORARIOS[t]
    ini,fim = ih*60+im, fh*60+fm
    if t==3: total,dec = 360, (m if m<360 else 0)
    else:    total,dec = fim-ini, max(0,min(fim-ini, m-ini))
    pct = min(max(dec/total,0),1)
    rest = total-dec
    return pct, f"{rest//60:02d}h{rest%60:02d}min restantes"

# TELA DE LOGIN
# **********************************************************************************************
class AplicacaoBase(ctk.CTk):
    def report_callback_exception(self, tipo, erro, traceback):
        logging.error("Erro na interface", exc_info=(tipo, erro, traceback))
        if isinstance(erro, sqlite3.IntegrityError):
            texto = "Não foi possível salvar. Verifique códigos/logins duplicados e os cadastros vinculados."
        elif isinstance(erro, sqlite3.OperationalError):
            texto = "Não foi possível acessar o banco. Verifique se há outra gravação em andamento e tente novamente."
        else:
            texto = str(erro) or "Ocorreu um erro inesperado."
        messagebox.showerror("Não foi possível concluir", texto, parent=self)


class TelaLogin(AplicacaoBase):
    def __init__(self):
        super().__init__()
        db.inicializar_banco()
        self.title("PROGRAMAÇÃO DO ACABAMENTO \u2013 Login")
        self.geometry("460x540"); self.resizable(False,False)
        self.configure(fg_color=C_FUNDO)
        self._build()

    def _build(self):
        card = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=16,
                            border_width=1, border_color=C_BORDA)
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.86)
        ctk.CTkLabel(card, text="\u2699\ufe0f", font=ctk.CTkFont(size=52)).pack(pady=(36,4))
        ctk.CTkLabel(card, text="PROGRAMAÇÃO \n   DO ACABAMENTO",
                     font=ctk.CTkFont(size=24,weight="bold"),text_color=C_TEXTO).pack()
        ctk.CTkLabel(card, text="   ",
                     font=ctk.CTkFont(size=12),text_color=C_TEXTO2).pack(pady=(2,28))
        for lbl,attr,kw in [("Usu\u00e1rio","entry_login",{}),
                             ("Senha","entry_senha",{"show":"\u25cf"})]:
            ctk.CTkLabel(card,text=lbl,anchor="w",
                         font=ctk.CTkFont(size=13),text_color=C_TEXTO2).pack(fill="x",padx=36)
            e=ctk.CTkEntry(card,height=42,font=ctk.CTkFont(size=14),**kw)
            e.pack(fill="x",padx=36,pady=(2,12)); setattr(self,attr,e)
        self.entry_senha.bind("<Return>", lambda e: self._login())
        self.lbl_err = ctk.CTkLabel(card,text="",text_color=C_VERM,
                                    font=ctk.CTkFont(size=12)); self.lbl_err.pack(pady=4)
        ctk.CTkButton(card,text="Entrar",height=44,
                      font=ctk.CTkFont(size=15,weight="bold"),
                      fg_color=C_AZUL,command=self._login).pack(fill="x",padx=36,pady=(4,20))
        ctk.CTkLabel(card,text="Entre com o usuário cadastrado pelo supervisor.",
                     text_color=C_TEXTO2,font=ctk.CTkFont(size=11)).pack(pady=(0,16))

    def _login(self):
        u = db.autenticar(self.entry_login.get().strip(), self.entry_senha.get())
        if u:
            usuario_atual.update(u); self.destroy(); App().mainloop()
        else:
            self.lbl_err.configure(text="Usu\u00e1rio ou senha incorretos.")

# FUNÇÕES AUXILIARES
# ****************************************************************************************
def _ttk_style():
    s = ttk.Style(); s.theme_use("clam")
    s.configure("D.Treeview", background=C_CARD, foreground=C_TEXTO,
        fieldbackground=C_CARD, rowheight=26, font=("Segoe UI",11), borderwidth=0)
    s.configure("D.Treeview.Heading", background="#1c2128", foreground="white",
        font=("Segoe UI",11,"bold"), borderwidth=0, relief="flat")
    s.map("D.Treeview", background=[("selected",C_AZUL)])

def mk_table(parent, cols, heights=None):
    _ttk_style()
    fr = ctk.CTkFrame(parent,fg_color=C_CARD,corner_radius=8,
                      border_width=1,border_color=C_BORDA)
    t  = ttk.Treeview(fr,columns=cols,show="headings",style="D.Treeview")
    sb = ttk.Scrollbar(fr,orient="vertical",command=t.yview)
    t.configure(yscrollcommand=sb.set)
    t.pack(side="left",fill="both",expand=True,padx=(4,0),pady=4)
    sb.pack(side="right",fill="y",pady=4)
    return fr,t

def busca_entry(parent, ph, cb):
    f=ctk.CTkFrame(parent,fg_color="transparent")
    e=ctk.CTkEntry(f,placeholder_text=ph,width=320,font=ctk.CTkFont(size=13),height=36)
    e.pack(side="left",padx=(0,6))
    e.bind("<KeyRelease>", lambda ev: cb(e.get()))
    return f,e

def hdr_tela(parent, icon, title, row=0):
    h=ctk.CTkFrame(parent,fg_color=C_CARD,corner_radius=10,
                   border_width=1,border_color=C_BORDA)
    h.grid(row=row,column=0,padx=16,pady=(16,8),sticky="ew")
    ctk.CTkLabel(h,text=f"{icon}  {title}",
                 font=ctk.CTkFont(size=20,weight="bold")).pack(side="left",padx=20,pady=14)
    return h

def setor_tabela(parent, setor, alocacoes):
    """Bloco de setor com tabela de linhas — sem transparência."""
    cor, bg = C_SETOR.get(setor, (C_AZUL, "#0a1929"))

    card = ctk.CTkFrame(parent, fg_color=bg, corner_radius=10,
                        border_width=2, border_color=cor)
    card.pack(fill="x", pady=5)

    # Cabeçalho do setor
    hdr = ctk.CTkFrame(card, fg_color=cor, corner_radius=0, height=36)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    ctk.CTkLabel(hdr, text=f"  {setor}  \u2014  {len(alocacoes)} m\u00e1quina(s)",
                 font=ctk.CTkFont(size=13, weight="bold"),
                 text_color="white").pack(side="left", padx=10, pady=6)

    if not alocacoes:
        ctk.CTkLabel(card, text="\u2014  Sem aloca\u00e7\u00f5es neste turno",
                     text_color=C_TEXTO2, font=ctk.CTkFont(size=12)).pack(pady=10)
        return card

    # Cabeçalho das colunas
    cols = ("M\u00e1quina","Crach\u00e1","Operador","Produto","Descri\u00e7\u00e3o","N\u00ba OP")
    widths = (90, 80, 200, 90, 340, 80)
    col_hdr = ctk.CTkFrame(card, fg_color=C_CARD, corner_radius=0, height=26)
    col_hdr.pack(fill="x")
    col_hdr.pack_propagate(False)
    for c, w in zip(cols, widths):
        ctk.CTkLabel(col_hdr, text=c, font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=C_TEXTO2, width=w, anchor="w").pack(side="left", padx=(8,0))

    # Linhas de dados
    for idx, a in enumerate(alocacoes):
        row_bg = C_ROW_A if idx % 2 == 0 else C_ROW_B
        r = ctk.CTkFrame(card, fg_color=row_bg, corner_radius=0, height=28)
        r.pack(fill="x")
        r.pack_propagate(False)

        vals = [
            a.get("maquina",""),
            a.get("cracha","") or "",
            a.get("operador","") or "\u2014",
            a.get("produto_cod","") or "",
            (a.get("produto_desc","") or "")[:45],
            a.get("num_op","") or "",
        ]
        for v, w in zip(vals, widths):
            lbl_c = cor if w == widths[0] else C_TEXTO
            ctk.CTkLabel(r, text=str(v), font=ctk.CTkFont(size=11),
                         text_color=lbl_c, width=w, anchor="w").pack(side="left", padx=(8,0))

    return card

def fora_tabela(parent, foras):
    """Bloco Fora de Máquina com tabela."""
    cor, bg = C_SETOR["Fora de Maquina"]
    card = ctk.CTkFrame(parent, fg_color=bg, corner_radius=10,
                        border_width=2, border_color=cor)
    card.pack(fill="x", pady=5)
    hdr = ctk.CTkFrame(card, fg_color=cor, corner_radius=0, height=36)
    hdr.pack(fill="x"); hdr.pack_propagate(False)
    ctk.CTkLabel(hdr, text=f"  Fora de M\u00e1quina  \u2014  {len(foras)} operador(es)",
                 font=ctk.CTkFont(size=13, weight="bold"),
                 text_color="white").pack(side="left", padx=10, pady=6)
    cols = ("Crach\u00e1","Operador","Observa\u00e7\u00e3o")
    widths = (80, 240, 400)
    ch = ctk.CTkFrame(card, fg_color=C_CARD, corner_radius=0, height=26)
    ch.pack(fill="x"); ch.pack_propagate(False)
    for c,w in zip(cols,widths):
        ctk.CTkLabel(ch,text=c,font=ctk.CTkFont(size=10,weight="bold"),
                     text_color=C_TEXTO2,width=w,anchor="w").pack(side="left",padx=(8,0))
    for idx,fm in enumerate(foras):
        rb = C_ROW_A if idx%2==0 else C_ROW_B
        r = ctk.CTkFrame(card,fg_color=rb,corner_radius=0,height=28)
        r.pack(fill="x"); r.pack_propagate(False)
        for v,w in zip([fm.get("cracha","") or "",
                        fm.get("operador","") or "\u2014",
                        fm.get("observacao","") or ""], widths):
            ctk.CTkLabel(r,text=str(v),font=ctk.CTkFont(size=11),
                         text_color=C_TEXTO,width=w,anchor="w").pack(side="left",padx=(8,0))
    return card

# APP PRINCIPAL COM MENU SANDUÍCHE
# *****************************************************************************************************
class App(AplicacaoBase):
    SIDEBAR_FULL = 230
    SIDEBAR_MINI = 52

    def __init__(self):
        super().__init__()
        self.title("PROGRAMAÇÃO ACABAMENTO")
        self.geometry("1380x840"); self.minsize(900,700)
        self._sidebar_open = True
        self._build()
        self._ir("programacoes")

    def _build(self):
        self.grid_columnconfigure(1,weight=1)
        self.grid_rowconfigure(0,weight=1)

        self.sb = ctk.CTkFrame(self,width=self.SIDEBAR_FULL,corner_radius=0,
                               fg_color=C_SIDEBAR,border_width=0)
        self.sb.grid(row=0,column=0,sticky="nsew")
        self.sb.grid_propagate(False)
        self.sb.grid_rowconfigure(20,weight=1)
        self._build_sidebar()

        self.cont = ctk.CTkFrame(self,corner_radius=0,fg_color=C_FUNDO)
        self.cont.grid(row=0,column=1,sticky="nsew")
        self.cont.grid_columnconfigure(0,weight=1)
        self.cont.grid_rowconfigure(0,weight=1)
        self.telas = {}

    def _build_sidebar(self):
        for w in self.sb.winfo_children(): w.destroy()
        full = self._sidebar_open
        eh_sup = usuario_atual["nivel"]=="supervisor"

        # Botão sanduíche
        ctk.CTkButton(self.sb,text="\u2630" if full else "\u2630",
                      width=40,height=40,corner_radius=6,
                      fg_color="transparent",hover_color=C_BORDA2,
                      font=ctk.CTkFont(size=20),
                      command=self._toggle_sidebar).grid(
            row=1,column=0,padx=(8,0),pady=(12,8),sticky="w")

        if full:
            # Logo
            logo=ctk.CTkFrame(self.sb,fg_color="transparent")
            logo.grid(row=0,column=0,sticky="ew",padx=8)
            logo.grid_columnconfigure(1,weight=1)
            ctk.CTkLabel(logo,text="\u2699\ufe0f",font=ctk.CTkFont(size=24)).grid(row=0,column=0,padx=(40,4))
            ctk.CTkLabel(logo,text="PROGRAMAÇÃO\n ACABAMENTO",
                         font=ctk.CTkFont(size=13,weight="bold"),
                         text_color=C_TEXTO,anchor="w").grid(row=0,column=1,sticky="w")

        ctk.CTkFrame(self.sb,height=1,fg_color=C_BORDA).grid(
            row=2,column=0,sticky="ew",padx=8,pady=(0,6))

        nav=[
            ("\U0001f4cb","Programa\u00e7\u00f5es","programacoes",True),
            ("\U0001f441","Vis\u00e3o Geral","visao_geral",True),
            ("\U0001f4fa","Turno Atual","turno_atual",True),
            ("\U0001f477","Operadores","operadores",True),
            ("\U0001f4e6","Produtos","produtos",True),
            ("\U0001f3ed","M\u00e1quinas","maquinas",True),
            ("\U0001f464","Usu\u00e1rios","usuarios",eh_sup),
            ("\U0001f4e5","Importar XLS","importar",eh_sup),
        ]
        r=2
        for icon,label,tela,vis in nav:
            if not vis: continue
            txt = f"{icon}  {label}" if full else icon
            ctk.CTkButton(self.sb,text=txt,anchor="w" if full else "center",
                          fg_color="transparent",hover_color=C_BORDA2,
                          font=ctk.CTkFont(size=13),height=40,
                          command=lambda t=tela:self._ir(t)).grid(
                row=r,column=0,padx=6,pady=2,sticky="ew"); r+=1

        ctk.CTkFrame(self.sb,height=1,fg_color=C_BORDA).grid(
            row=21,column=0,sticky="ew",padx=8,pady=6)

        if full:
            icon_nv="\U0001f6e1\ufe0f" if eh_sup else "\U0001f464"
            ctk.CTkLabel(self.sb,text=f"{icon_nv} {usuario_atual['nome']}",
                         font=ctk.CTkFont(size=11),text_color=C_TEXTO2).grid(
                row=22,column=0,padx=12,pady=(0,2))
            ctk.CTkLabel(self.sb,text=usuario_atual["nivel"].capitalize(),
                         font=ctk.CTkFont(size=10),text_color=C_TEXTO2).grid(
                row=23,column=0,padx=12)
        ctk.CTkButton(self.sb,text="Sair" if full else "\u21a9",
                      height=32,fg_color=C_VERM,font=ctk.CTkFont(size=12),
                      command=self._sair).grid(
            row=24,column=0,padx=10,pady=(6,14),sticky="ew")

    def _toggle_sidebar(self):
        self._sidebar_open = not self._sidebar_open
        w = self.SIDEBAR_FULL if self._sidebar_open else self.SIDEBAR_MINI
        self.sb.configure(width=w)
        self._build_sidebar()

    def _sair(self):
        self.destroy(); TelaLogin().mainloop()

    def _ir(self, nome):
        for t in self.telas.values(): t.grid_remove()
        eh_sup = usuario_atual["nivel"]=="supervisor"
        mapa={
            "programacoes":TelaProgramacoes,"visao_geral":TelaVisaoGeral,
            "turno_atual":TelaTurnoAtual,"operadores":TelaOperadores,
            "produtos":TelaProdutos,"maquinas":TelaMaquinas,
            "usuarios":TelaUsuarios if eh_sup else None,
            "importar":TelaImportar if eh_sup else None,
        }
        cls=mapa.get(nome)
        if cls is None: messagebox.showwarning("Permiss\u00e3o","Acesso restrito."); return
        if nome not in self.telas:
            self.telas[nome]=cls(self.cont,supervisor=eh_sup)
            self.telas[nome].grid(row=0,column=0,sticky="nsew")
        else:
            self.telas[nome].grid()
            self.telas[nome].atualizar()

# TELA – VISÃO GERAL
# *******************************************************************************************
class TelaVisaoGeral(ctk.CTkFrame):
    def __init__(self,master,supervisor=True):
        super().__init__(master,fg_color=C_FUNDO,corner_radius=0)
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(1,weight=1)
        self.data_atual=date.today()
        self._build()

    def _build(self):
        hdr=ctk.CTkFrame(self,fg_color=C_CARD,corner_radius=10,
                         border_width=1,border_color=C_BORDA)
        hdr.grid(row=0,column=0,padx=16,pady=(16,8),sticky="ew")
        ctk.CTkLabel(hdr,text="\U0001f441\ufe0f  Vis\u00e3o Geral \u2014 Todos os Turnos",
                     font=ctk.CTkFont(size=20,weight="bold")).pack(side="left",padx=20,pady=14)
        nf=ctk.CTkFrame(hdr,fg_color="transparent"); nf.pack(side="right",padx=16,pady=8)
        ctk.CTkButton(nf,text="\u25c4",width=34,command=self._ant).pack(side="left")
        self.lbl_d=ctk.CTkLabel(nf,text="",font=ctk.CTkFont(size=14,weight="bold"),
                                width=130,anchor="center"); self.lbl_d.pack(side="left",padx=8)
        ctk.CTkButton(nf,text="\u25ba",width=34,command=self._prox).pack(side="left")
        ctk.CTkButton(nf,text="Hoje",width=60,fg_color="#1c2128",
                      command=self._hoje).pack(side="left",padx=(8,0))

        self.scroll=ctk.CTkScrollableFrame(self,fg_color=C_FUNDO,corner_radius=0)
        self.scroll.grid(row=1,column=0,padx=12,pady=(0,12),sticky="nsew")
        self.scroll.grid_columnconfigure((0,1,2),weight=1)
        self.atualizar()

    def _hoje(self): self.data_atual=date.today(); self.atualizar()
    def _ant(self):  self.data_atual-=timedelta(days=1); self.atualizar()
    def _prox(self): self.data_atual+=timedelta(days=1); self.atualizar()

    def atualizar(self):
        for w in self.scroll.winfo_children(): w.destroy()
        ds=self.data_atual.strftime("%Y-%m-%d")
        self.lbl_d.configure(text=self.data_atual.strftime("%d/%m/%Y"))
        dados=db.alocacoes_por_data(ds)
        tn=turno_atual()

        for col,t in enumerate([1,2,3]):
            eh=(t==tn and self.data_atual==date.today())
            cor_b=C_CIZ_CLR if eh else C_BORDA
            tc=ctk.CTkFrame(self.scroll,fg_color=C_CARD,corner_radius=12,
                            border_width=2,border_color=cor_b)
            tc.grid(row=0,column=col,padx=6,pady=4,sticky="nsew")
            tc.grid_columnconfigure(0,weight=1)

            hbg=C_AZUL if eh else "#1c2128"
            th=ctk.CTkFrame(tc,fg_color=hbg,corner_radius=0,height=46)
            th.pack(fill="x"); th.pack_propagate(False)
            badge=" \U0001f534 ATIVO" if eh else ""
            ctk.CTkLabel(th,text=f"  {t}\u00ba Turno{badge}",
                         font=ctk.CTkFont(size=14,weight="bold"),
                         text_color="white").pack(side="left",padx=12,pady=8)
            inf=TURNOS[t].split("(")[1].rstrip(")")
            ctk.CTkLabel(th,text=inf,font=ctk.CTkFont(size=11),
                         text_color="#aad4ff").pack(side="right",padx=12)

            corpo=ctk.CTkFrame(tc,fg_color="transparent")
            corpo.pack(fill="both",padx=8,pady=8)

            info=dados.get(t)
            if not info:
                ctk.CTkLabel(corpo,text="Sem programa\u00e7\u00e3o",
                             text_color=C_TEXTO2,font=ctk.CTkFont(size=12)).pack(pady=20)
                continue

            alocs=info["alocacoes"]
            foras=info["fora_maquina"]

            for setor in SETORES:
                sl=[a for a in alocs if a["setor"]==setor]
                self._mini_setor(corpo, setor, sl)
            if foras:
                self._mini_fora(corpo, foras)

    def _mini_setor(self, parent, setor, alocs):
        cor, bg = C_SETOR.get(setor,(C_AZUL,"#0a1929"))
        c=ctk.CTkFrame(parent,fg_color=bg,corner_radius=8,
                       border_width=1,border_color=cor)
        c.pack(fill="x",pady=3)
        h=ctk.CTkFrame(c,fg_color=cor,corner_radius=0,height=24)
        h.pack(fill="x"); h.pack_propagate(False)
        ctk.CTkLabel(h,text=f"  {setor} ({len(alocs)})",
                     font=ctk.CTkFont(size=11,weight="bold"),
                     text_color="white").pack(side="left",padx=6,pady=3)
        if not alocs:
            ctk.CTkLabel(c,text="Sem aloca\u00e7\u00f5es",
                         text_color=C_TEXTO2,font=ctk.CTkFont(size=10)).pack(pady=4); return
        for a in alocs:
            r=ctk.CTkFrame(c,fg_color="transparent")
            r.pack(fill="x",padx=6,pady=1)
            ctk.CTkLabel(r,text=a["maquina"],font=ctk.CTkFont(size=10,weight="bold"),
                         text_color=cor,width=62,anchor="w").pack(side="left")
            ctk.CTkLabel(r,text=(a.get("operador") or "\u2014")[:24],
                         font=ctk.CTkFont(size=10),text_color=C_TEXTO).pack(side="left",padx=4)

    def _mini_fora(self, parent, foras):
        cor, bg = C_SETOR["Fora de Maquina"]
        c=ctk.CTkFrame(parent,fg_color=bg,corner_radius=8,
                       border_width=1,border_color=cor)
        c.pack(fill="x",pady=3)
        h=ctk.CTkFrame(c,fg_color=cor,corner_radius=0,height=24)
        h.pack(fill="x"); h.pack_propagate(False)
        ctk.CTkLabel(h,text=f"  Fora de M\u00e1quina ({len(foras)})",
                     font=ctk.CTkFont(size=11,weight="bold"),
                     text_color="white").pack(side="left",padx=6,pady=3)
        for fm in foras:
            r=ctk.CTkFrame(c,fg_color="transparent")
            r.pack(fill="x",padx=6,pady=1)
            ctk.CTkLabel(r,text=f"\u2022 {(fm.get('operador') or '\u2014')[:28]}",
                         font=ctk.CTkFont(size=10),text_color=C_TEXTO).pack(side="left")

# TELA – TURNO ATUAL (tabela por seção, barra de progresso)
# ***************************************************************************************************
class TelaTurnoAtual(ctk.CTkFrame):

    COLS_ALOC  = ("Máquina","Crachá","Operador","Produto","Descrição","Nº OP")
    COLS_W     = (80, 72, 190, 80, 280, 72)
    COLS_FORA  = ("Crachá","Operador","Observação")
    COLS_FW    = (80, 220, 500)

    def __init__(self, master, supervisor=True):
        super().__init__(master, fg_color=C_FUNDO, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._tv = None
        self._rodando = True
        self._panels = {}          # setor → Treeview
        self._build()
        self._tick()

    # ── layout estático ──────────────────────────────────────
    def _build(self):
        # ── Barra de topo ────────────────────────────────────
        self.hdr = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=0, height=110)
        self.hdr.grid(row=0, column=0, sticky="ew")
        self.hdr.grid_propagate(False)
        self.hdr.grid_columnconfigure(1, weight=1)

        self.lbl_gear = ctk.CTkLabel(self.hdr, text="⚙️", font=ctk.CTkFont(size=44))
        self.lbl_gear.grid(row=0, column=0, rowspan=2, padx=20, pady=8)

        self.lbl_turno = ctk.CTkLabel(self.hdr, text="",
                                      font=ctk.CTkFont(size=22, weight="bold"), anchor="w")
        self.lbl_turno.grid(row=0, column=1, sticky="w", padx=8, pady=(14, 0))

        self.lbl_jornada = ctk.CTkLabel(self.hdr, text="",
                                        font=ctk.CTkFont(size=13), text_color=C_TEXTO2, anchor="w")
        self.lbl_jornada.grid(row=1, column=1, sticky="w", padx=8)

        self.lbl_rel = ctk.CTkLabel(self.hdr, text="",
                                    font=ctk.CTkFont(size=34, weight="bold"),
                                    text_color=C_CIZ_CLR, anchor="e")
        self.lbl_rel.grid(row=0, column=2, padx=24, pady=(14, 0), sticky="e")

        self.lbl_dt = ctk.CTkLabel(self.hdr, text="",
                                   font=ctk.CTkFont(size=11), text_color=C_TEXTO2, anchor="e")
        self.lbl_dt.grid(row=1, column=2, padx=24, sticky="e")

        pf = ctk.CTkFrame(self.hdr, fg_color="transparent")
        pf.grid(row=2, column=0, columnspan=3, padx=16, pady=(4, 10), sticky="ew")
        self.lbl_pct = ctk.CTkLabel(pf, text="", font=ctk.CTkFont(size=11),
                                    text_color=C_TEXTO2, anchor="w")
        self.lbl_pct.pack(side="left", padx=(4, 10))
        self.prog = ctk.CTkProgressBar(pf, height=16, corner_radius=6,
                                       progress_color=C_VERDE_CLR, fg_color="#1c2128")
        self.prog.pack(side="left", fill="x", expand=True)
        self.prog.set(0)
        self.lbl_rest = ctk.CTkLabel(pf, text="", font=ctk.CTkFont(size=11, weight="bold"),
                                     text_color=C_VERDE_CLR, width=160, anchor="e")
        self.lbl_rest.pack(side="left", padx=(10, 4))

        # ── Grade de painéis ─────────────────────────────────
        self.grade = ctk.CTkFrame(self, fg_color=C_FUNDO, corner_radius=0)
        self.grade.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.grade.grid_columnconfigure(0, weight=1)
        self.grade.grid_columnconfigure(1, weight=1)
        self.grade.grid_rowconfigure(0, weight=4)   # Picote / Saco (maiores)
        self.grade.grid_rowconfigure(1, weight=3)   # Sacoleira / Corte Solda
        self.grade.grid_rowconfigure(2, weight=0,minsize=80)   # Fora de Máquina

        posicoes = [
            ("Picote",         0, 0, 1),
            ("Saco para Lixo", 0, 1, 1),
            ("Sacoleira",      1, 0, 1),
            ("Corte Solda",    1, 1, 1),
        ]
        for setor, row, col, colspan in posicoes:
            tree = self._painel(self.grade, setor, row, col, colspan)
            self._panels[setor] = tree

        # Fora de Máquina — linha 2, largura toda
        tree_fora = self._painel_fora(self.grade, row=2)
        self._panels["Fora de Máquina"] = tree_fora

        # Label de "sem programação" (oculto por padrão)
        self.lbl_vazio = ctk.CTkLabel(self.grade, text="",
                                      font=ctk.CTkFont(size=16), text_color=C_TEXTO2)

    def _painel(self, parent, setor, row, col, colspan):
        """Cria card de setor com Treeview + scrollbar interno."""
        cor, bg = C_SETOR.get(setor, (C_AZUL, "#0a1929"))

        card = ctk.CTkFrame(parent, fg_color=bg, corner_radius=10,
                            border_width=2, border_color=cor)
        card.grid(row=row, column=col, columnspan=colspan,
                  padx=5, pady=5, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        # Cabeçalho colorido
        hdr = ctk.CTkFrame(card, fg_color=cor, corner_radius=0, height=34)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)
        self._lbl_count = {}   # guardamos ref por setor
        lbl = ctk.CTkLabel(hdr, text=f"  {setor}",
                           font=ctk.CTkFont(size=13, weight="bold"), text_color="white")
        lbl.grid(row=0, column=0, sticky="w", padx=10, pady=6)
        # badge de contagem
        badge = ctk.CTkLabel(hdr, text="0 máq.",
                             font=ctk.CTkFont(size=11), text_color="#cce4ff")
        badge.grid(row=0, column=1, sticky="e", padx=10)
        card._badge = badge   # armazenamos no próprio frame

        # Treeview com scrollbar
        _ttk_style()
        cols = self.COLS_ALOC
        style_name = f"S{setor[:3].replace(' ','')}.Treeview"
        s = ttk.Style()
        s.configure(style_name, background=bg, foreground=C_TEXTO,
                    fieldbackground=bg, rowheight=24,
                    font=("Segoe UI", 10), borderwidth=0)
        s.configure(f"{style_name}.Heading",
                    background="#1c2128", foreground="white",
                    font=("Segoe UI", 10, "bold"), borderwidth=0, relief="flat")
        s.map(style_name, background=[("selected", cor)])

        # Alternating row tags
        tree = ttk.Treeview(card, columns=cols, show="headings", style=style_name)
        vsb  = ttk.Scrollbar(card, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.tag_configure("odd",  background=bg)
        tree.tag_configure("even", background=C_ROW_B)

        for c, w in zip(cols, self.COLS_W):
            tree.heading(c, text=c)
            anch = "center" if c in ("Máquina","Crachá","Nº OP") else "w"
            tree.column(c, width=w, minwidth=w, anchor=anch, stretch=(c == "Descrição"))

        tree.grid(row=1, column=0, sticky="nsew", padx=(4, 0), pady=(0, 4))
        vsb.grid(row=1, column=1, sticky="ns", pady=(0, 4))

        card._tree = tree
        return tree

    def _painel_fora(self, parent, row):
        """Painel Fora de Máquina — largura total, altura menor."""
        cor, bg = C_SETOR["Fora de Maquina"]
        card = ctk.CTkFrame(parent, fg_color=bg, corner_radius=10,
                            border_width=2, border_color=cor)
        card.grid(row=row, column=0, columnspan=2,
                  padx=5, pady=5, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(card, fg_color=cor, corner_radius=0, height=34)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=100)
        ctk.CTkLabel(hdr, text="  Fora de Máquina",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="white").grid(row=0, column=0, sticky="w", padx=10, pady=6)
        badge = ctk.CTkLabel(hdr, text="0 op.", font=ctk.CTkFont(size=11), text_color="#ffe0c0")
        badge.grid(row=0, column=1, sticky="e", padx=10)
        card._badge = badge

        _ttk_style()
        style_name = "Fora.Treeview"
        s = ttk.Style()
        s.configure(style_name, background=bg, foreground=C_TEXTO,
                    fieldbackground=bg, rowheight=24,
                    font=("Segoe UI", 10), borderwidth=0)
        s.configure(f"{style_name}.Heading",
                    background="#1c2128", foreground="white",
                    font=("Segoe UI", 10, "bold"), borderwidth=0, relief="flat")
        s.map(style_name, background=[("selected", cor)])

        tree = ttk.Treeview(card, columns=self.COLS_FORA, show="headings", style=style_name)
        vsb  = ttk.Scrollbar(card, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set,height=2)
        tree.tag_configure("odd",  background=bg)
        tree.tag_configure("even", background=C_ROW_B)

        for c, w in zip(self.COLS_FORA, self.COLS_FW):
            tree.heading(c, text=c)
            tree.column(c, width=w, minwidth=w, anchor="w", stretch=(c == "Observação"))

        tree.grid(row=1, column=0, sticky="nsew", padx=(4, 0), pady=(0, 4))
        vsb.grid(row=1, column=1, sticky="ns", pady=(0, 4))

        card._tree = tree
        return tree

    # ── tick: atualiza relógio e progresso a cada 1s ─────────
    def _tick(self):
        if not self._rodando:
            return
        agora = datetime.now()
        tn    = turno_atual()
        pct, rest = progresso_turno(tn)

        self.lbl_rel.configure(text=agora.strftime("%H:%M:%S"))
        self.lbl_dt.configure(text=agora.strftime("%A, %d/%m/%Y"))
        self.lbl_turno.configure(text=f"{tn}º Turno — Em andamento")
        self.lbl_jornada.configure(text="Jornada: " + TURNOS[tn].split("(")[1].rstrip(")"))
        self.prog.set(pct)
        self.lbl_pct.configure(text=f"{pct*100:.1f}% concluído")
        self.lbl_rest.configure(text=rest)

        if pct >= 0.9:   self.prog.configure(progress_color=C_VERM)
        elif pct >= 0.7: self.prog.configure(progress_color=C_AMAR)
        else:            self.prog.configure(progress_color=C_VERDE_CLR)

        gears = ["⚙️","🔧","⚙️","🔩"]
        self.lbl_gear.configure(text=gears[int(time.time()) % len(gears)])

        # Troca de turno → recarrega dados
        if (tn, agora.date()) != self._tv:
            self._tv = (tn, agora.date())
            self._carregar(tn)

        self._tick_job = self.after(1000, self._tick)

    # ── carrega dados nos painéis ─────────────────────────────
    def _carregar(self, tn):
        ds    = date.today().strftime("%Y-%m-%d")
        dados = db.alocacoes_por_data(ds)
        info  = dados.get(tn)

        # Limpar todos os trees
        for tree in self._panels.values():
            tree.delete(*tree.get_children())

        # Atualizar badges para 0
        for setor in SETORES + ["Fora de Máquina"]:
            card = self._card_de(setor)
            if card and hasattr(card, "_badge"):
                card._badge.configure(text="sem dados")

        if not info:
            self.lbl_vazio.configure(
                text=f"Sem programação cadastrada para o {tn}º Turno hoje.\nData: {ds}")
            self.lbl_vazio.grid(row=0, column=0, columnspan=2, pady=40)
            return

        self.lbl_vazio.grid_remove()

        alocs = info["alocacoes"]
        foras = info["fora_maquina"]

        # Preencher painéis de setor
        for setor in SETORES:
            tree = self._panels.get(setor)
            if not tree:
                continue
            sl = [a for a in alocs if a["setor"] == setor]
            for idx, a in enumerate(sl):
                tag = "odd" if idx % 2 == 0 else "even"
                tree.insert("", "end", tags=(tag,), values=(
                    a.get("maquina") or "",
                    a.get("cracha")  or "",
                    a.get("operador") or "—",
                    a.get("produto_cod") or "",
                    (a.get("produto_desc") or "")[:55],
                    a.get("num_op") or "",
                ))
            # Atualizar badge
            card = self._card_de(setor)
            if card:
                card._badge.configure(text=f"{len(sl)} máq.")

        # Preencher Fora de Máquina
        tree_f = self._panels.get("Fora de Máquina")
        if tree_f:
            for idx, fm in enumerate(foras):
                tag = "odd" if idx % 2 == 0 else "even"
                tree_f.insert("", "end", tags=(tag,), values=(
                    fm.get("cracha") or "",
                    fm.get("operador") or "—",
                    fm.get("observacao") or "",
                ))
            card_f = self._card_de("Fora de Máquina")
            if card_f:
                card_f._badge.configure(text=f"{len(foras)} op.")

    def _card_de(self, setor):
        """Retorna o frame card que contém a tree do setor."""
        tree = self._panels.get(setor)
        if not tree:
            return None
        return tree.master   # tree.master é o card CTkFrame

    def atualizar(self):
        self._tv = None

    def destroy(self):
        self._rodando = False
        if getattr(self, "_tick_job", None):
            self.after_cancel(self._tick_job)
        super().destroy()

# TELA – PROGRAMAÇÕES
# *******************************************************************************
class TelaProgramacoes(ctk.CTkFrame):
    def __init__(self, master, supervisor=True):
        super().__init__(master, fg_color=C_FUNDO, corner_radius=0)
        self.supervisor = supervisor
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()

    def _build(self):
        hdr = hdr_tela(self, "📋", "Programações")
        if self.supervisor:
            ctk.CTkButton(hdr, text="+ Nova Programação", fg_color=C_VERDE,
                          command=self._nova).pack(side="right", padx=16, pady=8)

        # Barra de busca/filtro
        filtro_f = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=8,
                                border_width=1, border_color=C_BORDA)
        filtro_f.grid(row=1, column=0, padx=16, pady=(0, 6), sticky="ew")

        ctk.CTkLabel(filtro_f, text="Filtrar:", font=ctk.CTkFont(size=12),
                     text_color=C_TEXTO2).pack(side="left", padx=(12, 4), pady=8)
        self.e_busca = ctk.CTkEntry(filtro_f, placeholder_text="Data, dia ou turno...",
                                    width=260, height=32)
        self.e_busca.pack(side="left", padx=4, pady=8)
        self.e_busca.bind("<KeyRelease>", lambda e: self.atualizar())

        ctk.CTkLabel(filtro_f, text="Dia:", font=ctk.CTkFont(size=12),
                     text_color=C_TEXTO2).pack(side="left", padx=(16, 4))
        self.combo_filtro_dia = ctk.CTkComboBox(
            filtro_f, values=["Todos"] + DIAS, width=160, height=32,
            command=lambda _: self.atualizar())
        self.combo_filtro_dia.set("Todos")
        self.combo_filtro_dia.pack(side="left", padx=4, pady=8)

        ctk.CTkLabel(filtro_f, text="Turno:", font=ctk.CTkFont(size=12),
                     text_color=C_TEXTO2).pack(side="left", padx=(12, 4))
        self.combo_filtro_turno = ctk.CTkComboBox(
            filtro_f, values=["Todos"] + list(TURNOS.values()), width=220, height=32,
            command=lambda _: self.atualizar())
        self.combo_filtro_turno.set("Todos")
        self.combo_filtro_turno.pack(side="left", padx=4, pady=8)

        ctk.CTkButton(filtro_f, text="✕ Limpar", width=80, height=32,
                      fg_color="#1c2128", hover_color=C_BORDA,
                      command=self._limpar_filtro).pack(side="left", padx=8)

        # Tabela principal
        cols = ("Data", "Dia", "Turno", "Alocações", "Fora de Máq.")
        tf, self.t = mk_table(self, cols)
        tf.grid(row=2, column=0, padx=16, pady=(0, 4), sticky="nsew")
        self.grid_rowconfigure(2, weight=1)

        for c, w in zip(cols, [110, 140, 240, 100, 110]):
            self.t.heading(c, text=c)
            self.t.column(c, width=w, anchor="center")
        self.t.bind("<Double-1>", self._abrir)

        # Barra de ações
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=3, column=0, padx=16, pady=(0, 16), sticky="ew")

        ctk.CTkButton(bar, text="📂  Abrir / Editar Alocações",
                      command=self._abrir_btn).pack(side="left", padx=4)
        if self.supervisor:
            ctk.CTkButton(bar, text="✏️  Editar Data/Turno", fg_color=C_AZUL,
                          command=self._editar_meta).pack(side="left", padx=4)
            ctk.CTkButton(bar, text="🗑️  Excluir", fg_color=C_VERM,
                          command=self._excluir).pack(side="left", padx=4)

        # Rodapé com contagem
        self.lbl_count = ctk.CTkLabel(bar, text="", text_color=C_TEXTO2,
                                      font=ctk.CTkFont(size=11))
        self.lbl_count.pack(side="right", padx=8)

        self.atualizar()

    def _limpar_filtro(self):
        self.e_busca.delete(0, "end")
        self.combo_filtro_dia.set("Todos")
        self.combo_filtro_turno.set("Todos")
        self.atualizar()

    def atualizar(self):
        self.t.delete(*self.t.get_children())
        txt   = self.e_busca.get().lower() if hasattr(self, "e_busca") else ""
        fdia  = self.combo_filtro_dia.get()  if hasattr(self, "combo_filtro_dia") else "Todos"
        fturno= self.combo_filtro_turno.get() if hasattr(self, "combo_filtro_turno") else "Todos"

        total = 0
        for p in db.listar_programacoes():
            turno_txt = TURNOS.get(p["turno"], "")
            # Filtros
            if txt and txt not in p["data"] and txt not in p["dia_semana"].lower() and txt not in turno_txt.lower():
                continue
            if fdia != "Todos" and p["dia_semana"] != fdia:
                continue
            if fturno != "Todos" and turno_txt != fturno:
                continue

            n_aloc = len(db.listar_alocacoes(p["id"]))
            n_fora = len(db.listar_fora_maquina(p["id"]))
            self.t.insert("", "end", iid=str(p["id"]),
                          values=(p["data"], p["dia_semana"], turno_txt,
                                  n_aloc, n_fora if n_fora else "—"))
            total += 1

        if hasattr(self, "lbl_count"):
            self.lbl_count.configure(text=f"{total} programação(ões)")

    def _nova(self):
        DlgEditProg(self, callback=self.atualizar)

    def _abrir_btn(self):
        s = self.t.selection()
        if not s:
            messagebox.showinfo("Aviso", "Selecione uma programação.")
            return
        self._abre(int(s[0]))

    def _abrir(self, e=None):
        s = self.t.selection()
        if s: self._abre(int(s[0]))

    def _abre(self, pid):
        conn = db.get_conn()
        p = conn.execute("SELECT * FROM programacoes WHERE id=?", (pid,)).fetchone()
        conn.close()
        if p:
            JanelaEdicao(self, dict(p), supervisor=self.supervisor, callback=self.atualizar)

    def _editar_meta(self):
        s = self.t.selection()
        if not s:
            messagebox.showinfo("Aviso", "Selecione uma programação.")
            return
        conn = db.get_conn()
        p = conn.execute("SELECT * FROM programacoes WHERE id=?", (int(s[0]),)).fetchone()
        conn.close()
        if p:
            DlgEditProg(self, programacao=dict(p), callback=self.atualizar)

    def _excluir(self):
        s = self.t.selection()
        if not s:
            return
        n_aloc = len(db.listar_alocacoes(int(s[0])))
        msg = f"Excluir esta programação e suas {n_aloc} alocação(ões)?"
        if messagebox.askyesno("Confirmar exclusão", msg):
            db.deletar_programacao(int(s[0]))
            self.atualizar()


class DlgEditProg(ctk.CTkToplevel):
    """Dialog unificado para criar E editar programação (data, dia, turno)."""
    def __init__(self, master, programacao=None, callback=None):
        super().__init__(master)
        self.prog = programacao   # None = novo
        self.cb   = callback
        titulo = "Editar Programação" if programacao else "Nova Programação"
        self.title(titulo)
        self.geometry("480x360")
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        # Cabeçalho
        hdr = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=0, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        titulo = "✏️  Editar Programação" if self.prog else "➕  Nova Programação"
        ctk.CTkLabel(hdr, text=titulo,
                     font=ctk.CTkFont(size=16, weight="bold")).pack(padx=20, pady=12)

        # Formulário
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=32, pady=16)
        f.grid_columnconfigure(1, weight=1)

        def row(lbl, widget, r, dica=""):
            ctk.CTkLabel(f, text=lbl, font=ctk.CTkFont(size=13),
                         anchor="w").grid(row=r, column=0, sticky="w", pady=8, padx=(0, 12))
            widget.grid(row=r, column=1, sticky="ew", pady=8)
            if dica:
                ctk.CTkLabel(f, text=dica, font=ctk.CTkFont(size=10),
                             text_color=C_TEXTO2).grid(row=r, column=2, padx=(8, 0))

        # Data com calendário rápido (navegação de dias)
        data_f = ctk.CTkFrame(f, fg_color="transparent")
        self.e_data = ctk.CTkEntry(data_f, width=160, font=ctk.CTkFont(size=13),
                                   placeholder_text="AAAA-MM-DD")
        self.e_data.pack(side="left")
        ctk.CTkButton(data_f, text="◀", width=30, height=30,
                      command=lambda: self._ajustar_data(-1)).pack(side="left", padx=(6, 2))
        ctk.CTkButton(data_f, text="▶", width=30, height=30,
                      command=lambda: self._ajustar_data(1)).pack(side="left", padx=2)
        ctk.CTkButton(data_f, text="Hoje", width=54, height=30,
                      fg_color="#1c2128",
                      command=lambda: self._set_data(date.today())).pack(side="left", padx=(6, 0))
        row("Data:", data_f, 0)

        # Dia da semana — atualiza automaticamente ao sair do campo data
        self.combo_dia = ctk.CTkComboBox(f, values=DIAS, width=240,
                                         font=ctk.CTkFont(size=13), state="disabled")
        row("Dia da semana:", self.combo_dia, 1)
        self.e_data.bind("<FocusOut>", self._autodetectar_dia)
        self.e_data.bind("<Return>",   self._autodetectar_dia)

        # Turno
        self.combo_turno = ctk.CTkComboBox(f, values=list(TURNOS.values()),
                                            width=240, font=ctk.CTkFont(size=13))
        row("Turno:", self.combo_turno, 2)

        # Preencher valores iniciais
        if self.prog:
            self.e_data.insert(0, self.prog["data"])
            self.combo_dia.set(self.prog["dia_semana"])
            self.combo_turno.set(TURNOS.get(self.prog["turno"], ""))
        else:
            hoje = date.today()
            self._set_data(hoje)
            self.combo_turno.set(list(TURNOS.values())[0])

        # Info de conflito
        self.lbl_info = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11),
                                     text_color=C_AMAR)
        self.lbl_info.pack(pady=(0, 4))

        # Botões
        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(pady=(4, 24))
        lbl_btn = "💾  Salvar Alterações" if self.prog else "✅  Criar Programação"
        ctk.CTkButton(btn_f, text=lbl_btn, fg_color=C_VERDE, width=200,
                      height=40, font=ctk.CTkFont(size=14),
                      command=self._salvar).pack(side="left", padx=6)
        ctk.CTkButton(btn_f, text="Cancelar", fg_color="#1c2128", width=100,
                      height=40, command=self.destroy).pack(side="left", padx=6)

    def _set_data(self, d):
        self.e_data.delete(0, "end")
        self.e_data.insert(0, d.strftime("%Y-%m-%d"))
        self._autodetectar_dia()

    def _ajustar_data(self, delta):
        try:
            d = datetime.strptime(self.e_data.get().strip(), "%Y-%m-%d").date()
            self._set_data(d + timedelta(days=delta))
        except ValueError:
            pass

    def _autodetectar_dia(self, event=None):
        """Detecta automaticamente o dia da semana a partir da data digitada."""
        try:
            d = datetime.strptime(self.e_data.get().strip(), "%Y-%m-%d").date()
            nomes = ["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira",
                     "Sexta-feira","Sábado","Domingo"]
            self.combo_dia.set(nomes[d.weekday()])
        except ValueError:
            pass

    def _salvar(self):
        data = self.e_data.get().strip()
        try:
            datetime.strptime(data, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Erro", "Data inválida. Use o formato AAAA-MM-DD.")
            return

        tn_txt = self.combo_turno.get()
        tn_num = next((k for k, v in TURNOS.items() if v == tn_txt), None)
        if not tn_num:
            messagebox.showerror("Erro", "Selecione um turno válido.")
            return

        dia = self.combo_dia.get()

        if self.prog:
            # Verificar conflito somente se data/turno mudou
            mudou = (data != self.prog["data"] or tn_num != self.prog["turno"])
            if mudou:
                existe = db.buscar_programacao(data, tn_num)
                if existe and existe["id"] != self.prog["id"]:
                    self.lbl_info.configure(
                        text=f"⚠️  Já existe programação para {data} – {tn_txt}")
                    return
            db.atualizar_programacao(self.prog["id"], data, tn_num, dia)
        else:
            if db.buscar_programacao(data, tn_num):
                self.lbl_info.configure(
                    text=f"⚠️  Já existe programação para {data} – {tn_txt}")
                return
            db.criar_programacao(data, tn_num, dia)

        if self.cb:
            self.cb()
        self.destroy()


class JanelaEdicao(ctk.CTkToplevel):
    def __init__(self, master, prog, supervisor=True, callback=None):
        super().__init__(master)
        self.prog = prog
        self.sup  = supervisor
        self.cb   = callback
        self._atualizar_titulo()
        self.geometry("1200x780")
        self.grab_set()
        self._build()
        self._load()

    def _atualizar_titulo(self):
        self.title(
            f"Alocações — {self.prog['data']}  |  "
            f"{self.prog['dia_semana']}  |  "
            f"{TURNOS.get(self.prog['turno'], '')}"
        )

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Cabeçalho ────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=0,
                           border_width=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)

        # Bloco de identidade da programação (clicável para editar)
        info_f = ctk.CTkFrame(hdr, fg_color=C_ACENTO if not hasattr(self, "_dummy") else C_CARD,
                               corner_radius=8, border_width=1, border_color=C_BORDA)
        info_f.grid(row=0, column=0, padx=12, pady=10, sticky="w")

        self.lbl_data_hdr = ctk.CTkLabel(
            info_f,
            text=f"📅  {self.prog['data']}",
            font=ctk.CTkFont(size=15, weight="bold"))
        self.lbl_data_hdr.pack(side="left", padx=(14, 6), pady=8)

        ctk.CTkLabel(info_f, text="│", text_color=C_BORDA).pack(side="left")

        self.lbl_dia_hdr = ctk.CTkLabel(
            info_f,
            text=self.prog["dia_semana"],
            font=ctk.CTkFont(size=13), text_color=C_TEXTO2)
        self.lbl_dia_hdr.pack(side="left", padx=6, pady=8)

        ctk.CTkLabel(info_f, text="│", text_color=C_BORDA).pack(side="left")

        self.lbl_turno_hdr = ctk.CTkLabel(
            info_f,
            text=TURNOS.get(self.prog["turno"], ""),
            font=ctk.CTkFont(size=13), text_color=C_CIZ_CLR)
        self.lbl_turno_hdr.pack(side="left", padx=6, pady=8)

        # Botão editar metadados (só supervisor)
        if self.sup:
            ctk.CTkButton(
                info_f, text="✏️", width=32, height=28,
                fg_color="transparent", hover_color=C_BORDA,
                font=ctk.CTkFont(size=14),
                command=self._editar_meta
            ).pack(side="left", padx=(4, 10))

        # Botões de ação à direita
        btn_f = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_f.grid(row=0, column=2, padx=12, pady=10, sticky="e")

        if self.sup:
            ctk.CTkButton(btn_f, text="+ Alocação", fg_color=C_VERDE,
                          height=36, command=self._add).pack(side="left", padx=4)
            ctk.CTkButton(btn_f, text="+ Fora de Máq.", fg_color=C_AMAR,
                          text_color="black", height=36,
                          command=self._add_fora).pack(side="left", padx=4)

        # Contador de alocações
        self.lbl_total = ctk.CTkLabel(btn_f, text="",
                                      font=ctk.CTkFont(size=11), text_color=C_TEXTO2)
        self.lbl_total.pack(side="left", padx=12)

        # ── Notebook de setores ──────────────────────────────
        self.nb = ttk.Notebook(self)
        self.nb.grid(row=1, column=0, padx=12, pady=6, sticky="nsew")
        self.trees = {}

        abas = SETORES + ["Fora de Máquina"]
        for s in abas:
            fr = ctk.CTkFrame(self.nb, fg_color=C_FUNDO, corner_radius=0)
            self.nb.add(fr, text=s)
            fr.grid_columnconfigure(0, weight=1)
            fr.grid_rowconfigure(0, weight=1)

            if s == "Fora de Máquina":
                cols = ("Crachá", "Operador", "Observação")
                widths = [80, 280, 500]
            else:
                cols = ("Máquina", "Crachá", "Operador", "Produto", "Descrição", "Nº OP")
                widths = [90, 80, 220, 90, 360, 80]

            tf, t = mk_table(fr, cols)
            tf.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

            for c, w in zip(cols, widths):
                t.heading(c, text=c)
                anchor = "center" if c in ("Máquina","Crachá","Nº OP") else "w"
                t.column(c, width=w, anchor=anchor, stretch=(c in ("Descrição","Observação","Operador")))

            self.trees[s] = t
            if self.sup:
                t.bind("<Double-1>", lambda e, ss=s: self._edit(ss))

        # ── Barra de ações na parte inferior ─────────────────
        if self.sup:
            bar = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=0, height=52)
            bar.grid(row=2, column=0, sticky="ew")
            bar.grid_propagate(False)

            ctk.CTkButton(bar, text="✏️  Editar Selecionado",
                          command=self._edit_aba).pack(side="left", padx=8, pady=10)
            ctk.CTkButton(bar, text="🗑️  Remover Selecionado",
                          fg_color=C_VERM, hover_color="#a02020",
                          command=self._del).pack(side="left", padx=4, pady=10)

            # Dica
            ctk.CTkLabel(bar, text="Dica: clique duplo na linha para editar rapidamente",
                         font=ctk.CTkFont(size=11), text_color=C_TEXTO2).pack(
                side="left", padx=20)

    def _editar_meta(self):
        """Abre dialog para editar data/dia/turno desta programação."""
        def _apos_salvar():
            # Recarregar o self.prog do banco
            conn = db.get_conn()
            p = conn.execute("SELECT * FROM programacoes WHERE id=?",
                             (self.prog["id"],)).fetchone()
            conn.close()
            if p:
                self.prog = dict(p)
                self._atualizar_titulo()
                # Atualizar labels do cabeçalho
                self.lbl_data_hdr.configure(text=f"📅  {self.prog['data']}")
                self.lbl_dia_hdr.configure(text=self.prog["dia_semana"])
                self.lbl_turno_hdr.configure(text=TURNOS.get(self.prog["turno"], ""))
            if self.cb:
                self.cb()

        DlgEditProg(self, programacao=self.prog, callback=_apos_salvar)

    def _load(self):
        for t in self.trees.values():
            t.delete(*t.get_children())

        total = 0
        for a in db.listar_alocacoes(self.prog["id"]):
            s = a.get("setor", "Picote")
            if s in self.trees:
                self.trees[s].insert("", "end", iid=f"a_{a['id']}",
                    values=(a["maquina"],
                            a["cracha"]      or "",
                            a["operador"]    or "—",
                            a["produto_cod"] or "",
                            a["produto_desc"] or "",
                            a["num_op"]      or ""))
                total += 1

        for fm in db.listar_fora_maquina(self.prog["id"]):
            self.trees["Fora de Máquina"].insert("", "end", iid=f"f_{fm['id']}",
                values=(fm["cracha"]     or "",
                        fm["operador"]   or "—",
                        fm["observacao"] or ""))
            total += 1

        # Atualizar contador
        fora_n = len(db.listar_fora_maquina(self.prog["id"]))
        aloc_n = total - fora_n
        self.lbl_total.configure(
            text=f"{aloc_n} alocações  |  {fora_n} fora de máq.")

        # Atualizar títulos das abas com contagens
        for i, s in enumerate(SETORES + ["Fora de Máquina"]):
            tree = self.trees[s]
            n = len(tree.get_children())
            self.nb.tab(i, text=f"{s}  ({n})")

    def _add(self):       DlgAloc(self, self.prog["id"], callback=self._load)
    def _add_fora(self):  DlgFora(self, self.prog["id"], callback=self._load)

    def _edit_aba(self):
        aba = self.nb.tab(self.nb.select(), "text")
        # Remover o contador do nome da aba
        aba = aba.split("  (")[0]
        self._edit(aba)

    def _edit(self, s):
        # s pode vir com contador — limpar
        s = s.split("  (")[0]
        t = self.trees.get(s)
        if not t:
            return
        sel = t.selection()
        if not sel:
            messagebox.showinfo("Selecione", "Clique em uma linha para selecionar.")
            return
        iid = sel[0]
        if iid.startswith("a_"):
            DlgAloc(self, self.prog["id"], aloc_id=int(iid[2:]), callback=self._load)
        elif iid.startswith("f_"):
            DlgFora(self, self.prog["id"], fm_id=int(iid[2:]), callback=self._load)

    def _del(self):
        aba = self.nb.tab(self.nb.select(), "text").split("  (")[0]
        t   = self.trees.get(aba)
        if not t:
            return
        sel = t.selection()
        if not sel:
            messagebox.showinfo("Selecione", "Clique em uma linha para selecionar.")
            return
        if not messagebox.askyesno("Confirmar", "Remover esta alocação?"):
            return
        iid = sel[0]
        if iid.startswith("a_"):
            db.deletar_alocacao(int(iid[2:]))
        elif iid.startswith("f_"):
            db.deletar_fora_maquina(int(iid[2:]))
        self._load()



class DlgAloc(ctk.CTkToplevel):
    def __init__(self,master,prog_id,aloc_id=None,callback=None):
        super().__init__(master)
        self.prog_id=prog_id; self.aid=aloc_id; self.cb=callback
        self.title("Aloca\u00e7\u00e3o"); self.geometry("540x520"); self.grab_set()
        self._ops=db.listar_operadores(); self._pros=db.listar_produtos(); self._maqs=db.listar_maquinas()
        self._nop=[""] +[f"{o['cracha']} \u2013 {o['nome']}" for o in self._ops]
        self._nmaq=[m["codigo"] for m in self._maqs]
        self._npro=[""] +[f"{p['codigo']} \u2013 {p['descricao'][:50]}" for p in self._pros]
        self._build()
        if aloc_id: self._fill()
    def _build(self):
        ctk.CTkLabel(self,text="Aloca\u00e7\u00e3o",font=ctk.CTkFont(size=16,weight="bold")).pack(pady=(16,8))
        f=ctk.CTkFrame(self,fg_color="transparent"); f.pack(fill="x",padx=30); f.grid_columnconfigure(1,weight=1)
        def row(l,w,r): ctk.CTkLabel(f,text=l).grid(row=r,column=0,sticky="w",pady=6); w.grid(row=r,column=1,padx=8,sticky="ew")
        self.cmaq=ctk.CTkComboBox(f,values=self._nmaq,width=360); row("M\u00e1quina:",self.cmaq,0)
        self.cop =ctk.CTkComboBox(f,values=self._nop, width=360); row("Operador:", self.cop, 1)
        cf=ctk.CTkFrame(f,fg_color="transparent")
        self.ecr=ctk.CTkEntry(cf,placeholder_text="Crach\u00e1",width=220); self.ecr.pack(side="left")
        ctk.CTkButton(cf,text="Buscar",width=80,command=self._bsc).pack(side="left",padx=6)
        row("Crach\u00e1:",cf,2)
        self.cpro=ctk.CTkComboBox(f,values=self._npro,width=360); row("Produto:",self.cpro,3)
        self.eop =ctk.CTkEntry(f,placeholder_text="N\u00ba da OP",width=360); row("N\u00ba OP:",self.eop,4)
        self.eobs=ctk.CTkEntry(f,placeholder_text="Opcional",width=360); row("Observação:",self.eobs,5)
        ctk.CTkButton(self,text="Salvar",fg_color=C_VERDE,command=self._salvar).pack(pady=20)
    def _bsc(self):
        cr=self.ecr.get().strip(); op=db.buscar_operador_por_cracha(cr)
        if op: self.cop.set(f"{op['cracha']} \u2013 {op['nome']}")
        else: messagebox.showinfo("N\u00e3o encontrado",f"Crach\u00e1 {cr} n\u00e3o cadastrado.")
    def _fill(self):
        conn=db.get_conn()
        a=conn.execute("SELECT a.*,m.codigo mc,o.cracha,o.nome on2,p.codigo pc,p.descricao pd FROM alocacoes a JOIN maquinas m ON m.id=a.maquina_id LEFT JOIN operadores o ON o.id=a.operador_id LEFT JOIN produtos p ON p.id=a.produto_id WHERE a.id=?",(self.aid,)).fetchone(); conn.close()
        if not a: return
        self.cmaq.set(a["mc"])
        if a["cracha"]: self.cop.set(f"{a['cracha']} \u2013 {a['on2']}")
        if a["pc"]: self.cpro.set(f"{a['pc']} \u2013 {(a['pd'] or '')[:50]}")
        if a["num_op"]: self.eop.insert(0,a["num_op"])
        if a["observacao"]: self.eobs.insert(0,a["observacao"])
    def _salvar(self):
        mq=next((m for m in self._maqs if m["codigo"]==self.cmaq.get()),None)
        if not mq: messagebox.showerror("Erro","M\u00e1quina inv\u00e1lida."); return
        op_id=None
        if self.cop.get():
            cr=self.cop.get().split("\u2013")[0].strip(); o=db.buscar_operador_por_cracha(cr); op_id=o["id"] if o else None
            if not op_id: messagebox.showerror("Erro", "Operador inválido. Selecione um cadastro existente."); return
        pr_id=None
        if self.cpro.get():
            cd=self.cpro.get().split("\u2013")[0].strip(); p=db.buscar_produto_por_codigo(cd); pr_id=p["id"] if p else None
            if not pr_id: messagebox.showerror("Erro", "Produto inválido. Selecione um cadastro existente."); return
        db.salvar_alocacao(self.prog_id,mq["id"],op_id,pr_id,self.eop.get().strip(),
                          observacao=self.eobs.get().strip(),aloc_id=self.aid)
        if self.cb: self.cb()
        self.destroy()


class DlgFora(ctk.CTkToplevel):
    def __init__(self,master,prog_id,fm_id=None,callback=None):
        super().__init__(master)
        self.prog_id=prog_id; self.fid=fm_id; self.cb=callback
        self.title("Fora de M\u00e1quina"); self.geometry("460,280".replace(",","x")); self.grab_set()
        self._ops=db.listar_operadores()
        self._nop=[""] +[f"{o['cracha']} \u2013 {o['nome']}" for o in self._ops]
        self._build()
        if fm_id: self._fill()
    def _build(self):
        ctk.CTkLabel(self,text="Fora de M\u00e1quina",font=ctk.CTkFont(size=15,weight="bold")).pack(pady=(16,8))
        f=ctk.CTkFrame(self,fg_color="transparent"); f.pack(fill="x",padx=30)
        ctk.CTkLabel(f,text="Operador:").grid(row=0,column=0,sticky="w",pady=8)
        self.cop=ctk.CTkComboBox(f,values=self._nop,width=300); self.cop.grid(row=0,column=1,padx=8)
        ctk.CTkLabel(f,text="Observa\u00e7\u00e3o:").grid(row=1,column=0,sticky="w",pady=8)
        self.eobs=ctk.CTkEntry(f,placeholder_text="Opcional",width=300); self.eobs.grid(row=1,column=1,padx=8)
        ctk.CTkButton(self,text="Salvar",fg_color=C_VERDE,command=self._salvar).pack(pady=20)
    def _fill(self):
        conn=db.get_conn()
        fm=conn.execute("SELECT f.*,o.cracha,o.nome on2 FROM fora_maquina f LEFT JOIN operadores o ON o.id=f.operador_id WHERE f.id=?",(self.fid,)).fetchone(); conn.close()
        if fm and fm["cracha"]: self.cop.set(f"{fm['cracha']} \u2013 {fm['on2']}")
        if fm and fm["observacao"]: self.eobs.insert(0,fm["observacao"])
    def _salvar(self):
        op_id=None
        if self.cop.get():
            cr=self.cop.get().split("\u2013")[0].strip(); o=db.buscar_operador_por_cracha(cr); op_id=o["id"] if o else None
        db.salvar_fora_maquina(self.prog_id,op_id,self.eobs.get().strip(),fm_id=self.fid)
        if self.cb: self.cb()
        self.destroy()


# ── OPERADORES ────────────────────────────────────────────────
class TelaOperadores(ctk.CTkFrame):
    def __init__(self,master,supervisor=True):
        super().__init__(master,fg_color=C_FUNDO,corner_radius=0)
        self.sup=supervisor; self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(2,weight=1); self._build()
    def _build(self):
        h=hdr_tela(self,"\U0001f477","Operadores")
        if self.sup: ctk.CTkButton(h,text="+ Novo",fg_color=C_VERDE,command=self._novo).pack(side="right",padx=16,pady=8)
        bf,self.eb=busca_entry(self,"Buscar por nome ou crach\u00e1...",self._filtrar)
        bf.grid(row=1,column=0,padx=16,pady=(0,6),sticky="w")
        tf,self.t=mk_table(self,("Crach\u00e1","Nome","Status"))
        tf.grid(row=2,column=0,padx=16,pady=4,sticky="nsew")
        self.t.heading("Crach\u00e1",text="Crach\u00e1"); self.t.column("Crach\u00e1",width=100,anchor="center")
        self.t.heading("Nome",text="Nome");   self.t.column("Nome",width=380)
        self.t.heading("Status",text="Status"); self.t.column("Status",width=80,anchor="center")
        if self.sup:
            bar=ctk.CTkFrame(self,fg_color="transparent"); bar.grid(row=3,column=0,padx=16,pady=(0,16),sticky="ew")
            ctk.CTkButton(bar,text="\u270f\ufe0f  Editar & Ativar",command=self._editar).pack(side="left",padx=4)
            ctk.CTkButton(bar,text="\U0001f5d1\ufe0f  Desativar",fg_color=C_VERM,command=self._desat).pack(side="left",padx=4)
        self.atualizar()
    def atualizar(self): self._filtrar("")
    def _filtrar(self,txt=""):
        self.t.delete(*self.t.get_children())
        for o in db.listar_operadores(apenas_ativos=False):
            if txt.lower() in o["nome"].lower() or txt in o["cracha"]:
                self.t.insert("","end",iid=str(o["id"]),
                              values=(o["cracha"],o["nome"],"\u2705 Ativo" if o["ativo"] else "\u274c Inativo"))
    def _novo(self): DlgOp(self,callback=self.atualizar)
    def _editar(self):
        s=self.t.selection()
        if not s: return
        o=next((x for x in db.listar_operadores(False) if str(x["id"])==s[0]),None)
        if o: DlgOp(self,operador=o,callback=self.atualizar)
    def _desat(self):
        s=self.t.selection()
        if not s: return
        if messagebox.askyesno("Confirmar","Desativar?"): db.deletar_operador(int(s[0])); self.atualizar()

class DlgOp(ctk.CTkToplevel):
    def __init__(self,master,operador=None,callback=None):
        super().__init__(master); self.o=operador; self.cb=callback
        self.title("Operador"); self.geometry("400x220"); self.grab_set()
        f=ctk.CTkFrame(self,fg_color="transparent"); f.pack(fill="x",padx=30,pady=20)
        ctk.CTkLabel(f,text="Crach\u00e1:").grid(row=0,column=0,sticky="w",pady=6)
        self.ecr=ctk.CTkEntry(f,width=260); self.ecr.grid(row=0,column=1,padx=8)
        ctk.CTkLabel(f,text="Nome:").grid(row=1,column=0,sticky="w",pady=6)
        self.enm=ctk.CTkEntry(f,width=260); self.enm.grid(row=1,column=1,padx=8)
        if self.o: self.ecr.insert(0,self.o["cracha"]); self.enm.insert(0,self.o["nome"])
        ctk.CTkButton(self,text="Salvar",fg_color=C_VERDE,command=self._s).pack(pady=10)
    def _s(self):
        cr=self.ecr.get().strip(); nm=self.enm.get().strip()
        if not cr or not nm: messagebox.showerror("Erro","Preencha crach\u00e1 e nome."); return
        db.salvar_operador(cr,nm,op_id=self.o["id"] if self.o else None)
        if self.cb: self.cb()
        self.destroy()


# ── PRODUTOS ─────────────────────────────────────────────────
class TelaProdutos(ctk.CTkFrame):
    def __init__(self,master,supervisor=True):
        super().__init__(master,fg_color=C_FUNDO,corner_radius=0)
        self.sup=supervisor; self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(2,weight=1); self._build()
    def _build(self):
        h=hdr_tela(self,"\U0001f4e6","Produtos")
        if self.sup: ctk.CTkButton(h,text="+ Novo",fg_color=C_VERDE,command=self._novo).pack(side="right",padx=16,pady=8)
        bf,self.eb=busca_entry(self,"Buscar por c\u00f3digo ou descri\u00e7\u00e3o...",self._filtrar)
        bf.grid(row=1,column=0,padx=16,pady=(0,6),sticky="w")
        tf,self.t=mk_table(self,("C\u00f3digo","Descri\u00e7\u00e3o","Status"))
        tf.grid(row=2,column=0,padx=16,pady=4,sticky="nsew")
        self.t.heading("C\u00f3digo",text="C\u00f3digo"); self.t.column("C\u00f3digo",width=120,anchor="center")
        self.t.heading("Descri\u00e7\u00e3o",text="Descri\u00e7\u00e3o"); self.t.column("Descri\u00e7\u00e3o",width=500)
        self.t.heading("Status",text="Status"); self.t.column("Status",width=80,anchor="center")
        if self.sup:
            bar=ctk.CTkFrame(self,fg_color="transparent"); bar.grid(row=3,column=0,padx=16,pady=(0,16),sticky="ew")
            ctk.CTkButton(bar,text="\u270f\ufe0f  Editar",command=self._editar).pack(side="left",padx=4)
            ctk.CTkButton(bar,text="\U0001f5d1\ufe0f  Desativar",fg_color=C_VERM,command=self._desat).pack(side="left",padx=4)
        self.atualizar()
    def atualizar(self): self._filtrar("")
    def _filtrar(self,txt=""):
        self.t.delete(*self.t.get_children())
        for p in db.listar_produtos(apenas_ativos=False):
            if txt.lower() in p["descricao"].lower() or txt.lower() in p["codigo"].lower():
                self.t.insert("","end",iid=str(p["id"]),
                              values=(p["codigo"],p["descricao"],"\u2705" if p["ativo"] else "\u274c"))
    def _novo(self): DlgProd(self,callback=self.atualizar)
    def _editar(self):
        s=self.t.selection()
        if not s: return
        p=next((x for x in db.listar_produtos(False) if str(x["id"])==s[0]),None)
        if p: DlgProd(self,produto=p,callback=self.atualizar)
    def _desat(self):
        s=self.t.selection()
        if not s: return
        if messagebox.askyesno("Confirmar","Desativar?"): db.deletar_produto(int(s[0])); self.atualizar()

class DlgProd(ctk.CTkToplevel):
    def __init__(self,master,produto=None,callback=None):
        super().__init__(master); self.p=produto; self.cb=callback
        self.title("Produto"); self.geometry("540x220"); self.grab_set()
        f=ctk.CTkFrame(self,fg_color="transparent"); f.pack(fill="x",padx=30,pady=20)
        ctk.CTkLabel(f,text="C\u00f3digo:").grid(row=0,column=0,sticky="w",pady=6)
        self.ec=ctk.CTkEntry(f,width=380); self.ec.grid(row=0,column=1,padx=8)
        ctk.CTkLabel(f,text="Descri\u00e7\u00e3o:").grid(row=1,column=0,sticky="w",pady=6)
        self.ed=ctk.CTkEntry(f,width=380); self.ed.grid(row=1,column=1,padx=8)
        if self.p: self.ec.insert(0,self.p["codigo"]); self.ed.insert(0,self.p["descricao"])
        ctk.CTkButton(self,text="Salvar",fg_color=C_VERDE,command=self._s).pack(pady=10)
    def _s(self):
        c=self.ec.get().strip(); d=self.ed.get().strip()
        if not c or not d: messagebox.showerror("Erro","Preencha c\u00f3digo e descri\u00e7\u00e3o."); return
        db.salvar_produto(c,d,prod_id=self.p["id"] if self.p else None)
        if self.cb: self.cb()
        self.destroy()


# ── MÁQUINAS ─────────────────────────────────────────────────
class TelaMaquinas(ctk.CTkFrame):
    def __init__(self,master,supervisor=True):
        super().__init__(master,fg_color=C_FUNDO,corner_radius=0)
        self.sup=supervisor; self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(1,weight=1); self._build()
    def _build(self):
        h=hdr_tela(self,"\U0001f3ed","M\u00e1quinas")
        if self.sup: ctk.CTkButton(h,text="+ Nova",fg_color=C_VERDE,command=self._nova).pack(side="right",padx=16,pady=8)
        tf,self.t=mk_table(self,("C\u00f3digo","Setor","Descri\u00e7\u00e3o"))
        tf.grid(row=1,column=0,padx=16,pady=8,sticky="nsew")
        self.t.heading("C\u00f3digo",text="C\u00f3digo"); self.t.column("C\u00f3digo",width=100,anchor="center")
        self.t.heading("Setor",text="Setor"); self.t.column("Setor",width=160)
        self.t.heading("Descri\u00e7\u00e3o",text="Descri\u00e7\u00e3o"); self.t.column("Descri\u00e7\u00e3o",width=400)
        if self.sup:
            bar=ctk.CTkFrame(self,fg_color="transparent"); bar.grid(row=2,column=0,padx=16,pady=(0,16),sticky="ew")
            ctk.CTkButton(bar,text="\u270f\ufe0f  Editar",command=self._editar).pack(side="left",padx=4)
        self.atualizar()
    def atualizar(self):
        self.t.delete(*self.t.get_children())
        for m in db.listar_maquinas():
            self.t.insert("","end",iid=str(m["id"]),values=(m["codigo"],m["setor"],m["descricao"] or ""))
    def _nova(self): DlgMaq(self,callback=self.atualizar)
    def _editar(self):
        s=self.t.selection()
        if not s: return
        conn=db.get_conn(); m=conn.execute("SELECT * FROM maquinas WHERE id=?",(int(s[0]),)).fetchone(); conn.close()
        if m: DlgMaq(self,maquina=dict(m),callback=self.atualizar)

class DlgMaq(ctk.CTkToplevel):
    def __init__(self,master,maquina=None,callback=None):
        super().__init__(master); self.m=maquina; self.cb=callback
        self.title("M\u00e1quina"); self.geometry("440x260"); self.grab_set()
        f=ctk.CTkFrame(self,fg_color="transparent"); f.pack(fill="x",padx=30,pady=20)
        ctk.CTkLabel(f,text="C\u00f3digo:").grid(row=0,column=0,sticky="w",pady=6)
        self.ec=ctk.CTkEntry(f,width=300); self.ec.grid(row=0,column=1,padx=8)
        ctk.CTkLabel(f,text="Setor:").grid(row=1,column=0,sticky="w",pady=6)
        self.cs=ctk.CTkComboBox(f,values=SETORES,width=300); self.cs.grid(row=1,column=1,padx=8)
        ctk.CTkLabel(f,text="Descri\u00e7\u00e3o:").grid(row=2,column=0,sticky="w",pady=6)
        self.ed=ctk.CTkEntry(f,width=300); self.ed.grid(row=2,column=1,padx=8)
        if self.m: self.ec.insert(0,self.m["codigo"]); self.cs.set(self.m["setor"]); self.ed.insert(0,self.m.get("descricao") or "")
        ctk.CTkButton(self,text="Salvar",fg_color=C_VERDE,command=self._s).pack(pady=10)
    def _s(self):
        c=self.ec.get().strip(); s=self.cs.get(); d=self.ed.get().strip()
        if not c or not s: messagebox.showerror("Erro","Preencha c\u00f3digo e setor."); return
        db.salvar_maquina(c,s,d,maq_id=self.m["id"] if self.m else None)
        if self.cb: self.cb()
        self.destroy()


# ── USUÁRIOS ─────────────────────────────────────────────────
class TelaUsuarios(ctk.CTkFrame):
    def __init__(self,master,supervisor=True):
        super().__init__(master,fg_color=C_FUNDO,corner_radius=0)
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(2,weight=1); self._build()
    def _build(self):
        h=hdr_tela(self,"\U0001f464","Usu\u00e1rios do Sistema")
        ctk.CTkButton(h,text="+ Novo",fg_color=C_VERDE,command=self._novo).pack(side="right",padx=16,pady=8)
        info=ctk.CTkFrame(self,fg_color="#0d2010",corner_radius=8,border_width=1,border_color=C_VERDE)
        info.grid(row=1,column=0,padx=16,pady=(0,8),sticky="ew")
        ctk.CTkLabel(info,text="\U0001f6e1\ufe0f  Supervisor: acesso total  \u2014  \U0001f464  Operador: somente visualiza\u00e7\u00e3o",
                     text_color=C_VERDE_CLR,font=ctk.CTkFont(size=12)).pack(padx=16,pady=8)
        tf,self.t=mk_table(self,("Login","Nome","N\u00edvel","Status"))
        tf.grid(row=2,column=0,padx=16,pady=4,sticky="nsew")
        self.t.heading("Login",text="Login");  self.t.column("Login",width=140,anchor="center")
        self.t.heading("Nome",text="Nome");    self.t.column("Nome",width=280)
        self.t.heading("N\u00edvel",text="N\u00edvel");  self.t.column("N\u00edvel",width=120,anchor="center")
        self.t.heading("Status",text="Status");self.t.column("Status",width=80,anchor="center")
        bar=ctk.CTkFrame(self,fg_color="transparent"); bar.grid(row=3,column=0,padx=16,pady=(0,16),sticky="ew")
        ctk.CTkButton(bar,text="\u270f\ufe0f  Editar",command=self._editar).pack(side="left",padx=4)
        ctk.CTkButton(bar,text="\U0001f5d1\ufe0f  Desativar",fg_color=C_VERM,command=self._desat).pack(side="left",padx=4)
        self.atualizar()
    def atualizar(self):
        self.t.delete(*self.t.get_children())
        for u in db.listar_usuarios():
            ni="\U0001f6e1\ufe0f Supervisor" if u["nivel"]=="supervisor" else "\U0001f464 Operador"
            self.t.insert("","end",iid=str(u["id"]),
                          values=(u["login"],u["nome"],ni,"\u2705 Ativo" if u["ativo"] else "\u274c Inativo"))
    def _novo(self): DlgUser(self,callback=self.atualizar)
    def _editar(self):
        s=self.t.selection()
        if not s: return
        u=next((x for x in db.listar_usuarios() if str(x["id"])==s[0]),None)
        if u: DlgUser(self,usuario=u,callback=self.atualizar)
    def _desat(self):
        s=self.t.selection()
        if not s: return
        u=next((x for x in db.listar_usuarios() if str(x["id"])==s[0]),None)
        if u and u["login"]=="admin": messagebox.showerror("Erro","N\u00e3o \u00e9 poss\u00edvel desativar o admin."); return
        if messagebox.askyesno("Confirmar","Desativar?"): db.deletar_usuario(int(s[0])); self.atualizar()

class DlgUser(ctk.CTkToplevel):
    def __init__(self,master,usuario=None,callback=None):
        super().__init__(master); self.u=usuario; self.cb=callback
        self.title("Usu\u00e1rio"); self.geometry("440x340"); self.grab_set()
        ctk.CTkLabel(self,text="Usu\u00e1rio do Sistema",font=ctk.CTkFont(size=16,weight="bold")).pack(pady=(16,8))
        f=ctk.CTkFrame(self,fg_color="transparent"); f.pack(fill="x",padx=30); f.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(f,text="Login:").grid(row=0,column=0,sticky="w",pady=6)
        self.el=ctk.CTkEntry(f,width=280); self.el.grid(row=0,column=1,padx=8)
        ctk.CTkLabel(f,text="Nome:").grid(row=1,column=0,sticky="w",pady=6)
        self.en=ctk.CTkEntry(f,width=280); self.en.grid(row=1,column=1,padx=8)
        ctk.CTkLabel(f,text="Senha:").grid(row=2,column=0,sticky="w",pady=6)
        self.es=ctk.CTkEntry(f,width=280,show="\u25cf",
                             placeholder_text="Deixe vazio para n\u00e3o alterar" if usuario else "")
        self.es.grid(row=2,column=1,padx=8)
        ctk.CTkLabel(f,text="N\u00edvel:").grid(row=3,column=0,sticky="w",pady=6)
        self.cnv=ctk.CTkComboBox(f,values=["supervisor","operador"],width=280); self.cnv.grid(row=3,column=1,padx=8)
        if self.u: self.el.insert(0,self.u["login"]); self.en.insert(0,self.u["nome"]); self.cnv.set(self.u["nivel"])
        ctk.CTkButton(self,text="Salvar",fg_color=C_VERDE,command=self._s).pack(pady=20)
    def _s(self):
        l=self.el.get().strip(); n=self.en.get().strip(); s=self.es.get(); nv=self.cnv.get()
        if not l or not n: messagebox.showerror("Erro","Preencha login e nome."); return
        if not self.u and not s: messagebox.showerror("Erro","Informe uma senha."); return
        db.salvar_usuario(l,s,n,nv,usuario_id=self.u["id"] if self.u else None)
        if self.cb: self.cb()
        self.destroy()


# ── IMPORTAR ─────────────────────────────────────────────────
class TelaImportar(ctk.CTkFrame):
    def __init__(self,master,supervisor=True):
        super().__init__(master,fg_color=C_FUNDO,corner_radius=0)
        self.grid_columnconfigure(0,weight=1); self._build()
    def _build(self):
        card=ctk.CTkFrame(self,fg_color=C_CARD,corner_radius=12,border_width=1,border_color=C_BORDA)
        card.pack(padx=40,pady=40,fill="both",expand=True)
        ctk.CTkLabel(card,text="\U0001f4e5  Importar Planilha Excel",font=ctk.CTkFont(size=22,weight="bold")).pack(pady=(30,8))
        ctk.CTkLabel(card,text="Importa operadores, produtos e programa\u00e7\u00f5es da planilha original.",
                     text_color=C_TEXTO2,font=ctk.CTkFont(size=13)).pack(pady=(0,20))
        ctk.CTkButton(card,text="\U0001f4c2  Selecionar arquivo .xlsx",height=48,
                      font=ctk.CTkFont(size=15),command=self._sel).pack(pady=8)
        self.larq=ctk.CTkLabel(card,text="Nenhum arquivo selecionado",text_color="gray60"); self.larq.pack(pady=4)
        self.bimp=ctk.CTkButton(card,text="\u25b6  Iniciar Importa\u00e7\u00e3o",fg_color=C_VERDE,
                                height=44,command=self._imp); self.bimp.pack(pady=16)
        self.prog=ctk.CTkProgressBar(card,width=400); self.prog.set(0); self.prog.pack(pady=8)
        self.lst=ctk.CTkLabel(card,text="",font=ctk.CTkFont(size=13)); self.lst.pack(pady=4)
        self.txt=ctk.CTkTextbox(card,height=200,font=ctk.CTkFont(family="Courier",size=11))
        self.txt.pack(padx=20,pady=12,fill="x")
        self.caminho=None
    def atualizar(self): pass
    def _sel(self):
        if getattr(self, "_importando", False): return
        p=filedialog.askopenfilename(filetypes=[("Excel","*.xlsx *.xls *.xlsm")])
        if p:
            self.caminho=p; self.larq.configure(text=f"\U0001f4c4  {p.split('/')[-1].split(chr(92))[-1]}",text_color=C_TEXTO)
            self.bimp.configure(state="normal")
    def _imp(self):
        if not self.caminho or getattr(self, "_importando", False): return
        self._importando = True
        caminho = self.caminho
        self.bimp.configure(state="disabled")
        self.lst.configure(text="\u23f3  Importando...",text_color=C_AMAR)
        self.txt.delete("0.0","end")
        self.prog.configure(mode="indeterminate")
        self.prog.start()
        resultados = queue.Queue()
        def t():
            try:
                r = imp.importar_planilha(caminho)
            except Exception as exc:
                logging.exception("Falha inesperada na importação")
                r = imp.novo_resultado()
                r["erros"].append(str(exc))
            resultados.put(r)
        def concluir():
            try:
                r = resultados.get_nowait()
            except queue.Empty:
                self.after(100, concluir)
                return
            self._importando = False
            self.prog.stop()
            self.prog.configure(mode="determinate")
            self.prog.set(0 if r["erros"] else 1)
            pendencias = bool(r["erros"] or r["avisos"])
            self.lst.configure(text="Importação finalizada com pendências. Confira o relatório." if pendencias else "Importação concluída.",
                               text_color=C_AMAR if pendencias else C_VERDE_CLR)
            log = "Registros novos:\n" + "\n".join(
                f"{nome}: {r[chave]}" for chave, nome in (
                    ("operadores", "Operadores"), ("produtos", "Produtos"),
                    ("programacoes", "Programações"), ("alocacoes", "Alocações"),
                    ("fora_maquina", "Fora de máquina")))
            log += f"\nRegistros já existentes: {r['ignorados']}\n"
            for chave, titulo in (("erros", "Erros — registros não importados"), ("avisos", "Avisos")):
                if r[chave]:
                    log += f"\n{titulo} ({len(r[chave])}):\n" + "\n".join(r[chave]) + "\n"
            self.txt.insert("end",log)
            self.bimp.configure(state="normal")
        threading.Thread(target=t,daemon=True).start()
        self.after(100, concluir)


if __name__=="__main__":
    logging.basicConfig(filename=db.os.path.join(db.os.path.dirname(db.DB_PATH), "sistema.log"),
                        encoding="utf-8", level=logging.ERROR,
                        format="%(asctime)s %(levelname)s %(message)s")
    TelaLogin().mainloop()
