document.addEventListener('DOMContentLoaded', () => {
    const bubble = document.getElementById('ai-chat-bubble');
    const hint = document.getElementById('ai-chat-hint');
    
    // Create Chat Window if it doesn't exist
    let chatWindow = document.getElementById('ai-chat-window');
    if (!chatWindow) {
        chatWindow = document.createElement('div');
        chatWindow.id = 'ai-chat-window';
        chatWindow.className = 'fixed bottom-24 right-4 md:bottom-28 md:right-8 z-[70] w-[calc(100%-32px)] md:w-[380px] h-[500px] md:h-[550px] bg-white rounded-[32px] shadow-2xl border border-outline-variant/10 flex flex-col overflow-hidden transition-all duration-500 opacity-0 translate-y-8 pointer-events-none scale-95';
        chatWindow.innerHTML = `
            <!-- Header -->
            <div class="p-6 bg-zinc-900 text-white flex justify-between items-center relative overflow-hidden">
                <div class="relative z-10 flex items-center gap-3">
                    <div class="w-10 h-10 bg-primary/20 rounded-2xl flex items-center justify-center border border-white/10">
                        <span class="material-symbols-outlined text-emerald-400">bubble_chart</span>
                    </div>
                    <div>
                        <h3 class="font-headline font-extrabold text-sm tracking-tight text-white">Local Concierge</h3>
                        <div class="flex items-center gap-1.5">
                            <div class="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                            <span class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Active Now</span>
                        </div>
                    </div>
                </div>
                <button id="close-ai-chat" class="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-all relative z-10">
                    <span class="material-symbols-outlined text-sm font-bold">close</span>
                </button>
                <!-- Decorative background -->
                <div class="absolute -right-4 -top-4 w-20 h-20 bg-primary/20 rounded-full blur-2xl"></div>
            </div>
            
            <!-- Messages Area -->
            <div id="ai-messages" class="flex-grow p-6 overflow-y-auto space-y-4 bg-surface-container-low/30 scroll-smooth">
                <div class="flex gap-3">
                    <div class="w-8 h-8 bg-emerald-100 rounded-xl flex items-center justify-center text-emerald-700 flex-shrink-0">
                        <span class="material-symbols-outlined text-sm">potted_plant</span>
                    </div>
                    <div class="bg-white border border-outline-variant/5 rounded-2xl rounded-tl-none p-4 shadow-sm max-w-[80%]">
                        <p class="text-xs font-medium text-on-surface-variant leading-relaxed">
                            Welcome to the Food Network Market. I can help you find fresh harvests, meet our producers, or assist with your local order. What's on your mind today? 🌿
                        </p>
                    </div>
                </div>
            </div>
            
            <!-- Input Area -->
            <div class="p-4 border-t border-outline-variant/10 bg-white">
                <div class="flex gap-2 items-center bg-surface-container-high rounded-full px-5 py-2 group focus-within:ring-2 focus-within:ring-primary/20 transition-all">
                    <input type="text" id="ai-chat-input" class="bg-transparent border-none focus:ring-0 text-sm flex-grow font-medium" placeholder="Ask about seasonal produce..." autocomplete="off">
                    <button id="send-ai-message" class="w-8 h-8 bg-primary text-on-primary rounded-full flex items-center justify-center shadow-lg shadow-primary/20 hover:scale-105 active:scale-95 transition-all">
                        <span class="material-symbols-outlined text-sm">arrow_upward</span>
                    </button>
                </div>
                <p class="text-[8px] text-center text-outline mt-3 font-bold uppercase tracking-widest">Powered by Local Qwen2.5 Intelligence</p>
            </div>
        `;
        document.body.appendChild(chatWindow);
    }

    const messagesArea = document.getElementById('ai-messages');
    const inputField = document.getElementById('ai-chat-input');
    const sendBtn = document.getElementById('send-ai-message');
    const closeBtn = document.getElementById('close-ai-chat');

    function toggleChat() {
        if (chatWindow.classList.contains('opacity-0')) {
            // Open
            chatWindow.classList.remove('opacity-0', 'translate-y-8', 'pointer-events-none', 'scale-95');
            chatWindow.classList.add('opacity-100', 'translate-y-0', 'pointer-events-auto', 'scale-100');
            if (hint) hint.classList.add('hidden');
            inputField.focus();
        } else {
            // Close
            chatWindow.classList.add('opacity-0', 'translate-y-8', 'pointer-events-none', 'scale-95');
            chatWindow.classList.remove('opacity-100', 'translate-y-0', 'pointer-events-auto', 'scale-100');
        }
    }

    bubble.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    function appendMessage(role, text) {
        const isUser = role === 'user';
        const msgDiv = document.createElement('div');
        msgDiv.className = `flex ${isUser ? 'justify-end' : 'justify-start'} gap-3 animate-in slide-in-from-bottom-2 duration-300`;
        
        const parsedText = parseMarkdown(text);
        
        if (isUser) {
            msgDiv.innerHTML = `
                <div class="bg-zinc-900 text-white rounded-[24px] rounded-tr-none p-4 shadow-sm max-w-[85%]">
                    <div class="text-sm font-medium leading-relaxed whitespace-pre-wrap">${text}</div>
                </div>
            `;
        } else {
            msgDiv.innerHTML = `
                <div class="w-9 h-9 bg-emerald-100 rounded-2xl flex items-center justify-center text-emerald-700 flex-shrink-0 shadow-sm">
                    <span class="material-symbols-outlined text-base">bubble_chart</span>
                </div>
                <div class="bg-white border border-outline-variant/10 rounded-[24px] rounded-tl-none p-5 shadow-sm max-w-[85%] transition-all">
                    <div class="text-[13px] font-medium text-on-surface-variant leading-relaxed space-y-2">${parsedText}</div>
                </div>
            `;
        }
        
        messagesArea.appendChild(msgDiv);
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }

    function parseMarkdown(text) {
        // 1. Handle Bold: **text**
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong class="text-zinc-900 font-extrabold">$1</strong>');
        
        // 2. Handle Lists: Start with - or * or •
        const lines = text.split('\n');
        let inList = false;
        let html = '';
        
        lines.forEach(line => {
            const trimmed = line.trim();
            if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ')) {
                if (!inList) {
                    html += '<ul class="list-none space-y-2 mt-2">';
                    inList = true;
                }
                const content = trimmed.substring(2);
                html += `<li class="flex gap-2 items-start"><span class="text-emerald-500 font-bold mt-0.5">◦</span><span>${content}</span></li>`;
            } else {
                if (inList) {
                    html += '</ul>';
                    inList = false;
                }
                if (trimmed) {
                    html += `<p class="mb-2">${line}</p>`;
                } else {
                    html += '<div class="h-2"></div>'; // Spacing for double newlines
                }
            }
        });
        
        if (inList) html += '</ul>';
        return html;
    }

    async function handleSend() {
        const message = inputField.value.trim();
        if (!message) return;

        inputField.value = '';
        appendMessage('user', message);

        // Show typing indicator
        const typingId = 'typing-' + Date.now();
        const typingDiv = document.createElement('div');
        typingDiv.id = typingId;
        typingDiv.className = 'flex gap-3 justify-start items-center';
        typingDiv.innerHTML = `
            <div class="w-8 h-8 bg-emerald-50 rounded-xl flex items-center justify-center text-emerald-600 flex-shrink-0">
                <span class="material-symbols-outlined text-sm animate-pulse">monitoring</span>
            </div>
            <p class="text-[9px] font-bold text-outline-variant uppercase tracking-widest animate-pulse">Syncing with local records...</p>
        `;
        messagesArea.appendChild(typingDiv);
        messagesArea.scrollTop = messagesArea.scrollHeight;

        try {
            const res = await fetch('/ai/chatbot/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ message: message })
            });
            
            const data = await res.json();
            document.getElementById(typingId).remove();

            if (res.ok && data.success) {
                appendMessage('assistant', data.reply || data.response || "No reply found.");
            } else {
                appendMessage('assistant', "AI is offline, please try again later (AI server is resting 🌿)");
            }
        } catch (e) {
            document.getElementById(typingId).remove();
            appendMessage('assistant', "AI is offline, please try again later. System connection error.");
        }
    }

    sendBtn.addEventListener('click', handleSend);
    inputField.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSend();
    });

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
