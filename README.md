# Sistema de Programação de Acabamento

![Capa do sistema](https://portifolio-denilsom-lobo.web.app/images/projetos/sistema-de-acabamentos.png) 

Aplicação desktop para organizar a programação do setor de acabamento industrial. Centraliza a distribuição de operadores entre máquinas, produtos e ordens de produção (OPs), com consulta por data e turno.

## Para que serve

O sistema apoia o planejamento e o acompanhamento das atividades de acabamento: permite consultar quem está alocado em cada máquina, qual produto será trabalhado e a OP correspondente. Também registra operadores em atividades fora de máquina e importa programações de planilhas Excel no modelo descrito abaixo.

Os dados ficam armazenados localmente em SQLite, sem necessidade de configurar um servidor de banco de dados.

## Funcionalidades

- **Programações:** criação, consulta, filtros, edição de data e turno e exclusão.
- **Alocações:** associação de operadores, máquinas, produtos e OPs, com observações.
- **Visão geral:** consulta por data, com navegação entre os dias.
- **Turno atual:** acompanhamento da programação do turno em andamento.
- **Fora de máquina:** registro de operadores em outras atividades.
- **Cadastros:** manutenção de operadores, produtos e máquinas.
- **Usuários:** autenticação com perfis de supervisor e operador; gestão de usuários e importação disponíveis para supervisores.
- **Importação Excel:** leitura de `.xlsx`, `.xlsm` e `.xls`, com relatório de resultados e pendências.

## Imagens do sistema

A capa e as três imagens de funcionalidades serão adicionadas após o envio. Sugestão de organização:

### 1. Visão geral

Consulta da programação diária e da distribuição dos operadores.

![Visão geral da programação diária](https://portifolio-denilsom-lobo.web.app/images/git_hub_imgs/sistemas-programa-o-acabamento_01.jpeg) -->

### 2. Programações e alocações

Organização das máquinas, operadores, produtos e ordens de produção por turno.

![Programação e alocações por turno](https://portifolio-denilsom-lobo.web.app/images/git_hub_imgs/sistemas-programa-o-acabamento_03.jpeg) 

### 3. Turno atual

Acompanhamento da programação do turno em andamento.

![Painel do turno atual](https://portifolio-denilsom-lobo.web.app/images/git_hub_imgs/sistemas-programa-o-acabamento_02.jpeg)

## Tecnologias utilizadas

| Tecnologia | Uso no projeto |
| --- | --- |
| Python 3.10+ | Linguagem da aplicação |
| CustomTkinter | Interface gráfica desktop |
| Tkinter / ttk | Janelas, tabelas e diálogos |
| SQLite / sqlite3 | Armazenamento local dos dados |
| pandas | Leitura e tratamento de planilhas |
| openpyxl | Suporte a arquivos `.xlsx` e `.xlsm` |
| xlrd | Suporte a arquivos `.xls` |
| hashlib / hmac | Proteção e verificação de senhas com PBKDF2 |
| PyInstaller | Geração opcional do executável Windows |
| unittest | Testes automatizados |

As dependências de execução estão em `requirements.txt`. SQLite, Tkinter, hashlib, hmac e unittest fazem parte da biblioteca padrão do Python; a interface exige Tcl/Tk.

## Instalação e execução

Instale Python 3.10 ou superior, incluindo Tcl/Tk (instalação padrão do Python para Windows).
Baixe ou clone o repositório e abra o PowerShell na pasta que contém `main.py` e `requirements.txt`. Crie um ambiente virtual, instale as dependências e inicie o sistema:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Usar o Python do ambiente virtual diretamente dispensa a ativação. Nos demais comandos deste README, substitua `python` por `.\.venv\Scripts\python.exe` para usar o mesmo ambiente.

### Primeiro acesso

Uma base vazia recebe o usuário `admin` com senha `admin123`. Altere a senha no cadastro de usuários.
As senhas de bases antigas continuam funcionando e são migradas para PBKDF2 no login válido.

## Como usar

1. Entre com seu usuário e senha.
2. Confira ou cadastre operadores, produtos e máquinas com um perfil de supervisor.
3. Em **Programações**, crie uma programação para a data e o turno desejados.
4. Abra as alocações e associe máquina, operador, produto e OP; preencha observações quando necessário.
5. Registre outras atividades em **Fora de Máquina**.
6. Consulte **Visão Geral** e **Turno Atual** para acompanhar a programação.

Para aproveitar uma planilha existente, use **Importar XLS** com um perfil de supervisor e confira o relatório ao final.

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

## Estrutura do projeto

```text
.
├── main.py              # Interface, login e navegação
├── database.py          # Banco SQLite, cadastros e autenticação
├── importar.py          # Importação das planilhas Excel
├── demonstracao.py      # Execução com dados fictícios
├── requirements.txt     # Dependências de execução
├── main.spec            # Configuração do PyInstaller
├── engrenagem.ico       # Ícone do executável
├── tests/               # Testes e dados fictícios
└── README.md            # Apresentação e instruções
```

As imagens da apresentação serão organizadas em `docs/imagens/` após o envio.

## Backup dos dados

Feche o sistema e copie `acabamento.db` para um local seguro. Para restaurar uma cópia, mantenha a aplicação fechada e coloque o banco na pasta usada pela execução, preservando antes o arquivo atual. O banco reúne cadastros, usuários e programações.

## Solução de problemas

| Situação | O que verificar |
| --- | --- |
| Dependência não encontrada | Instale `requirements.txt` com o mesmo Python usado para iniciar o sistema. |
| Falta de Tkinter | Confira se a instalação do Python inclui Tcl/Tk. |
| Banco sem permissão de gravação | Use uma pasta em que seu usuário possa gravar arquivos. |
| Planilha com registros rejeitados | Consulte o relatório e confira o modelo, a data e os cadastros auxiliares. |
| Erro durante o uso da interface | Consulte `sistema.log`. |

**Para conhecer mais projetos meus, acesse meu portfólio pelo link abaixo:**
🔗 https://portifolio-denilsom-lobo.web.app/projetos.html


