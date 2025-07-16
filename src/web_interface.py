from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import threading
import time
import queue
from selenium import webdriver
from src.gift_logic import GiftBuyer

app = Flask(__name__)

# Глобальные переменные для управления ботом
bot_thread = None
driver = None
buyer = None
is_running = False
log_queue = queue.Queue()

# HTML шаблон для веб-интерфейса
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Gift Bot - Веб-интерфейс</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .content {
            display: flex;
            min-height: 600px;
        }
        .left-panel {
            flex: 1;
            padding: 30px;
            border-right: 1px solid #eee;
        }
        .right-panel {
            flex: 1;
            padding: 30px;
        }
        .form-group {
            margin-bottom: 25px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #2c3e50;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #3498db;
        }
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-right: 10px;
        }
        .btn-primary {
            background: #27ae60;
            color: white;
        }
        .btn-primary:hover {
            background: #229954;
            transform: translateY(-2px);
        }
        .btn-danger {
            background: #e74c3c;
            color: white;
        }
        .btn-danger:hover {
            background: #c0392b;
            transform: translateY(-2px);
        }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .status {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: 600;
        }
        .status.waiting {
            background: #f39c12;
            color: white;
        }
        .status.running {
            background: #27ae60;
            color: white;
        }
        .status.error {
            background: #e74c3c;
            color: white;
        }
        .log-area {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.4;
        }
        .log-entry {
            margin-bottom: 5px;
            padding: 2px 0;
        }
        .log-timestamp {
            color: #95a5a6;
        }
        .log-message {
            color: #ecf0f1;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            margin-bottom: 20px;
        }
        .stat-item {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            flex: 1;
            margin: 0 5px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }
        .stat-label {
            color: #7f8c8d;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎁 Telegram Gift Bot</h1>
            <p>Веб-интерфейс управления</p>
        </div>
        
        <div class="content">
            <div class="left-panel">
                <div id="status" class="status waiting">
                    🟠 Ожидание
                </div>
                
                <form id="settings-form">
                    <div class="form-group">
                        <label for="threshold">Порог в процентах ниже среднего:</label>
                        <input type="range" id="threshold" name="threshold" min="10" max="90" value="50" 
                               oninput="updateThresholdValue(this.value)">
                        <span id="threshold-value">50%</span>
                    </div>
                    
                    <div class="form-group">
                        <label for="min-price">Минимальная цена фильтрации:</label>
                        <input type="number" id="min-price" name="min_price" value="10000" min="1000" step="1000">
                        <span>⭐</span>
                    </div>
                    
                    <div class="form-group">
                        <button type="button" id="start-btn" class="btn btn-primary" onclick="startBot()">
                            ▶ Запустить бота
                        </button>
                        <button type="button" id="stop-btn" class="btn btn-danger" onclick="stopBot()" disabled>
                            ⏹ Остановить
                        </button>
                    </div>
                </form>
                
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-value" id="gifts-bought">0</div>
                        <div class="stat-label">Подарков куплено</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="cycles">0</div>
                        <div class="stat-label">Циклов выполнено</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="errors">0</div>
                        <div class="stat-label">Ошибок</div>
                    </div>
                </div>
            </div>
            
            <div class="right-panel">
                <h3>📝 Логи работы</h3>
                <div id="log-area" class="log-area"></div>
                <button type="button" class="btn btn-primary" onclick="clearLogs()" style="margin-top: 10px;">
                    🗑 Очистить логи
                </button>
            </div>
        </div>
    </div>

    <script>
        let logUpdateInterval;
        
        function updateThresholdValue(value) {
            document.getElementById('threshold-value').textContent = value + '%';
        }
        
        function updateStatus(status, message) {
            const statusEl = document.getElementById('status');
            statusEl.className = 'status ' + status;
            statusEl.innerHTML = message;
        }
        
        function addLogEntry(message) {
            const logArea = document.getElementById('log-area');
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry';
            logEntry.innerHTML = `
                <span class="log-timestamp">[${timestamp}]</span>
                <span class="log-message">${message}</span>
            `;
            logArea.appendChild(logEntry);
            logArea.scrollTop = logArea.scrollHeight;
        }
        
        function startBot() {
            const threshold = document.getElementById('threshold').value;
            const minPrice = document.getElementById('min-price').value;
            
            fetch('/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    threshold: parseInt(threshold),
                    min_price: parseInt(minPrice)
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateStatus('running', '🟢 Бот активен');
                    document.getElementById('start-btn').disabled = true;
                    document.getElementById('stop-btn').disabled = false;
                    addLogEntry('🚀 Бот запущен');
                } else {
                    addLogEntry('❌ Ошибка запуска: ' + data.error);
                }
            })
            .catch(error => {
                addLogEntry('❌ Ошибка: ' + error);
            });
        }
        
        function stopBot() {
            fetch('/stop', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateStatus('waiting', '🟠 Ожидание');
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('stop-btn').disabled = true;
                    addLogEntry('⏹ Бот остановлен');
                }
            })
            .catch(error => {
                addLogEntry('❌ Ошибка остановки: ' + error);
            });
        }
        
        function clearLogs() {
            document.getElementById('log-area').innerHTML = '';
        }
        
        function updateLogs() {
            fetch('/logs')
            .then(response => response.json())
            .then(data => {
                data.logs.forEach(log => {
                    addLogEntry(log);
                });
            });
        }
        
        function updateStats() {
            fetch('/stats')
            .then(response => response.json())
            .then(data => {
                document.getElementById('gifts-bought').textContent = data.gifts_bought;
                document.getElementById('cycles').textContent = data.cycles;
                document.getElementById('errors').textContent = data.errors;
            });
        }
        
        // Запуск обновлений
        setInterval(updateLogs, 1000);
        setInterval(updateStats, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start', methods=['POST'])
def start_bot():
    global bot_thread, driver, buyer, is_running
    
    if is_running:
        return jsonify({'success': False, 'error': 'Бот уже запущен'})
    
    try:
        data = request.get_json()
        threshold = data.get('threshold', 50)
        min_price = data.get('min_price', 10000)
        
        def run_bot():
            global driver, buyer, is_running
            try:
                log_message("🌐 Открытие браузера Firefox...")
                driver = webdriver.Firefox()
                driver.get('https://web.telegram.org')
                
                log_message("📱 Откройте Telegram Web и авторизуйтесь")
                
                time.sleep(3)
                
                log_message("🤖 Создание экземпляра бота...")
                buyer = GiftBuyer(driver, threshold, 13, min_price, log_message)
                
                log_message("🎯 Запуск основного цикла...")
                buyer.buy_gift_if_profitable()
                
            except Exception as e:
                log_message(f"❌ Ошибка в работе бота: {e}")
            finally:
                stop_bot_internal()
        
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        is_running = True
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/stop', methods=['POST'])
def stop_bot():
    global is_running
    stop_bot_internal()
    return jsonify({'success': True})

def stop_bot_internal():
    global driver, buyer, is_running
    is_running = False
    
    if driver:
        try:
            driver.quit()
            log_message("🌐 Браузер закрыт")
        except:
            pass
        driver = None
    
    buyer = None

@app.route('/logs')
def get_logs():
    logs = []
    try:
        while True:
            log = log_queue.get_nowait()
            logs.append(log)
    except queue.Empty:
        pass
    return jsonify({'logs': logs})

@app.route('/stats')
def get_stats():
    # Здесь можно добавить реальную статистику
    return jsonify({
        'gifts_bought': 0,
        'cycles': 0,
        'errors': 0
    })

def log_message(message):
    """Добавление сообщения в лог"""
    timestamp = time.strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    log_queue.put(log_entry)

if __name__ == '__main__':
    print("🌐 Запуск веб-интерфейса...")
    print("📱 Откройте браузер и перейдите по адресу: http://localhost:8080")
    app.run(debug=True, host='0.0.0.0', port=8080) 