/**
 * Frontend JavaScript для FastAPI RAG Agent
 * Поддержка SSE streaming, syntax highlighting, история сессий
 */

class ChatApp {
    constructor() {
        this.sessionId = this.loadSessionId();
        this.eventSource = null;
        this.isStreaming = false;
        
        // DOM элементы
        this.messagesContainer = document.getElementById('messages');
        this.messageInput = document.getElementById('message-input');
        this.chatForm = document.getElementById('chat-form');
        this.sendBtn = document.getElementById('send-btn');
        this.typingIndicator = document.getElementById('typing-indicator');
        
        this.init();
    }
    
    init() {
        // Обработчик формы
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Автофокус на поле ввода
        this.messageInput.focus();
        
        // Восстановление session_id из localStorage
        if (!this.sessionId) {
            this.sessionId = this.generateSessionId();
            this.saveSessionId();
        }
        
        console.log('Chat initialized with session:', this.sessionId);
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    loadSessionId() {
        return localStorage.getItem('fastapi_rag_session_id');
    }
    
    saveSessionId() {
        localStorage.setItem('fastapi_rag_session_id', this.sessionId);
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        
        const message = this.messageInput.value.trim();
        if (!message || this.isStreaming) return;
        
        // Добавление сообщения пользователя
        this.addMessage(message, 'user');
        this.messageInput.value = '';
        
        // Отправка запроса с SSE streaming
        await this.sendMessage(message);
    }
    
    addMessage(content, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (role === 'assistant') {
            // Для ассистента используем parseMarkdown для подсветки кода
            contentDiv.innerHTML = this.parseMarkdown(content);
            hljs.highlightAll();
        } else {
            contentDiv.textContent = content;
        }
        
        messageDiv.appendChild(contentDiv);
        this.messagesContainer.appendChild(messageDiv);
        
        // Прокрутка вниз
        this.scrollToBottom();
        
        return contentDiv;
    }
    
    updateLastMessage(content) {
        const lastMessage = this.messagesContainer.querySelector('.message.assistant:last-child .message-content');
        if (lastMessage) {
            lastMessage.innerHTML = this.parseMarkdown(content);
            hljs.highlightAll();
            this.scrollToBottom();
        }
    }
    
    parseMarkdown(text) {
        // Базовый парсинг markdown
        let html = text
            // Блоки кода
            .replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
                const language = lang || 'plaintext';
                return `<pre><code class="language-${language}">${this.escapeHtml(code.trim())}</code></pre>`;
            })
            // Инлайн код
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Жирный текст
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            // Курсив
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            // Переносы строк
            .replace(/\n/g, '<br>');
        
        return html;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    scrollToBottom() {
        const chatContainer = document.getElementById('chat-container');
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    showTypingIndicator(show) {
        this.typingIndicator.style.display = show ? 'flex' : 'none';
        if (show) {
            this.scrollToBottom();
        }
    }
    
    setLoading(loading) {
        this.isStreaming = loading;
        this.sendBtn.disabled = loading;
        this.messageInput.disabled = loading;
        
        if (loading) {
            this.showTypingIndicator(true);
        } else {
            this.showTypingIndicator(false);
            this.messageInput.focus();
        }
    }
    
    sendMessage(message) {
        // Используем streaming fetch запрос
        return this.sendStreamRequest(message);
    }
    
    async sendStreamRequest(message) {
        this.setLoading(true);
        
        let fullResponse = '';
        let assistantMessageDiv = this.addMessage('...', 'assistant');
        
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Чтение потока
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                const chunk = decoder.decode(value);
                
                // Парсинг SSE формата: data: {...}\n\n
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6);
                        
                        try {
                            const data = JSON.parse(dataStr);
                            
                            if (data.token) {
                                fullResponse += data.token;
                                this.updateLastMessage(fullResponse);
                            }
                            
                            if (data.done) {
                                this.sessionId = data.session_id;
                                this.saveSessionId();
                            }
                            
                            if (data.error) {
                                throw new Error(data.error);
                            }
                        } catch (e) {
                            console.warn('Parse error:', e, dataStr);
                        }
                    }
                }
            }
            
        } catch (error) {
            console.error('Stream error:', error);
            this.updateLastMessage(`Ошибка: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }
    
    async sendFallbackRequest(message) {
        this.setLoading(true);
        
        try {
            const response = await fetch('/chat/sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.updateLastMessage(data.response);
            this.sessionId = data.session_id;
            this.saveSessionId();
            
        } catch (error) {
            console.error('Fallback error:', error);
            this.updateLastMessage(`Ошибка: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }
}

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
});
