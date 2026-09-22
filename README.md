# Sistema de Programação de Acabamento

Aplicação desktop para programar operadores, produtos e máquinas de acabamento.

## Instalação e execução

Instale Python 3.10 ou superior, incluindo Tcl/Tk (instalação padrão do Python para Windows).
Na pasta do projeto:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Uma base vazia recebe o usuário `admin` com senha `admin123`. Altere a senha no cadastro de usuários.
As senhas de bases antigas continuam funcionando e são migradas para PBKDF2 no login válido.

## Demonstração com dados fictícios

```powershell
python demonstracao.py
```

Esse comando abre o sistema usando exclusivamente `demo/acabamento.db`, criado do zero.
Todos os funcionários se chamam **John Doe**, com crachás fictícios `900001` a `900005`.
Produtos, máquinas, ordens de produção e observações também são fictícios.
O acesso inicial de demonstração é `admin` / `admin123`.
Para apenas preparar a base sem abrir a janela, use `python demonstracao.py --preparar`.

A demonstração não lê nem modifica a base de trabalho. Para abrir seus dados locais, continue usando `python main.py`.
Bases novas recebem quatro máquinas fictícias; bases com máquinas cadastradas mantêm seus registros.

## Importação

Acesse **Importar XLS**, selecione o arquivo e inicie a importação. Consulte o relatório completo ao final.
São aceitos `.xlsx`, `.xlsm` e `.xls` (este último exige `xlrd`, incluído em requirements.txt).

O importador atende ao seguinte modelo:

- `Plan2 (2)` ou `Plan2`: crachá/nome em C:D; código/descrição de produto em F:G.
- Abas `1º Turno`, `2º Turno`, `3º Turno`, com ou sem sufixos, e `Domingo`.
- Data em M2; turno em N2. Nos nomes que incluem o número do turno, o nome tem prioridade e divergências são avisadas. Domingo usa N2.
- Cabeçalhos de máquinas em B5 e I5; dados à esquerda em B:G e à direita em I:N.
- Células mescladas de máquina/produto/OP são expandidas para ler operadores adicionais.
- A seção fora de máquina começa após o título em C. Crachá em C (ou B, quando C estiver vazio), nome em D e observação em E.

A data nunca é substituída pela data atual. Datas inválidas impedem a importação daquela aba.
Nome de aba indicando sábado/domingo em desacordo com a data gera aviso; prevalece a data de M2.
Campos com erros de fórmula podem ser recuperados pelo cadastro auxiliar. Quando um código não está cadastrado e seu nome/descrição está ausente, a linha é rejeitada e identificada no relatório.

A importação é **aditiva**: preserva cadastros e alocações existentes. Repetir registros idênticos não os duplica.
Uma linha alterada constitui um novo registro; use a edição da programação para substituir ou remover alocações antigas.
Os contadores representam registros novos. Erros de uma linha revertem aquela linha; falhas fatais de arquivo/banco revertem toda a importação.

## Banco e executável

Rodando `main.py`, o banco `acabamento.db` fica na pasta do código.
No executável, fica ao lado do `.exe`, fora da pasta temporária do PyInstaller. Use uma pasta com permissão de gravação.
Não coloque uma base existente no pacote `--onefile`.

Para atualizar o executável:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --clean main.spec
```

O resultado será `dist/main.exe`. Executáveis anteriores não são atualizados pela edição do código.
Para usar a mesma base com o executável, feche o sistema, faça uma cópia de segurança e copie `acabamento.db` para a pasta do novo `.exe`.
Não sobrescreva outra base sem verificar qual contém seus dados.

## Testes

```powershell
python -m unittest discover -s tests -v
```

Os testes usam bases temporárias e uma planilha inteiramente fictícia gerada por `tests/dados_ficticios.py`.
Não precisam de planilhas ou bancos da empresa. Os testes de interface abrem janelas ocultas e exigem Tcl/Tk.
Não alteram o banco de produção.

Erros de interface executados pelo programa são registrados em `sistema.log`.

## Publicação

Publique os arquivos de código, os testes fictícios e esta documentação.
O `.gitignore` exclui bancos, planilhas, logs, backups, executáveis e relatórios internos.
Dados reais continuam apenas no ambiente local e não fazem parte da demonstração.
Revise `git diff --cached` antes de cada commit: arquivos ignorados ainda podem ser adicionados à força,
e o `.gitignore` não remove dados de commits anteriores.
