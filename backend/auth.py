import hashlib
import hmac
import os
import time

AVATAR_PADRAO = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' fill='%23333333'><rect width='100' height='100' fill='%23f0f0f0'/><circle cx='50' cy='35' r='22'/><path d='M 15 88 C 15 62, 35 56, 50 56 C 65 56, 85 62, 85 88 Z'/></svg>"

class AuthManager:
    def __init__(self):
        salt_lkm = bytes.fromhex("a1b2c3d4e5f601020304050607080900")
        hash_lkm = hashlib.pbkdf2_hmac('sha256', b'2255', salt_lkm, 100000).hex()
        salt_crawford = bytes.fromhex("b2c3d4e5f601020304050607080900a1")
        hash_crawford = hashlib.pbkdf2_hmac('sha256', b'2255', salt_crawford, 100000).hex()

        self.users = {
            "lkm2201": {"hash": hash_lkm, "salt": salt_lkm, "name": "Lkm2201", "role": "Pistons Tech Developer", "avatar": "https://github.com/lkm2201.png"},
            "crawford-guitar": {"hash": hash_crawford, "salt": salt_crawford, "name": "Vencedor", "role": "Pistons Tech Developer", "avatar": "https://github.com/crawford-guitar.png"}
        }
        self.falhas_login = {}
        self.tempo_bloqueio = 300
        self.max_tentativas = 3

    def validar_login_dev(self, username, password):
        usr = (username or "").strip().lower()
        pwd = (password or "").strip().encode('utf-8')
        agora = time.time()

        if usr in self.falhas_login:
            tentativas, expiracao = self.falhas_login[usr]
            if tentativas >= self.max_tentativas and agora < expiracao:
                return {"status": "error", "message": f"Bloqueado por {int(expiracao - agora)}s."}
            elif agora >= expiracao:
                self.falhas_login[usr] = (0, 0)

        if usr not in self.users:
            self._registrar_falha(usr)
            return {"status": "error", "message": "Credenciais inválidas."}

        dados_user = self.users[usr]
        hash_tentativa = hashlib.pbkdf2_hmac('sha256', pwd, dados_user["salt"], 100000).hex()

        if hmac.compare_digest(hash_tentativa, dados_user["hash"]):
            if usr in self.falhas_login: del self.falhas_login[usr]
            return {"status": "success", "user": {"name": dados_user["name"], "role": dados_user["role"], "avatar": dados_user["avatar"]}}
        else:
            self._registrar_falha(usr)
            return {"status": "error", "message": "Credenciais inválidas."}

    def _registrar_falha(self, usr):
        tentativas, _ = self.falhas_login.get(usr, (0, 0))
        tentativas += 1
        expiracao = time.time() + self.tempo_bloqueio if tentativas >= self.max_tentativas else 0
        self.falhas_login[usr] = (tentativas, expiracao)

    def validar_token_convidado(self, token):
        tk = (token or "").strip().upper()
        if hmac.compare_digest(tk, "PISTONS-2026") or hmac.compare_digest(tk, "GUEST-2255"):
            return {"status": "success", "user": {"name": "Convidado PISTONS", "role": "Acesso Temporário", "avatar": AVATAR_PADRAO}}
        return {"status": "error", "message": "Token inválido."}
