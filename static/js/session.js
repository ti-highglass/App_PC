// Sistema de logout automático por inatividade
let inactivityTimer;
const INACTIVITY_TIME = 60 * 60 * 1000; // 60 minutos em milissegundos
const ACTIVITY_MESSAGE = 'opera:activity';

const buildAllowedOrigins = () => {
    const list = [];
    if (typeof window !== 'undefined') {
        if (window.location && window.location.origin) {
            list.push(window.location.origin);
        }
        if (Array.isArray(window.OPERA_ACTIVITY_ALLOWED_ORIGINS)) {
            window.OPERA_ACTIVITY_ALLOWED_ORIGINS.forEach((origin) => {
                if (origin && !list.includes(origin)) {
                    list.push(origin);
                }
            });
        }
    }
    return list;
};

const activityAllowedOrigins = buildAllowedOrigins();

function resetTimer() {
    clearTimeout(inactivityTimer);
    inactivityTimer = setTimeout(() => {
        alert('Sessão expirada por inatividade. Você será redirecionado para o login.');
        window.location.href = '/logout';
    }, INACTIVITY_TIME);
}

// Eventos que resetam o timer
const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];

// Adicionar listeners para todos os eventos
events.forEach(event => {
    document.addEventListener(event, resetTimer, true);
});

window.addEventListener('message', (event) => {
    if (event.data !== ACTIVITY_MESSAGE) {
        return;
    }
    if (event.origin && activityAllowedOrigins.length && !activityAllowedOrigins.includes(event.origin)) {
        return;
    }
    resetTimer();
});

// Iniciar o timer quando a página carregar
document.addEventListener('DOMContentLoaded', resetTimer);
