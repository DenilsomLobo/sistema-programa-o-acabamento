"""Smoke tests reais do Tk em janela oculta, com base temporária."""
import importlib.util
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import database as db


@unittest.skipUnless(importlib.util.find_spec('customtkinter'), 'CustomTkinter não instalado')
class Interface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import main
        cls.main = main
        cls.temp = tempfile.TemporaryDirectory()
        cls.antigo = db.DB_PATH
        db.DB_PATH = str(Path(cls.temp.name) / 'interface.db')
        db.inicializar_banco()
        main.usuario_atual.update(db.autenticar('admin', 'admin123'))
        try:
            cls.app = main.App()
            cls.app.withdraw()
        except Exception:
            db.DB_PATH = cls.antigo
            cls.temp.cleanup()
            raise
        cls.erros = []
        cls.app.report_callback_exception = lambda *args: cls.erros.append(str(args[1]))

    @classmethod
    def tearDownClass(cls):
        cls.app.destroy()
        db.DB_PATH = cls.antigo
        cls.temp.cleanup()

    def test_telas_e_dialogos(self):
        for tela in ('programacoes','visao_geral','turno_atual','operadores','produtos','maquinas','usuarios','importar'):
            with self.subTest(tela=tela):
                self.app._ir(tela)
                self.app.update_idletasks()
        for nome in ('DlgEditProg','DlgOp','DlgProd','DlgMaq','DlgUser'):
            with self.subTest(dialogo=nome):
                dlg = getattr(self.main, nome)(self.app)
                dlg.withdraw()
                dlg.update_idletasks()
                dlg.destroy()
        self.assertFalse(self.erros)

    def test_importacao_interface_reabilita_apos_falha(self):
        self.app._ir('importar')
        tela = self.app.telas['importar']
        tela.caminho = 'arquivo_inexistente.xlsx'
        tela._imp()
        limite = time.monotonic()+10
        while tela._importando and time.monotonic() < limite:
            self.app.update()
            time.sleep(0.02)
        self.assertFalse(tela._importando)
        self.assertEqual(tela.bimp.cget('state'), 'normal')
        self.assertIn('pendências', tela.lst.cget('text'))
        self.assertIn('nenhuma alteração', tela.txt.get('1.0', 'end'))
        self.assertFalse(self.erros)

    def test_observacao_alocacao_preservada_na_edicao(self):
        prog = db.criar_programacao('2026-09-22', 1, '')
        db.salvar_alocacao(prog, db.listar_maquinas()[0]['id'], None, None, '10', 'Não apagar')
        aloc = db.listar_alocacoes(prog)[0]
        dlg = self.main.DlgAloc(self.app, prog, aloc_id=aloc['id'])
        dlg.withdraw()
        self.assertEqual(dlg.eobs.get(), 'Não apagar')
        dlg._salvar()
        self.assertEqual(db.listar_alocacoes(prog)[0]['observacao'], 'Não apagar')

    def test_operador_nao_pode_abrir_administracao(self):
        self.main.usuario_atual['nivel'] = 'operador'
        try:
            with patch.object(self.main.messagebox, 'showwarning') as aviso:
                self.app._ir('usuarios')
                self.assertTrue(aviso.called)
        finally:
            self.main.usuario_atual['nivel'] = 'supervisor'

if __name__ == '__main__':
    unittest.main()
