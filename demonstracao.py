"""Demonstração com dados inteiramente fictícios, separada da base de trabalho."""
import argparse
from contextlib import closing
from datetime import date
from pathlib import Path

import database as db


def preparar_banco(caminho):
    """Cria uma base nova, sem copiar ou consultar dados reais."""
    caminho = Path(caminho).resolve()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    # Nunca sobrescreve um banco existente, mesmo se o caminho for incorreto.
    with caminho.open('xb'):
        pass
    anterior = db.DB_PATH
    try:
        db.DB_PATH = str(caminho)
        db.inicializar_banco()
        with closing(db.get_conn()) as conn, conn:
            conn.execute('CREATE TABLE demonstracao (somente_dados_ficticios INTEGER NOT NULL)')
            conn.execute('INSERT INTO demonstracao VALUES (1)')
            conn.execute("UPDATE usuarios SET nome='John Doe'")
            for i in range(1, 6):
                conn.execute('INSERT INTO operadores (cracha,nome) VALUES (?,?)',
                             (f'{900000+i}', 'John Doe'))
            for i in range(1, 4):
                conn.execute('INSERT INTO produtos (codigo,descricao) VALUES (?,?)',
                             (f'DEMO-{i:03d}', f'Produto fictício {i}'))
            operadores = [r[0] for r in conn.execute('SELECT id FROM operadores ORDER BY id')]
            maquinas = [r[0] for r in conn.execute('SELECT id FROM maquinas ORDER BY id')]
            produtos = [r[0] for r in conn.execute('SELECT id FROM produtos ORDER BY id')]
            hoje = date.today()
            dia = ('Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira',
                   'Sexta-feira', 'Sábado', 'Domingo')[hoje.weekday()]
            for turno in (1, 2, 3):
                prog = conn.execute('INSERT INTO programacoes (data,turno,dia_semana) VALUES (?,?,?)',
                                    (hoje.isoformat(), turno, dia)).lastrowid
                for i, maquina in enumerate(maquinas):
                    conn.execute('''INSERT INTO alocacoes
                        (programacao_id,maquina_id,operador_id,produto_id,num_op,observacao)
                        VALUES (?,?,?,?,?,?)''',
                        (prog, maquina, operadores[i], produtos[i % 3],
                         str(800000+turno*10+i), 'Exemplo fictício'))
                conn.execute('INSERT INTO fora_maquina (programacao_id,operador_id,observacao) VALUES (?,?,?)',
                             (prog, operadores[-1], 'Atividade fictícia'))
        return caminho
    finally:
        db.DB_PATH = anterior


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preparar', action='store_true', help='Cria a base fictícia sem abrir a interface.')
    args = parser.parse_args()
    caminho = Path(__file__).resolve().parent / 'demo' / 'acabamento.db'
    if not caminho.exists():
        preparar_banco(caminho)
    else:
        with closing(db.sqlite3.connect(caminho.as_uri()+'?mode=ro', uri=True)) as conn:
            try:
                valido = conn.execute('SELECT somente_dados_ficticios FROM demonstracao').fetchone()
            except db.sqlite3.Error:
                valido = None
        if valido != (1,):
            raise RuntimeError('O arquivo existente não é uma base de demonstração. Ele foi preservado.')
    if args.preparar:
        print('Base fictícia disponível em demo/acabamento.db. A base de trabalho foi preservada.')
        return
    db.DB_PATH = str(caminho)
    from main import TelaLogin
    TelaLogin().mainloop()


if __name__ == '__main__':
    main()
