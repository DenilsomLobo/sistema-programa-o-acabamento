import sqlite3
import os
import hashlib
import hmac
import sys
from contextlib import closing
from datetime import datetime

DB_PATH = os.path.join(
    os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__),
    "acabamento.db",
)

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _hash(senha):
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt), 600000).hex()
    return f"pbkdf2_sha256$600000${salt}${digest}"


def _verificar_senha(senha, armazenada):
    if not armazenada.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(hashlib.sha256(senha.encode()).hexdigest(), armazenada)
    try:
        _, iteracoes, salt, digest = armazenada.split("$")
        atual = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt), int(iteracoes)).hex()
        return hmac.compare_digest(atual, digest)
    except (ValueError, TypeError):
        return False

def inicializar_banco():
    with closing(get_conn()) as conn, conn:
        c = conn.cursor()

        c.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                nome TEXT NOT NULL,
                nivel TEXT NOT NULL DEFAULT 'operador',
                ativo INTEGER DEFAULT 1
            );
        """)

        # Criar acesso inicial somente em uma base sem usuários.
        existe = c.execute("SELECT id FROM usuarios LIMIT 1").fetchone()
        if not existe:
            h = _hash("admin123")
            c.execute("INSERT INTO usuarios (login, senha_hash, nome, nivel) VALUES (?,?,?,?)",
                      ("admin", h, "Administrador", "supervisor"))

        c.executescript("""
            CREATE TABLE IF NOT EXISTS operadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cracha TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                ativo INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                descricao TEXT NOT NULL,
                ativo INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS maquinas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                setor TEXT NOT NULL,
                descricao TEXT,
                ativo INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS programacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data DATE NOT NULL,
                turno INTEGER NOT NULL,
                dia_semana TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS alocacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                programacao_id INTEGER NOT NULL REFERENCES programacoes(id) ON DELETE CASCADE,
                maquina_id INTEGER NOT NULL REFERENCES maquinas(id),
                operador_id INTEGER REFERENCES operadores(id),
                produto_id INTEGER REFERENCES produtos(id),
                num_op TEXT,
                observacao TEXT
            );

            CREATE TABLE IF NOT EXISTS fora_maquina (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                programacao_id INTEGER NOT NULL REFERENCES programacoes(id) ON DELETE CASCADE,
                operador_id INTEGER REFERENCES operadores(id),
                observacao TEXT
            );
        """)

        # Exemplos ficticios somente para uma base sem maquinas.
        # Bases de trabalho existentes mantem seus cadastros.
        if not c.execute("SELECT id FROM maquinas LIMIT 1").fetchone():
            maquinas_exemplo = [
                ("PCT900001", "Picote", "Maquina ficticia 1"),
                ("LXR900002", "Saco para Lixo", "Maquina ficticia 2"),
                ("SCL900003", "Sacoleira", "Maquina ficticia 3"),
                ("CSD900004", "Corte Solda", "Maquina ficticia 4"),
            ]
            c.executemany(
                "INSERT INTO maquinas (codigo, setor, descricao) VALUES (?, ?, ?)",
                maquinas_exemplo,
            )

# ── OPERADORES ──────────────────────────────────────────────
def listar_operadores(apenas_ativos=True):
    with closing(get_conn()) as conn, conn:
        filtro = "WHERE ativo=1" if apenas_ativos else ""
        rows = conn.execute(f"SELECT * FROM operadores {filtro} ORDER BY nome").fetchall()
        return [dict(r) for r in rows]

def buscar_operador_por_cracha(cracha):
    with closing(get_conn()) as conn, conn:
        r = conn.execute("SELECT * FROM operadores WHERE cracha=?", (str(cracha),)).fetchone()
        return dict(r) if r else None

def salvar_operador(cracha, nome, ativo=1, op_id=None):
    with closing(get_conn()) as conn, conn:
        if op_id:
            conn.execute("UPDATE operadores SET cracha=?, nome=?, ativo=? WHERE id=?",
                         (str(cracha), nome.strip().upper(), ativo, op_id))
        else:
            conn.execute("INSERT INTO operadores (cracha, nome, ativo) VALUES (?,?,?) ON CONFLICT(cracha) DO UPDATE SET nome=excluded.nome, ativo=excluded.ativo",
                         (str(cracha), nome.strip().upper(), ativo))

def deletar_operador(op_id):
    with closing(get_conn()) as conn, conn:
        conn.execute("UPDATE operadores SET ativo=0 WHERE id=?", (op_id,))

# ── PRODUTOS ─────────────────────────────────────────────────
def listar_produtos(apenas_ativos=True):
    with closing(get_conn()) as conn, conn:
        filtro = "WHERE ativo=1" if apenas_ativos else ""
        rows = conn.execute(f"SELECT * FROM produtos {filtro} ORDER BY codigo").fetchall()
        return [dict(r) for r in rows]

def buscar_produto_por_codigo(codigo):
    with closing(get_conn()) as conn, conn:
        codigo = str(codigo).strip().upper()
        r = conn.execute("SELECT * FROM produtos WHERE codigo=? COLLATE NOCASE ORDER BY (codigo=?) DESC,id",
                         (codigo, codigo)).fetchone()
        return dict(r) if r else None

def salvar_produto(codigo, descricao, ativo=1, prod_id=None):
    with closing(get_conn()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        codigo = codigo.strip().upper()
        if not prod_id:
            existente = conn.execute("SELECT id FROM produtos WHERE codigo=? COLLATE NOCASE ORDER BY (codigo=?) DESC,id",
                                      (codigo, codigo)).fetchone()
            if existente:
                prod_id = existente["id"]
        if prod_id:
            conn.execute("UPDATE produtos SET codigo=?, descricao=?, ativo=? WHERE id=?",
                         (codigo.strip(), descricao.strip(), ativo, prod_id))
        else:
            conn.execute("INSERT INTO produtos (codigo, descricao, ativo) VALUES (?,?,?) ON CONFLICT(codigo) DO UPDATE SET descricao=excluded.descricao, ativo=excluded.ativo",
                         (codigo.strip(), descricao.strip(), ativo))

def deletar_produto(prod_id):
    with closing(get_conn()) as conn, conn:
        conn.execute("UPDATE produtos SET ativo=0 WHERE id=?", (prod_id,))

# ── MÁQUINAS ─────────────────────────────────────────────────
def listar_maquinas(setor=None):
    with closing(get_conn()) as conn, conn:
        if setor:
            rows = conn.execute("SELECT * FROM maquinas WHERE setor=? AND ativo=1 ORDER BY codigo",
                                (setor,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM maquinas WHERE ativo=1 ORDER BY setor, codigo").fetchall()
        return [dict(r) for r in rows]

def salvar_maquina(codigo, setor, descricao="", maq_id=None):
    with closing(get_conn()) as conn, conn:
        if maq_id:
            conn.execute("UPDATE maquinas SET codigo=?, setor=?, descricao=? WHERE id=?",
                         (codigo, setor, descricao, maq_id))
        else:
            conn.execute("INSERT INTO maquinas (codigo, setor, descricao) VALUES (?,?,?)",
                         (codigo, setor, descricao))

# ── PROGRAMAÇÕES ─────────────────────────────────────────────
def listar_programacoes():
    with closing(get_conn()) as conn, conn:
        rows = conn.execute(
            "SELECT * FROM programacoes ORDER BY data DESC, turno"
        ).fetchall()
        return [dict(r) for r in rows]

def buscar_programacao(data, turno):
    with closing(get_conn()) as conn, conn:
        r = conn.execute(
            "SELECT * FROM programacoes WHERE data=? AND turno=?", (data, turno)
        ).fetchone()
        return dict(r) if r else None

def criar_programacao(data, turno, dia_semana):
    with closing(get_conn()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        dia_semana = _validar_programacao(conn, data, turno)
        cursor = conn.execute(
            "INSERT INTO programacoes (data, turno, dia_semana) VALUES (?,?,?)",
            (data, turno, dia_semana)
        )
        prog_id = cursor.lastrowid
        return prog_id

def atualizar_programacao(prog_id, data, turno, dia_semana):
    with closing(get_conn()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        dia_semana = _validar_programacao(conn, data, turno, prog_id)
        conn.execute(
            "UPDATE programacoes SET data=?, turno=?, dia_semana=? WHERE id=?",
            (data, turno, dia_semana, prog_id)
        )

def deletar_programacao(prog_id):
    with closing(get_conn()) as conn, conn:
        conn.execute("DELETE FROM programacoes WHERE id=?", (prog_id,))


def _validar_programacao(conn, data, turno, prog_id=-1):
    dia = datetime.strptime(data, "%Y-%m-%d").weekday()
    if turno not in (1, 2, 3):
        raise ValueError("Turno inválido. Selecione 1, 2 ou 3.")
    if conn.execute("SELECT id FROM programacoes WHERE data=? AND turno=? AND id<>?",
                    (data, turno, prog_id)).fetchone():
        raise ValueError("Já existe uma programação para esta data e turno.")
    return ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
            "Sexta-feira", "Sábado", "Domingo")[dia]

# ── ALOCAÇÕES ─────────────────────────────────────────────────
def listar_alocacoes(programacao_id):
    with closing(get_conn()) as conn, conn:
        rows = conn.execute("""
            SELECT a.id, a.num_op, a.observacao,
                   m.codigo as maquina, m.setor,
                   o.cracha, o.nome as operador,
                   p.codigo as produto_cod, p.descricao as produto_desc
            FROM alocacoes a
            JOIN maquinas m ON m.id = a.maquina_id
            LEFT JOIN operadores o ON o.id = a.operador_id
            LEFT JOIN produtos p ON p.id = a.produto_id
            WHERE a.programacao_id=?
            ORDER BY m.setor, m.codigo
        """, (programacao_id,)).fetchall()
        return [dict(r) for r in rows]

def salvar_alocacao(programacao_id, maquina_id, operador_id, produto_id, num_op, observacao="", aloc_id=None):
    with closing(get_conn()) as conn, conn:
        if aloc_id:
            conn.execute("""
                UPDATE alocacoes SET maquina_id=?, operador_id=?, produto_id=?, num_op=?, observacao=?
                WHERE id=?
            """, (maquina_id, operador_id, produto_id, num_op, observacao, aloc_id))
        else:
            conn.execute("""
                INSERT INTO alocacoes (programacao_id, maquina_id, operador_id, produto_id, num_op, observacao)
                VALUES (?,?,?,?,?,?)
            """, (programacao_id, maquina_id, operador_id, produto_id, num_op, observacao))

def deletar_alocacao(aloc_id):
    with closing(get_conn()) as conn, conn:
        conn.execute("DELETE FROM alocacoes WHERE id=?", (aloc_id,))

def listar_fora_maquina(programacao_id):
    with closing(get_conn()) as conn, conn:
        rows = conn.execute("""
            SELECT f.id, f.observacao, o.cracha, o.nome as operador
            FROM fora_maquina f
            LEFT JOIN operadores o ON o.id = f.operador_id
            WHERE f.programacao_id=?
        """, (programacao_id,)).fetchall()
        return [dict(r) for r in rows]

def salvar_fora_maquina(programacao_id, operador_id, observacao="", fm_id=None):
    if not operador_id:
        raise ValueError("Selecione um operador válido para a programação fora de máquina.")
    with closing(get_conn()) as conn, conn:
        if fm_id:
            conn.execute("UPDATE fora_maquina SET operador_id=?, observacao=? WHERE id=?",
                         (operador_id, observacao, fm_id))
        else:
            conn.execute("INSERT INTO fora_maquina (programacao_id, operador_id, observacao) VALUES (?,?,?)",
                         (programacao_id, operador_id, observacao))

def deletar_fora_maquina(fm_id):
    with closing(get_conn()) as conn, conn:
        conn.execute("DELETE FROM fora_maquina WHERE id=?", (fm_id,))

# ── USUÁRIOS ──────────────────────────────────────────────────
def autenticar(login, senha):
    with closing(get_conn()) as conn, conn:
        u = conn.execute(
            "SELECT * FROM usuarios WHERE login=? AND ativo=1",
            (login.strip(),)
        ).fetchone()
        if not u or not _verificar_senha(senha, u["senha_hash"]):
            return None
        if not u["senha_hash"].startswith("pbkdf2_sha256$"):
            conn.execute("UPDATE usuarios SET senha_hash=? WHERE id=?", (_hash(senha), u["id"]))
        return {k: u[k] for k in ("id", "login", "nome", "nivel", "ativo")}

def listar_usuarios():
    with closing(get_conn()) as conn, conn:
        rows = conn.execute("SELECT id,login,nome,nivel,ativo FROM usuarios ORDER BY nivel,nome").fetchall()
        return [dict(r) for r in rows]

def salvar_usuario(login, senha, nome, nivel, usuario_id=None):
    with closing(get_conn()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        if nivel not in ("supervisor", "operador"):
            raise ValueError("Nível inválido. Selecione supervisor ou operador.")
        if not login.strip() or not nome.strip() or (not usuario_id and not senha):
            raise ValueError("Preencha login, nome e senha do novo usuário.")
        login, nome = login.strip(), nome.strip()
        if usuario_id and nivel != "supervisor":
            _proteger_supervisor(conn, usuario_id)
        if usuario_id:
            if senha:
                conn.execute("UPDATE usuarios SET login=?,senha_hash=?,nome=?,nivel=? WHERE id=?",
                             (login, _hash(senha), nome, nivel, usuario_id))
            else:
                conn.execute("UPDATE usuarios SET login=?,nome=?,nivel=? WHERE id=?",
                             (login, nome, nivel, usuario_id))
        else:
            conn.execute("INSERT INTO usuarios (login,senha_hash,nome,nivel) VALUES (?,?,?,?)",
                         (login, _hash(senha), nome, nivel))

def deletar_usuario(usuario_id):
    with closing(get_conn()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        _proteger_supervisor(conn, usuario_id)
        conn.execute("UPDATE usuarios SET ativo=0 WHERE id=?", (usuario_id,))


def _proteger_supervisor(conn, usuario_id):
    u = conn.execute("SELECT * FROM usuarios WHERE id=?", (usuario_id,)).fetchone()
    if u and u["ativo"] and u["nivel"] == "supervisor":
        outro = conn.execute("SELECT id FROM usuarios WHERE ativo=1 AND nivel='supervisor' AND id<>?",
                             (usuario_id,)).fetchone()
        if not outro:
            raise ValueError("Não é possível remover o último supervisor ativo.")

# ── VISÃO GERAL ───────────────────────────────────────────────
def alocacoes_por_data(data):
    """Retorna alocações agrupadas por turno para uma data específica."""
    with closing(get_conn()) as conn, conn:
        resultado = {}
        for turno in (1, 2, 3):
            prog = conn.execute(
                "SELECT id FROM programacoes WHERE data=? AND turno=?", (data, turno)
            ).fetchone()
            if prog:
                rows = conn.execute("""
                    SELECT a.num_op, m.codigo as maquina, m.setor,
                           o.cracha, o.nome as operador,
                           p.codigo as produto_cod, p.descricao as produto_desc
                    FROM alocacoes a
                    JOIN maquinas m ON m.id=a.maquina_id
                    LEFT JOIN operadores o ON o.id=a.operador_id
                    LEFT JOIN produtos p ON p.id=a.produto_id
                    WHERE a.programacao_id=?
                    ORDER BY m.setor, m.codigo
                """, (prog["id"],)).fetchall()
                foras = conn.execute("""
                    SELECT f.observacao, o.cracha, o.nome as operador
                    FROM fora_maquina f
                    LEFT JOIN operadores o ON o.id=f.operador_id
                    WHERE f.programacao_id=?
                """, (prog["id"],)).fetchall()
                resultado[turno] = {
                    "prog_id": prog["id"],
                    "alocacoes": [dict(r) for r in rows],
                    "fora_maquina": [dict(r) for r in foras],
                }
            else:
                resultado[turno] = None
        return resultado
