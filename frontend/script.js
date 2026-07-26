/* ==========================================================================
   CONFIGURAÇÕES GLOBAIS E ESTADOS
   ========================================================================== */
let modoAtual = 'dev';
const IMG_ANONIMO = "avatar.jpg";
const IMG_STYLE = 'style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover; position: absolute; top: 0; left: 0;"';

const USUARIOS_CONHECIDOS = {
    "lkm2201": "https://github.com/lkm2201.png",
    "crawford-guitar": "https://github.com/crawford-guitar.png"
};

/* ==========================================================================
   MÓDULO DE AUTENTICAÇÃO E PERFIL
   ========================================================================== */
function alternarModo(modo) {
    modoAtual = modo;
    document.getElementById('login-erro').innerText = "";
    
    const av = document.getElementById('login-avatar-text');
    const title = document.getElementById('login-user-title');
    const sub = document.getElementById('login-user-sub');

    if (modo === 'dev') {
        document.getElementById('btn-mode-dev').classList.add('ativo');
        document.getElementById('btn-mode-guest').classList.remove('ativo');
        document.getElementById('fields-dev').classList.remove('hidden');
        document.getElementById('fields-guest').classList.add('hidden');
        atualizarIniciais();
    } else {
        document.getElementById('btn-mode-guest').classList.add('ativo');
        document.getElementById('btn-mode-dev').classList.remove('ativo');
        document.getElementById('fields-guest').classList.remove('hidden');
        document.getElementById('fields-dev').classList.add('hidden');
        
        av.innerHTML = `AN<img src="${IMG_ANONIMO}" ${IMG_STYLE} onerror="this.style.display='none'">`;
        title.innerText = "Acesso via Token";
        sub.innerText = "Modo Convidado";
    }
}

function atualizarIniciais() {
    const rawVal = document.getElementById('user-input').value.trim();
    const val = rawVal.toLowerCase();
    const av = document.getElementById('login-avatar-text');
    const title = document.getElementById('login-user-title');
    const sub = document.getElementById('login-user-sub');
    
    const fallbackText = val.length > 0 ? val.substring(0, 2).toUpperCase() : "AN";
    
    if (val.length > 0) {
        if (USUARIOS_CONHECIDOS[val]) {
            av.innerHTML = `${fallbackText}<img src="${USUARIOS_CONHECIDOS[val]}" ${IMG_STYLE} onerror="this.style.display='none'">`;
            title.innerText = rawVal;
            sub.innerText = "Desenvolvedor Identificado";
        } else {
            av.innerHTML = `${fallbackText}<img src="${IMG_ANONIMO}" ${IMG_STYLE} onerror="this.style.display='none'">`;
            title.innerText = rawVal;
            sub.innerText = "Verificando...";
        }
    } else {
        av.innerHTML = `AN<img src="${IMG_ANONIMO}" ${IMG_STYLE} onerror="this.style.display='none'">`;
        title.innerText = "Usuário Anônimo";
        sub.innerText = "Acesso Não Identificado";
    }
}

function executarLogin() {
    const err = document.getElementById('login-erro');
    err.innerText = "";

    if (modoAtual === 'guest') {
        const token = document.getElementById('token-input').value.trim();
        if(!token) { err.innerText = "Digite um token válido!"; return; }
        
        pywebview.api.validar_token(token).then(res => {
            if (res.status === "success") { entrarNoHub(res.user.name, res.user.avatar, res.user.role); } 
            else { err.innerText = res.message || "Token inválido!"; }
        });
        return;
    }

    const u = document.getElementById('user-input').value;
    const p = document.getElementById('pass-input').value;
    if(!u || !p) { err.innerText = "Preencha usuário e senha!"; return; }

    pywebview.api.fazer_login(u, p).then(res => {
        if (res.status === "success") { entrarNoHub(res.user.name, res.user.avatar, res.user.role); } 
        else { err.innerText = res.message || "Credenciais inválidas!"; }
    }).catch(() => { err.innerText = "Erro na comunicação com o backend."; });
}

/* ==========================================================================
   MÓDULO DO HUB E NAVEGAÇÃO
   ========================================================================== */
function entrarNoHub(nome, avatar, cargo) {
    document.getElementById('screen-login').classList.add('hidden');
    document.getElementById('screen-hub').classList.remove('hidden');
    document.getElementById('user-display-name').innerText = `${nome} (${cargo})`;
    
    if (avatar) {
        document.getElementById('user-avatar').innerHTML = `<img src="${avatar}" style="width:100%; border-radius:50%;" onerror="this.style.display='none'">`;
    }
    
    carregarLauncher();
    sincronizarDados();
    setInterval(sincronizarDados, 3000);
}

function trocarAba(nomeAba) {
    document.getElementById('tab-launcher').classList.add('hidden');
    document.getElementById('tab-dashboard').classList.add('hidden');
    document.getElementById('btn-launcher').classList.remove('ativo');
    document.getElementById('btn-dashboard').classList.remove('ativo');
    
    document.getElementById('tab-' + nomeAba).classList.remove('hidden');
    document.getElementById('btn-' + nomeAba).classList.add('ativo');
}

/* ==========================================================================
   GERENCIAMENTO DE APLICATIVOS E STATUS
   ========================================================================== */
function carregarLauncher() {
    pywebview.api.listar_jogos().then(jogos => {
        const grid = document.getElementById('grid-jogos');
        grid.innerHTML = "";
        
        if (!jogos || jogos.length === 0) {
            grid.innerHTML = `<div style="grid-column: span 3; color: #4b5563; font-style: italic; font-size: 14px; text-align: center; padding-top: 40px;">Nenhum aplicativo cadastrado. Clique em "+ Cadastrar App" para adicionar executáveis.</div>`;
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
                    <button class="btn-piston primario" style="padding: 10px; margin-top: 20px;" onclick="pywebview.api.lancar_jogo('${jogo.caminho}')">ABRIR</button>
                </div>
            `;
        });
    });
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
    });
}

/* ATALHOS DE TECLADO */
document.addEventListener('keypress', function (e) {
    if (e.key === 'Enter' && !document.getElementById('screen-login').classList.contains('hidden')) { 
        executarLogin(); 
    }
});
