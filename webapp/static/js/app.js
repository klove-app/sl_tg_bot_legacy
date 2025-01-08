// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Получаем текущий год и месяц
const currentDate = new Date();
const currentYear = currentDate.getFullYear();
const currentMonth = currentDate.getMonth() + 1;

// API endpoints
const API_BASE = '/api';
const endpoints = {
    summary: `${API_BASE}/stats/summary`,
    monthly: `${API_BASE}/stats/monthly`,
    runners: `${API_BASE}/stats/runners`,
    challenges: `${API_BASE}/stats/challenges`,
    chats: `${API_BASE}/stats/chats`
};

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Обработка переключения вкладок
    setupTabs();
    
    // Загрузка начальных данных
    loadSummaryStats();
});

// Настройка переключения вкладок
function setupTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Убираем активный класс у всех вкладок
            tabs.forEach(t => t.classList.remove('active'));
            // Добавляем активный класс текущей вкладке
            tab.classList.add('active');
            
            // Показываем соответствующий контент
            const tabId = tab.dataset.tab;
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');
            
            // Загружаем данные для вкладки
            loadTabData(tabId);
        });
    });
}

// Загрузка данных для вкладки
async function loadTabData(tabId) {
    switch (tabId) {
        case 'summary':
            await loadSummaryStats();
            break;
        case 'monthly':
            await loadMonthlyStats();
            break;
        case 'runners':
            await loadTopRunners();
            break;
        case 'challenges':
            await loadChallenges();
            break;
        case 'chats':
            await loadChatStats();
            break;
    }
}

// Загрузка общей статистики
async function loadSummaryStats() {
    try {
        const response = await fetch(endpoints.summary);
        const data = await response.json();
        
        // Обновляем значения на странице
        document.getElementById('total-runs').textContent = data.runs_count;
        document.getElementById('total-km').textContent = `${data.total_km.toFixed(1)} км`;
        document.getElementById('total-runners').textContent = data.users_count;
        document.getElementById('avg-km').textContent = `${data.avg_km.toFixed(1)} км`;
    } catch (error) {
        console.error('Error loading summary stats:', error);
    }
}

// Загрузка статистики по месяцам
async function loadMonthlyStats() {
    try {
        const response = await fetch(endpoints.monthly);
        const data = await response.json();
        
        const ctx = document.getElementById('monthly-chart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => `${d.month}.${currentYear}`),
                datasets: [{
                    label: 'Километры',
                    data: data.map(d => d.total_km),
                    backgroundColor: '#2481cc'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    } catch (error) {
        console.error('Error loading monthly stats:', error);
    }
}

// Загрузка топ бегунов
async function loadTopRunners() {
    try {
        const response = await fetch(endpoints.runners);
        const data = await response.json();
        
        const container = document.getElementById('top-runners');
        container.innerHTML = '';
        
        data.forEach((runner, index) => {
            const medal = index < 3 ? ['🥇', '🥈', '🥉'][index] : '';
            const progress = (runner.total_km / data[0].total_km * 100).toFixed(0);
            
            const item = document.createElement('div');
            item.className = 'list-item';
            item.innerHTML = `
                <div>
                    ${medal} ${runner.username}
                    <small>${runner.total_km.toFixed(1)} км</small>
                </div>
                <div class="progress-bar">
                    <div class="progress-bar-fill" style="width: ${progress}%"></div>
                </div>
            `;
            container.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading top runners:', error);
    }
}

// Загрузка челленджей
async function loadChallenges() {
    try {
        const response = await fetch(endpoints.challenges);
        const data = await response.json();
        
        const container = document.getElementById('active-challenges');
        container.innerHTML = '';
        
        data.forEach(challenge => {
            const progress = (challenge.total_km / challenge.goal_km * 100).toFixed(0);
            
            const item = document.createElement('div');
            item.className = 'list-item';
            item.innerHTML = `
                <div>
                    ${challenge.title}
                    <small>${challenge.total_km.toFixed(1)}/${challenge.goal_km} км</small>
                </div>
                <div class="progress-bar">
                    <div class="progress-bar-fill" style="width: ${progress}%"></div>
                </div>
                <span>${progress}%</span>
            `;
            container.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading challenges:', error);
    }
}

// Загрузка статистики по чатам
async function loadChatStats() {
    try {
        const response = await fetch(endpoints.chats);
        const data = await response.json();
        
        const container = document.getElementById('chat-stats');
        container.innerHTML = '';
        
        const maxKm = Math.max(...data.map(chat => chat.total_km));
        
        data.forEach(chat => {
            const progress = (chat.total_km / maxKm * 100).toFixed(0);
            
            const item = document.createElement('div');
            item.className = 'list-item';
            item.innerHTML = `
                <div>
                    ${chat.chat_id}
                    <small>${chat.total_km.toFixed(1)} км • ${chat.runs_count} пробежек</small>
                </div>
                <div class="progress-bar">
                    <div class="progress-bar-fill" style="width: ${progress}%"></div>
                </div>
            `;
            container.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading chat stats:', error);
    }
} 