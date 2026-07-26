# Pistons HUB

Pistons HUB é um gerenciador e launcher desktop para execução e controle de aplicações, ferramentas do sistema e dependências, com suporte a múltiplas linguagens e ambientes Linux/Wine, além de recursos avançados de controle de rede.

---

## Funcionalidades

- **Central de Execução:** Suporte para inicialização de arquivos executáveis e scripts (.exe, .jar, .php).
- **Painel de Performance (Dashboard):** Monitoramento em tempo real de consumo de memória RAM, status da sessão Wine e processos ativos no sistema.
- **Controle de Rede & Filtros:** Gerenciamento administrativo para bloqueio de domínios e redirecionamento de servidores.
- **Gerenciador de Pacotes e Atualizações:** Interface integrada para download e atualização remota de pacotes e dependências (Flatpak) com barra de progresso em tempo real.
- **Autenticação e Perfis:** Modos de acesso para Desenvolvedor (com integração de avatar via GitHub) e Convidado via Token.

---

## Tecnologias Utilizadas

- **Frontend:** HTML5, CSS3, JavaScript (Interface moderna em estilo escuro).
- **Backend / Desktop Integration:** Python 3 + pywebview.
- **Compatibilidade:** Linux / Wine / Winetricks.

---

## Como Executar o Projeto

### Pré-requisitos
Certifique-se de ter o Python 3 e as bibliotecas necessárias instaladas no seu sistema:

```bash
pip install pywebview psutil
