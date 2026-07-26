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

    def obter_senha(self):
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

    # ---------------- AUTENTICAÇÃO E LOGIN ----------------
    def fazer_login(self, usuario, senha):
        u = usuario.strip().lower()
        p = senha.strip()
        
        if u in ["lkm2201", "crawford-guitar"] and p != "":
            return {
                "status": "success",
                "user": {
                    "name": usuario,
                    "avatar": f"https://github.com/{u}.png",
                    "role": "Desenvolvedor"
                }
            }
        return {"status": "error", "message": "Credenciais de desenvolvedor inválidas!"}

    def validar_token(self, token):
        if token.strip() != "":
            return {
                "status": "success",
                "user": {
                    "name": "Convidado",
                    "avatar": "avatar.jpg",
                    "role": "Convidado"
                }
            }
        return {"status": "error", "message": "Token de acesso inválido!"}

    # ---------------- MONITORAMENTO DE SISTEMA ----------------
    def obter_status(self):
        try:
            ram = "Desconhecido"
            ram_pct = 40
            try:
                ram = subprocess.run("free -h | awk 'NR==2 {print $3 \" / \" $2}'", shell=True, capture_output=True, text=True, errors='ignore').stdout.strip()
                ram_dados = subprocess.run("free | awk 'NR==2 {print $3/$2 * 100}'", shell=True, capture_output=True, text=True, errors='ignore').stdout.strip()
                ram_pct = int(float(ram_dados))
            except:
                pass
            
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
            
            processos = []
            try:
                proc_raw = subprocess.run("ps ax | grep -i '\\.exe' | grep -v 'grep' | awk '{print $1 \" - \" $5}'", shell=True, capture_output=True, text=True, errors='ignore').stdout
                processos = [p.strip() for p in proc_raw.split("\n") if p.strip()]
            except:
                pass
            if not processos: 
                processos = ["Nenhum app Windows em execução."]
                
            programas = []
            if wine_bin:
                try:
                    res_reg = subprocess.run(
                        f"{wine_bin} reg query \"HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\" /s",
                        shell=True, capture_output=True, text=True, errors='ignore', timeout=3
                    )
                    for line in res_reg.stdout.splitlines():
                        if "DisplayName" in line:
                            part = line.replace("DisplayName", "").replace("REG_SZ", "").strip()
                            part = " ".join(part.split())
                            if part and part not in programas and "grep" not in part.lower():
                                programas.append(part)
                    programas.sort()
                except:
                    pass
                
            if not programas: 
                programas = ["Nenhum software registrado."]

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
        except Exception:
            return {
                "ram": "Erro", "ram_pct": 40, "wine": "Erro",
                "processos": ["Erro no monitoramento interno."],
                "programas": ["Erro ao processar registros."], "sites": []
            }

    # ---------------- LAUNCHER DE JOGOS ----------------
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

    # ---------------- BLOQUEIO DE REDE ----------------
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

    # ---------------- GERENCIAMENTO DE ATUALIZAÇÕES ----------------
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
        try:
            if self.window: self.window.destroy()
        except:
            pass
        os._exit(0)

api = API()
html_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "index.html")

window = webview.create_window('Pistons HUB', url=html_file, js_api=api, fullscreen=True)
api.window = window
webview.start()
