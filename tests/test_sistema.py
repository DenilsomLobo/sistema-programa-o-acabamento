"""Regressões: sempre usam SQLite temporário, nunca acabamento.db de produção."""
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import runpy
import sys
import unittest
from unittest.mock import patch
from contextlib import closing
from datetime import datetime
import pandas as pd
import database as db
import importar as imp


class BancoFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.antigo = db.DB_PATH
        db.DB_PATH = str(Path(self.temp.name) / 'teste.db')
        db.inicializar_banco()

    def tearDown(self):
        db.DB_PATH = self.antigo
        self.temp.cleanup()

class BancoTemporario(BancoFixture):
    def test_atualizar_cadastros_preserva_ids_e_alocacoes(self):
        db.salvar_operador('007', 'John Doe')
        db.salvar_produto('p-001', 'Produto')
        op = db.buscar_operador_por_cracha('007')['id']
        prod = db.buscar_produto_por_codigo('P-001')['id']
        prog = db.criar_programacao('2026-04-13', 1, 'Sexta-feira')
        db.salvar_alocacao(prog, db.listar_maquinas()[0]['id'], op, prod, '001')
        db.salvar_operador('007', 'John Doe')
        db.salvar_produto('P-001', 'Descrição corrigida')
        self.assertEqual(db.buscar_operador_por_cracha('007')['id'], op)
        self.assertEqual(db.buscar_produto_por_codigo('p-001')['id'], prod)
        self.assertEqual(db.listar_alocacoes(prog)[0]['operador'], 'JOHN DOE')
        self.assertEqual(len(db.listar_produtos()), 1)

    def test_erro_nao_mantem_banco_bloqueado(self):
        db.salvar_operador('1', 'John Doe')
        db.salvar_operador('2', 'John Doe')
        with self.assertRaises(sqlite3.IntegrityError):
            db.salvar_operador('1', 'John Doe', op_id=db.buscar_operador_por_cracha('2')['id'])
        db.salvar_operador('3', 'John Doe')
        self.assertEqual(len(db.listar_operadores()), 3)

    def test_programacao_impede_duplicata_e_corrige_dia(self):
        p = db.criar_programacao('2026-04-13', 1, 'Sexta-feira')
        self.assertEqual(db.buscar_programacao('2026-04-13', 1)['dia_semana'], 'Segunda-feira')
        with self.assertRaises(ValueError):
            db.criar_programacao('2026-04-13', 1, '')
        outra = db.criar_programacao('2026-04-14', 1, '')
        with self.assertRaises(ValueError):
            db.atualizar_programacao(outra, '2026-04-13', 1, '')
        self.assertEqual(len(db.listar_programacoes()), 2)
        db.atualizar_programacao(p, '2026-04-13', 1, '')

    def test_excluir_programacao_remove_vinculos(self):
        db.salvar_operador('1', 'John Doe')
        op = db.buscar_operador_por_cracha('1')['id']
        prog = db.criar_programacao('2026-04-13', 1, '')
        db.salvar_fora_maquina(prog, op)
        db.salvar_alocacao(prog, db.listar_maquinas()[0]['id'], op, None, '')
        db.deletar_programacao(prog)
        self.assertFalse(db.listar_alocacoes(prog))
        self.assertFalse(db.listar_fora_maquina(prog))

    def test_fora_maquina_exige_operador(self):
        with self.assertRaises(ValueError):
            db.salvar_fora_maquina(1, None)

    def test_senha_legada_migra_sem_alterar_acesso(self):
        with closing(db.get_conn()) as c, c:
            c.execute('UPDATE usuarios SET senha_hash=?', (hashlib.sha256(b'antiga').hexdigest(),))
        self.assertIsNone(db.autenticar('admin', 'errada'))
        self.assertNotIn('senha_hash', db.autenticar('admin', 'antiga'))
        with closing(db.get_conn()) as c:
            self.assertTrue(c.execute('SELECT senha_hash FROM usuarios').fetchone()[0].startswith('pbkdf2_sha256$'))
        self.assertIsNotNone(db.autenticar('admin', 'antiga'))

    def test_ultimo_supervisor_protegido(self):
        uid = db.listar_usuarios()[0]['id']
        with self.assertRaises(ValueError):
            db.salvar_usuario('admin', '', 'John Doe', 'operador', uid)
        with self.assertRaises(ValueError):
            db.deletar_usuario(uid)
        self.assertIsNotNone(db.autenticar('admin', 'admin123'))

    def test_renomear_admin_nao_recria_senha_padrao(self):
        uid = db.listar_usuarios()[0]['id']
        db.salvar_usuario('gestor', '', 'John Doe', 'supervisor', uid)
        db.inicializar_banco()
        self.assertEqual([u['login'] for u in db.listar_usuarios()], ['gestor'])

    def test_nivel_usuario_invalido(self):
        with self.assertRaises(ValueError):
            db.salvar_usuario('x', 'x', 'John Doe', 'qualquer')

    def test_maquina_duplicada_nao_finge_sucesso(self):
        with self.assertRaises(sqlite3.IntegrityError):
            db.salvar_maquina('PCT900001', 'Picote')

    def test_falha_de_arquivo_retorna_contagens(self):
        r = imp.importar_planilha(Path(self.temp.name) / 'ausente.xlsx')
        self.assertEqual(r['alocacoes'], 0)
        self.assertTrue(r['erros'])
        self.assertFalse(db.listar_programacoes())

    def test_rollback_de_linha_preserva_contadores(self):
        r = imp.novo_resultado()
        with closing(db.get_conn()) as c, c:
            c.execute('BEGIN IMMEDIATE')
            def falhar():
                imp._operador(c, '123', 'John Doe', r)
                raise ValueError('Falha de produto')
            imp._tentar(c, r, 'Teste', falhar)
        self.assertEqual(r['operadores'], 0)
        self.assertIsNone(db.buscar_operador_por_cracha('123'))
        self.assertTrue(r['erros'])

    def test_produto_antigo_com_caixa_diferente_nao_duplica_alocacao(self):
        with closing(db.get_conn()) as c, c:
            c.execute("INSERT INTO produtos(codigo,descricao) VALUES ('p-1','Antigo')")
            antigo = c.execute('SELECT id FROM produtos').fetchone()[0]
            c.execute("INSERT INTO produtos(codigo,descricao) VALUES ('P-1','John Doe')")
        prog = db.criar_programacao('2026-04-13', 1, '')
        maquina = next(m['id'] for m in db.listar_maquinas() if m['codigo'] == 'PCT900001')
        db.salvar_alocacao(prog, maquina, None, antigo, '7')
        df = pd.DataFrame([[None, 'PCT900001', None, None, 'P-1', 'Produto', 7]])
        df.attrs['linhas_com_dados'] = {1: {0}}
        r = imp.novo_resultado()
        with closing(db.get_conn()) as c, c:
            imp._linha(c, df, 0, 1, prog, r)
        self.assertEqual(len(db.listar_alocacoes(prog)), 1)
        self.assertEqual(r['ignorados'], 1)
        self.assertTrue(r['avisos'])


class Conversoes(unittest.TestCase):
    def test_banco_empacotado_fica_ao_lado_do_executavel(self):
        with tempfile.TemporaryDirectory() as pasta:
            executavel = str(Path(pasta) / 'programa.exe')
            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'executable', executavel):
                modulo = runpy.run_path(db.__file__)
            self.assertEqual(Path(modulo['DB_PATH']), Path(pasta) / 'acabamento.db')

    def test_identificadores_sem_perda(self):
        for valor, esperado in [('0012', '0012'), (12.0, '12'), ('12,0', '12'),
                                 ('9007199254740993', '9007199254740993'),
                                 (12.9, None), (float('inf'), None), (float('nan'), None), ('#N/A', None)]:
            with self.subTest(valor=valor):
                self.assertEqual(imp._safe_float_str(valor), esperado)

    def test_datas_brasileiras_e_excel(self):
        self.assertEqual(imp._data('04/05/2026'), '2026-05-04')
        self.assertEqual(imp._data(datetime(2026, 4, 13)), '2026-04-13')
        self.assertEqual(imp._data(46125), '2026-04-13')
        self.assertIsNone(imp._data('Turno 01'))
        self.assertIsNone(imp._data('31/02/2026'))


class PlanilhaFicticia(BancoFixture):
    def setUp(self):
        super().setUp()
        from dados_ficticios import criar_planilha
        self.arquivo = criar_planilha(Path(self.temp.name) / 'exemplo.xlsx')

    def test_importacao_ficticia_repetida(self):
        r = imp.importar_planilha(self.arquivo)
        self.assertEqual(r['alocacoes'], 28, r)
        self.assertEqual(r['programacoes'], 7)
        self.assertEqual(r['fora_maquina'], 7)
        prog = db.buscar_programacao('2024-01-05', 1)
        alocs = db.listar_alocacoes(prog['id'])
        self.assertTrue(any(a['maquina'] == 'PCT900001' and a['cracha'] == '900002' for a in alocs))
        self.assertTrue(any(a['maquina'] == 'LXR900002' and a['cracha'] == '900002' for a in alocs))
        self.assertTrue(all(a['operador'] == 'JOHN DOE' for a in alocs))
        self.assertTrue(all(a['produto_cod'] == a['produto_cod'].upper() for a in alocs))
        self.assertTrue(any('M2' in a for a in r['avisos']))
        self.assertTrue(any('DEMO-AUSENTE' in e for e in r['erros']))
        repetido = imp.importar_planilha(self.arquivo)
        for chave in ('operadores','produtos','programacoes','alocacoes','fora_maquina'):
            self.assertEqual(repetido[chave], 0, repetido)
        with closing(db.get_conn()) as c:
            self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchall())

    def test_falha_fatal_reverte_cadastros(self):
        with patch.object(imp, '_ler_aba', side_effect=RuntimeError('Falha de leitura')):
            r = imp.importar_planilha(self.arquivo)
        self.assertTrue(r['erros'])
        self.assertEqual(r['operadores'], 0)
        self.assertFalse(db.listar_operadores())
        self.assertFalse(db.listar_produtos())

    def test_data_ausente_nao_usa_hoje(self):
        sem_data = pd.DataFrame([[None]*14 for _ in range(5)])
        sem_data.iat[4, 1] = 'M\u00e1quina'
        with patch.object(imp, '_ler_aba', return_value=sem_data):
            r = imp.importar_planilha(self.arquivo)
        self.assertEqual(r['programacoes'], 0)
        self.assertFalse(db.listar_programacoes())
        self.assertEqual(len(r['erros']), 7)
        self.assertTrue(all('M2' in e for e in r['erros']))


if __name__ == '__main__':
    unittest.main()
