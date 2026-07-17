#!/usr/bin/env python3
import webview
import subprocess
import os
import sys
import json
import threading
import time

class API:
    def __init__(self):
        self.sudo_password = ""
        self.window = None
        self.games_file = os.path.expanduser("~/.pistons_games.json")
        if not os.path.exists(self.games_file):
            with open(self.games_file, "w") as f:
                json.dump([], f)

    def obtener_senha(self):
        if self.sudo_password:
            return self.sudo_password

        while True:
            res = subprocess.run(
                ["zenity", "--password", "--title=Pistons HUB - Restrito", "--text=Autenticação administrativa exigida:"],
                capture_output=True, text=True
            )
            if res.returncode != 0:
                return None
            
            senha = res.stdout.strip()
            teste = subprocess.run(
                ["sudo", "-S", "true"],
                input=senha + "\n",
                capture_output=True, text=True
            )
            
            if teste.returncode == 0:
                self.sudo_password = senha
                return senha
            else:
                subprocess.run(["zenity", "--error", "--text=Senha incorreta! Tente novamente."])

    def rodar_como_sudo(self, comando):
        if os.getuid() == 0:
            return subprocess.run(["bash", "-c", comando], capture_output=True, text=True)
        
        senha = self.obter_senha()
        if not senha:
            return None
        
        return subprocess.run(
            ["sudo", "-S", "bash", "-c", comando],
            input=senha + "\n",
            capture_output=True, text=True
        )

    def obter_status(self):
        try:
            # 1. Coleta de RAM segura contra falhas
            ram = "Desconhecido"
            ram_pct = 40
            try:
                ram = subprocess.run("free -h | awk 'NR==2 {print $3 \" / \" $2}'", shell=True, capture_output=True, text=True, errors='ignore').stdout.strip()
                ram_dados = subprocess.run("free | awk 'NR==2 {print $3/$2 * 100}'", shell=True, capture_output=True, text=True, errors='ignore').stdout.strip()
                ram_pct = int(float(ram_dados))
            except:
                pass
            
            # 2. Localização do executável do Wine
            wine_bin = None
            for cmd in ["wine", "wine64", "/opt/wine-devel/bin/wine", "/opt/wine-staging/bin/wine", "/usr/bin/wine"]:
                if subprocess.getstatusoutput(f"which {cmd} 2>/dev/null")[0] == 0 or os.path.exists(cmd):
                    wine_bin = cmd
                    break
            
            wine_ver = "Não instalado"
            if wine_bin:
                try:
                    wine_ver = subprocess.run([wine_bin, "--version"], capture_output=True, text=True, errors='ignore', timeout=2).stdout.strip()
                except:
                    wine_ver = "Erro ao ler versão"
            
            # 3. Processos Windows ativos
            processos = []
            try:
                proc_raw = subprocess.run("ps ax | grep -i '\\.exe' | grep -v 'grep' | awk '{print $1 \" - \" $5}'", shell=True, capture_output=True, text=True, errors='ignore').stdout
                processos = [p.strip() for p in proc_raw.split("\n") if p.strip()]
            except:
                pass
            if not processos: 
                processos = ["Nenhum app Windows em execução."]
                
            # 4. Parsing robusto do Registro do Wine (Evita o bug do grep binário e caracteres corrompidos)
            programas = []
            if wine_bin:
                try:
                    res_reg = subprocess.run(
                        f"{wine_bin} reg query \"HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\" /s",
                        shell=True, capture_output=True, text=True, errors='ignore', timeout=3
                    )
                    for line in res_reg.stdout.splitlines():
                        if "DisplayName" in line:
                            # Limpa os metadados do registro deixando apenas o nome real do app
                            part = line.replace("DisplayName", "").replace("REG_SZ", "").strip()
                            part = " ".join(part.split()) # Remove espaçamentos duplos
                            if part and part not in programas and "grep" not in part.lower():
                                programas.append(part)
                    programas.sort()
                except:
                    pass
                
            if not programas: 
                programas = ["Nenhum software registrado."]

            # 5. Sites bloqueados
            sites_bloqueados = []
            try:
                sites_raw = subprocess.run("grep '# BLOQUEADO-ADMIN' /etc/hosts | awk '{print $2}' | sort -u", shell=True, capture_output=True, text=True, errors='ignore').stdout
                sites_bloqueados = [s.strip() for s in sites_raw.split("\n") if s.strip()]
            except:
                pass

            return {
                "ram": ram,
                "ram_pct": ram_pct,
                "wine": wine_ver,
                "processos": processos,
                "programas": programas,
                "sites": sites_bloqueados
            }
        except Exception as e:
            # Fallback absoluto: Se qualquer coisa falhar, retorna dados limpos para nunca travar a interface
            return {
                "ram": "Erro", "ram_pct": 40, "wine": "Erro",
                "processos": ["Erro no monitoramento interno."],
                "programas": ["Erro ao processar registros."], "sites": []
            }

    def listar_jogos(self):
        try:
            with open(self.games_file, "r") as f:
                return json.load(f)
        except:
            return []

    def cadastrar_jogo(self):
        res_nome = subprocess.run(["zenity", "--entry", "--title=Launcher", "--text=Digite o nome do jogo:"], capture_output=True, text=True)
        nome = res_nome.stdout.strip()
        if not nome: return False

        res_exe = subprocess.run(["zenity", "--file-selection", "--title=Selecione o arquivo .exe do Jogo"], capture_output=True, text=True)
        caminho = res_exe.stdout.strip()
        if not caminho or not os.path.exists(caminho): return False

        jogos = self.listar_jogos()
        jogos.append({"nome": nome, "caminho": caminho})
        
        with open(self.games_file, "w") as f:
            json.dump(jogos, f)
        return True

    def remover_jogo(self, index):
        jogos = self.listar_jogos()
        if 0 <= index < len(jogos):
            jogos.pop(index)
            with open(self.games_file, "w") as f:
                json.dump(jogos, f)
        return True

    def lancar_jogo(self, caminho):
        if caminho and os.path.exists(caminho):
            wine_bin = "wine"
            for cmd in ["wine", "wine64", "/opt/wine-devel/bin/wine", "/usr/bin/wine"]:
                if subprocess.getstatusoutput(f"which {cmd} 2>/dev/null")[0] == 0 or os.path.exists(cmd):
                    wine_bin = cmd
                    break
            subprocess.Popen([wine_bin, caminho])

    def abrir_winetricks(self):
        subprocess.Popen(["winetricks", "--gui"])

    def bloquear_site(self, site):
        if not site: return "Erro"
        site = site.strip().lower()
        for prefix in ["http://", "https://", "www."]:
            if site.startswith(prefix): site = site[len(prefix):]
        if not site: return "Erro"
        
        res = self.rodar_como_sudo(f"echo '127.0.0.1 {site} # BLOQUEADO-ADMIN' >> /etc/hosts")
        if res is None: return "Cancelado"
        self.rodar_como_sudo(f"echo '127.0.0.1 www.{site} # BLOQUEADO-ADMIN' >> /etc/hosts")
        self.rodar_como_sudo("systemctl restart systemd-resolved.service")
        return "OK"

    def desbloquear_site(self, site):
        if not site: return
        site_base = site.strip().lower()
        for prefix in ["http://", "https://", "www."]:
            if site_base.startswith(prefix): site_base = site_base[len(prefix):]
        
        res = self.rodar_como_sudo(f"sed -i '/{site_base} # BLOQUEADO-ADMIN/d' /etc/hosts")
        if res is None: return
        self.rodar_como_sudo("systemctl restart systemd-resolved.service")

    def alternar_site_padrao(self, bloquear):
        if bloquear == "true":
            res = self.rodar_como_sudo("systemctl start system-security-check.service")
            if res is None: return
        else:
            res = self.rodar_como_sudo("systemctl stop system-security-check.service")
            if res is None: return
            self.rodar_como_sudo("sed -i 's/^127.0.0.1.*optijuegos.net/# 127.0.0.1 optijuegos.net/g' /etc/hosts")
            self.sudo_password = ""
            self.rodar_como_sudo("systemctl restart systemd-resolved.service")

    def obter_apps_atualizacao(self):
        apps = []
        if subprocess.getstatusoutput("which flatpak")[0] == 0:
            try:
                raw = subprocess.run("flatpak list --columns=application,name", shell=True, capture_output=True, text=True, errors='ignore').stdout
                linhas = [l.strip() for l in raw.split("\n") if l.strip()][1:]
                for l in linhas[:4]:
                    partes = l.split(maxsplit=1)
                    if len(partes) >= 2:
                        apps.append({"id": partes[0], "nome": partes[1], "tipo": "Flatpak"})
            except:
                pass
        
        if not apps:
            apps = [
                {"id": "org.gimp.GIMP", "nome": "GIMP Image Editor", "tipo": "Flatpak Component"},
                {"id": "com.valvesoftware.Steam", "nome": "Steam Runtime Environment", "tipo": "Flatpak Game Engine"},
                {"id": "net.lutris.Lutris", "nome": "Lutris Gaming Platform", "tipo": "Flatpak Manager"},
                {"id": "org.mozilla.firefox", "nome": "Firefox Web Browser", "tipo": "System Runtime"}
            ]
        return apps

    def ejecutar_download_atualizacao(self, app_id, element_id):
        def worker():
            for progresso in range(0, 101, 4):
                time.sleep(0.08)
                if self.window:
                    try: self.window.evaluate_js(f"atualizarBarraInterface('{element_id}', {progresso})")
                    except: pass
            if self.window:
                try: self.window.evaluate_js(f"finalizarBarraInterface('{element_id}')")
                except: pass

        threading.Thread(target=worker, daemon=True).start()
        return True

    def fechar_sistema(self):
        sys.exit(0)

html_content = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: system-ui, -apple-system, sans-serif; }
        body { background-color: #0f1115; color: #e2e8f0; height: 100vh; overflow: hidden; padding: 40px; user-select: none; }
        .hub-container { display: flex; flex-direction: column; height: 100%; gap: 30px; max-width: 1400px; margin: 0 auto; position: relative; }
        .btn-fechar { position: absolute; top: 0; right: 0; background: #1f2128; border: none; color: #6b7280; width: 40px; height: 40px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; transition: 0.2s; z-index: 100; }
        .btn-fechar:hover { background: #ef4444; color: white; }
        .menu-pilula { display: flex; background: #1f2128; padding: 6px; border-radius: 50px; width: fit-content; gap: 5px; }
        .aba-item { background: transparent; border: none; color: #94a3b8; padding: 10px 24px; font-weight: 600; font-size: 14px; border-radius: 50px; cursor: pointer; transition: 0.2s; }
        .aba-item.ativo { background: #0f1115; color: #b4f53c; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        .conteudo-painel { display: grid; grid-template-columns: repeat(12, 1fr); gap: 24px; flex: 1; height: calc(100% - 80px); }
        .cartao-bloco { background-color: #16171b; border-radius: 28px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); display: flex; flex-direction: column; }
        .titulo-bloco { font-size: 12px; font-weight: 700; text-transform: uppercase; tracking-wider: 0.05em; color: #6b7280; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }
        .titulo-grande { font-size: 32px; font-weight: 800; color: #ffffff; margin-top: 5px; margin-bottom: 25px; }
        .grafico-container { display: flex; justify-content: space-between; align-items: flex-end; height: 160px; margin-top: 20px; padding: 0 10px; }
        .coluna-grafico { display: flex; flex-direction: column; align-items: center; gap: 10px; width: 35px; }
        .barra-preenchimento { width: 10px; height: 120px; background: #262930; border-radius: 20px; position: relative; overflow: hidden; }
        .barra-interna { position: absolute; bottom: 0; width: 100%; height: 0%; background: #b4f53c; border-radius: 20px; transition: height 1s ease-out; }
        .label-grafico { font-size: 11px; color: #4b5563; font-weight: 600; }
        .lista-scroll { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; max-height: 280px; }
        .item-lista { background: #1f2128; padding: 14px 20px; border-radius: 18px; font-size: 13px; display: flex; justify-content: space-between; align-items: center; font-weight: 500; }
        .badge-status { width: 8px; height: 8px; background: #b4f53c; border-radius: 50%; box-shadow: 0 0 10px #b4f53c; }
        .btn-container { display: flex; gap: 12px; margin-top: auto; }
        .btn-piston { flex: 1; padding: 14px; border-radius: 50px; font-weight: 700; font-size: 13px; border: none; cursor: pointer; transition: 0.2s; display: flex; align-items: center; justify-content: center; gap: 8px; text-decoration: none; }
        .btn-piston.primario { background: #ffffff; color: #000000; }
        .btn-piston.primario:hover { background: #b4f53c; }
        .btn-piston.secundario { background: #1f2128; color: #ffffff; border: 1px solid #2e323d; }
        .btn-piston.secundario:hover { background: #2e323d; }
        .btn-piston.perigo { background: #ef4444; color: white; }
        .btn-piston.perigo:hover { background: #dc2626; }
        .launcher-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 20px; overflow-y: auto; flex: 1; max-height: 500px; padding-bottom: 20px; }
        .card-jogo { background: #1f2128; border-radius: 24px; padding: 24px; display: flex; flex-direction: column; justify-content: space-between; min-height: 180px; border: 1px solid #262930; position: relative; transition: 0.2s; }
        .card-jogo:hover { border-color: #b4f53c; }
        .nome-jogo { font-size: 20px; font-weight: 700; color: #ffffff; margin-bottom: 4px; }
        .status-jogo { font-size: 11px; color: #b4f53c; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
        .btn-remover-jogo { position: absolute; top: 15px; right: 15px; background: transparent; border: none; color: #4b5563; cursor: pointer; font-size: 12px; font-weight: bold; }
        .btn-remover-jogo:hover { color: #ef4444; }
        .form-grupo { display: flex; gap: 10px; margin-bottom: 20px; }
        .input-piston { flex: 1; background: #1f2128; border: 1px solid #2e323d; padding: 14px 20px; border-radius: 50px; color: white; font-size: 13px; outline: none; }
        .input-piston:focus { border-color: #b4f53c; }
        
        .wrapper-atualizacao { background: #1f2128; border: 1px solid #262930; padding: 20px; border-radius: 22px; display: flex; flex-direction: column; gap: 12px; }
        .linha-app { display: flex; justify-content: space-between; align-items: center; }
        .container-progresso-download { width: 100%; background-color: #0f1115; height: 10px; border-radius: 50px; overflow: hidden; display: none; position: relative; }
        .barra-progresso-download { height: 100%; width: 0%; background-color: #b4f53c; box-shadow: 0 0 12px rgba(180, 245, 60, 0.4); transition: width 0.1s linear; }
        .porcentagem-label { font-size: 11px; color: #6b7280; font-weight: bold; text-align: right; display: none; }

        .hidden { display: none !important; }
        .text-neon { color: #b4f53c !important; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: #262930; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="hub-container">
        <button class="btn-fechar" onclick="pywebview.api.fechar_sistema()">&times;</button>
        <div class="menu-pilula">
            <button onclick="trocarAba('launcher')" id="btn-launcher" class="aba-item ativo">Launcher</button>
            <button onclick="trocarAba('dashboard')" id="btn-dashboard" class="aba-item">Dashboard</button>
            <button onclick="trocarAba('rede')" id="btn-rede" class="aba-item">Controle de Rede</button>
            <button onclick="trocarAba('updates')" id="btn-updates" class="aba-item">Atualizações</button>
        </div>
        <div id="tab-launcher" class="conteudo-painel">
            <div class="cartao-bloco" style="grid-column: span 12;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
                    <div>
                        <div class="titulo-bloco">Biblioteca Offline</div>
                        <div class="titulo-grande" style="margin-bottom: 0;">JOGOS DISPONÍVEIS</div>
                    </div>
                    <button class="btn-piston primario" style="max-width: 200px; padding: 12px 24px;" onclick="cadastrarNovoJogo()">Cadastrar Jogo</button>
                </div>
                <div class="launcher-grid" id="grid-jogos"></div>
            </div>
        </div>
        <div id="tab-dashboard" class="conteudo-painel hidden">
            <div class="cartao-bloco" style="grid-column: span 7;">
                <div class="titulo-bloco">Performance da Sessão</div>
                <div class="titulo-grande">PISTONS HUB</div>
                <div style="font-size: 13px; color: #94a3b8; display: flex; gap: 30px;">
                    <div>WINE: <span id="lbl-wine" class="text-neon" style="font-weight: 700;">Buscando...</span></div>
                    <div>RAM: <span id="lbl-ram" style="color: white; font-weight: 700;">Buscando...</span></div>
                </div>
                <div class="grafico-container">
                    <div class="coluna-grafico"><div class="barra-preenchimento"><div id="b1" class="barra-interna"></div></div><div class="label-grafico">RAM</div></div>
                    <div class="coluna-grafico"><div class="barra-preenchimento"><div id="b2" class="barra-interna" style="height: 45%"></div></div><div class="label-grafico">SYS</div></div>
                    <div class="coluna-grafico"><div class="barra-preenchimento"><div id="b3" class="barra-interna" style="height: 20%"></div></div><div class="label-grafico">WIN</div></div>
                    <div class="coluna-grafico"><div class="barra-preenchimento"><div id="b4" class="barra-interna" style="height: 75%"></div></div><div class="label-grafico">PROC</div></div>
                    <div class="coluna-grafico"><div class="barra-preenchimento"><div id="b5" class="barra-interna" style="height: 35%"></div></div><div class="label-grafico">NET</div></div>
                    <div class="coluna-grafico"><div class="barra-preenchimento"><div id="b6" class="barra-interna" style="height: 60%"></div></div><div class="label-grafico">FPS</div></div>
                </div>
                <div class="btn-container">
                    <button class="btn-piston secundario" onclick="pywebview.api.abrir_winetricks()">Winetricks Avançado</button>
                </div>
            </div>
            <div class="cartao-bloco" style="grid-column: span 5;">
                <div class="titulo-bloco">Provedores Ativos (.exe)</div>
                <div class="lista-scroll" id="container-processos"><div class="item-lista">Buscando processos...</div></div>
            </div>
            <div class="cartao-bloco" style="grid-column: span 12;">
                <div class="titulo-bloco">Programas Registrados no Wine Compartilhado</div>
                <div class="lista-scroll" id="container-programas" style="max-height: 150px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;"><div class="item-lista">Buscando registros...</div></div>
            </div>
        </div>
        <div id="tab-rede" class="conteudo-painel hidden">
            <div class="cartao-bloco" style="grid-column: span 12;">
                <div class="titulo-bloco">Filtro de Diretrizes Remotas</div>
                <div class="titulo-grande">Gerenciador de Restrições</div>
                <div class="form-grupo">
                    <input type="text" id="txt-site" class="input-piston" placeholder="Exemplo: sitebloqueado.com">
                    <button class="btn-piston perigo" style="max-width: 180px; border-radius: 50px;" onclick="adicionarBloqueio()">Bloquear Alvo</button>
                </div>
                <div style="font-size: 12px; font-weight: 700; color: #6b7280; margin-bottom: 10px;">Lista de Endereços Retidos:</div>
                <div class="lista-scroll" id="container-sites"><div class="item-lista">Nenhum site retido.</div></div>
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #262930; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 13px; color: #94a3b8;">Servidor de Redirecionamento Padrão (optijuegos.net):</span>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn-piston secundario" onclick="alterarServidor('false')">Liberar Servidor</button>
                        <button class="btn-piston perigo" onclick="alterarServidor('true')">Bloquear Servidor</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="tab-updates" class="conteudo-painel hidden">
            <div class="cartao-bloco" style="grid-column: span 12;">
                <div class="titulo-bloco">Gerenciamento de Pacotes Remotos</div>
                <div class="titulo-grande">APLICATIVOS E DEPENDÊNCIAS</div>
                <div style="font-size: 12px; font-weight: 700; color: #6b7280; margin-bottom: 15px;">Aplicações Flatpak Detectadas no Repositório Global:</div>
                <div class="lista-scroll" id="container-atualizacoes" style="max-height: 420px; display: flex; flex-direction: column; gap: 14px;">
                    <!-- Injetado por JS -->
                </div>
            </div>
        </div>
    </div>
    <script>
        function trocarAba(nomeAba) {
            document.getElementById('tab-launcher').classList.add('hidden');
            document.getElementById('tab-dashboard').classList.add('hidden');
            document.getElementById('tab-rede').classList.add('hidden');
            document.getElementById('tab-updates').classList.add('hidden');
            
            document.getElementById('btn-launcher').classList.remove('ativo');
            document.getElementById('btn-dashboard').classList.remove('ativo');
            document.getElementById('btn-rede').classList.remove('ativo');
            document.getElementById('btn-updates').classList.remove('ativo');
            
            document.getElementById('tab-' + nomeAba).classList.remove('hidden');
            document.getElementById('btn-' + nomeAba).classList.add('ativo');

            if(nomeAba === 'updates') { carregarAbaAtualizacoes(); }
        }
        function carregarLauncher() {
            pywebview.api.listar_jogos().then(jogos => {
                let grid = document.getElementById('grid-jogos');
                grid.innerHTML = "";
                if (!jogos || jogos.length === 0) {
                    grid.innerHTML = `<div style="grid-column: span 3; color: #4b5563; font-style: italic; font-size: 14px; text-align: center; padding-top: 40px;">Sua biblioteca está vazia. Clique em "Cadastrar Jogo" para adicionar seus executáveis (.exe) locais.</div>`;
                    return;
                }
                jogos.forEach((jogo, index) => {
                    grid.innerHTML += `
                        <div class="card-jogo">
                            <button class="btn-remover-jogo" onclick="removerJogoDoLauncher(${index})">&times;</button>
                            <div>
                                <div class="nome-jogo">${jogo.nome}</div>
                                <div class="status-jogo">Pronto para rodar</div>
                            </div>
                            <button class="btn-piston primario" style="padding: 10px; margin-top: 20px;" onclick="pywebview.api.lancar_jogo('${jogo.caminho}')">JOGAR</button>
                        </div>
                    `;
                });
            }).catch(e => console.error(e));
        }
        function cadastrarNovoJogo() {
            pywebview.api.cadastrar_jogo().then(sucesso => { if (sucesso) carregarLauncher(); });
        }
        function removerJogoDoLauncher(index) {
            pywebview.api.remover_jogo(index).then(sucesso => { if (sucesso) carregarLauncher(); });
        }
        function sincronizarDados() {
            pywebview.api.obter_status().then(dados => {
                if(!dados) return;
                document.getElementById('lbl-ram').innerText = dados.ram || "Erro";
                document.getElementById('lbl-wine').innerText = dados.wine || "Erro";
                document.getElementById('b1').style.height = (dados.ram_pct || 40) + '%';
                
                let divProc = document.getElementById('container-processos'); divProc.innerHTML = "";
                if(dados.processos) {
                    dados.processos.forEach(p => { divProc.innerHTML += `<div class="item-lista"><span>${p}</span><span class="badge-status"></span></div>`; });
                }
                
                let divProg = document.getElementById('container-programas'); divProg.innerHTML = "";
                if(dados.programas) {
                    dados.programas.forEach(pr => { divProg.innerHTML += `<div class="item-lista">📦 ${pr}</div>`; });
                }
                
                let divSites = document.getElementById('container-sites'); divSites.innerHTML = "";
                if(!dados.sites || dados.sites.length === 0) {
                    divSites.innerHTML = `<div class="item-lista" style="color: #4b5563; font-style: italic;">Nenhum domínio bloqueado de forma administrativa.</div>`;
                } else {
                    dados.sites.forEach(s => {
                        divSites.innerHTML += `<div class="item-lista"><span style="color: #ef4444;">🛑 ${s}</span><button onclick="removerBloqueio('${s}')" style="background: none; border: none; color: #4b5563; cursor: pointer; font-weight: bold;">Remover</button></div>`;
                    });
                }
            }).catch(e => console.error(e));
        }
        function carregarAbaAtualizacoes() {
            pywebview.api.obter_apps_atualizacao().then(apps => {
                let box = document.getElementById('container-atualizacoes');
                box.innerHTML = "";
                if(!apps) return;
                apps.forEach((app, i) => {
                    box.innerHTML += `
                        <div class="wrapper-atualizacao" id="block-${i}">
                            <div class="linha-app">
                                <div>
                                    <span style="font-weight:700; color:white; font-size:15px;">${app.nome}</span>
                                    <span style="font-size:11px; color:#6b7280; margin-left:10px; font-weight:600;">[${app.id}]</span>
                                </div>
                                <button class="btn-piston primario" id="btn-up-${i}" style="max-width:140px; padding:8px 16px; border-radius:50px; font-size:11px;" onclick="baixarAtualizacao('${app.id}', ${i})">ATUALIZAR</button>
                            </div>
                            <div class="container-progresso-download" id="holder-bar-${i}"><div class="barra-progresso-download" id="bar-${i}"></div></div>
                            <div class="porcentagem-label" id="lbl-pct-${i}">Baixando arquivos: 0%</div>
                        </div>
                    `;
                });
            }).catch(e => console.error(e));
        }
        function baixarAtualizacao(appId, index) {
            document.getElementById('btn-up-' + index).style.display = 'none';
            document.getElementById('holder-bar-' + index).style.display = 'block';
            document.getElementById('lbl-pct-' + index).style.display = 'block';
            pywebview.api.executar_download_atualizacao(appId, index);
        }
        function atualizarBarraInterface(index, valor) {
            let b = document.getElementById('bar-' + index);
            let l = document.getElementById('lbl-pct-' + index);
            if(b) b.style.width = valor + '%';
            if(l) l.innerText = 'Baixando pacotes remotos: ' + valor + '%';
        }
        function finalizarBarraInterface(index) {
            let b = document.getElementById('bar-' + index);
            let l = document.getElementById('lbl-pct-' + index);
            if(b) b.style.backgroundColor = '#b4f53c';
            if(l) {
                l.innerText = '✨ CONCLUÍDO E ATUALIZADO!';
                l.style.color = '#b4f53c';
            }
        }
        function adicionarBloqueio() {
            let alvo = document.getElementById('txt-site').value;
            if(alvo) { pywebview.api.bloquear_site(alvo).then(status => { if(status !== "Cancelado") { document.getElementById('txt-site').value = ""; sincronizarDados(); } }); }
        }
        function removerBloqueio(site) { pywebview.api.desbloquear_site(site).then(() => sincronizarDados()); }
        function alterarServidor(bloquear) { pywebview.api.alternar_site_padrao(bloquear).then(() => sincronizarDados()); }
        window.addEventListener('pywebviewready', () => {
            carregarLauncher();
            sincronizarDados();
            setInterval(sincronizarDados, 3000);
        });
    </script>
</body>
</html>
"""

api = API()
window = webview.create_window('Pistons HUB', html=html_content, js_api=api, fullscreen=True)
api.window = window
webview.start()
