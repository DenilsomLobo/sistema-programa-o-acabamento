from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

import database as db
from demonstracao import preparar_banco


class Demonstracao(unittest.TestCase):
    def test_base_ficticia_isolada(self):
        anterior = db.DB_PATH
        with tempfile.TemporaryDirectory() as pasta:
            caminho = preparar_banco(Path(pasta) / 'demo.db')
            self.assertEqual(db.DB_PATH, anterior)
            with closing(sqlite3.connect(caminho)) as conn:
                self.assertEqual(conn.execute('SELECT DISTINCT nome FROM operadores').fetchall(), [('John Doe',)])
                self.assertEqual(conn.execute('SELECT cracha FROM operadores ORDER BY cracha').fetchall(),
                                 [(str(i),) for i in range(900001, 900006)])
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM alocacoes').fetchone()[0], 12)
                self.assertFalse(conn.execute('PRAGMA foreign_key_check').fetchall())

    def test_nao_sobrescreve_arquivo_existente(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / 'existente.db'
            caminho.write_bytes(b'arquivo a preservar')
            with self.assertRaises(FileExistsError):
                preparar_banco(caminho)
            self.assertEqual(caminho.read_bytes(), b'arquivo a preservar')

    def test_inicializacao_preserva_maquinas_existentes(self):
        anterior = db.DB_PATH
        try:
            with tempfile.TemporaryDirectory() as pasta:
                db.DB_PATH = str(Path(pasta) / 'teste.db')
                db.inicializar_banco()
                with closing(db.get_conn()) as conn, conn:
                    conn.execute('DELETE FROM maquinas')
                    conn.execute("INSERT INTO maquinas(codigo,setor) VALUES ('TESTE-LOCAL','Picote')")
                db.inicializar_banco()
                self.assertEqual([m['codigo'] for m in db.listar_maquinas()], ['TESTE-LOCAL'])
        finally:
            db.DB_PATH = anterior
