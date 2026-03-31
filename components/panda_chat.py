"""
熊猫小助手 - 悬浮AI聊天组件
通过 st.components.v1.html 注入到 Streamlit 主页面，
调用本地部署的通义千问模型 (Qwen-1_8B-Chat) 提供交互式AI问答。
"""
import os
import base64
import streamlit.components.v1 as components

_AVATAR_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "panda_avatar.png")

def _get_avatar_data_uri():
    """读取熊猫头像图片并返回 base64 data URI。"""
    if os.path.exists(_AVATAR_PATH):
        with open(_AVATAR_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{b64}"
    return "https://img.icons8.com/emoji/96/panda-emoji.png"

_PANDA_CHAT_HTML_TEMPLATE = """
<script>
(function() {
    var parentDoc;
    try {
        parentDoc = window.parent.document;
        if (!parentDoc || !parentDoc.body) return;
    } catch(e) {
        console.warn('Panda Assistant: cannot access parent document', e);
        return;
    }

    // 避免重复注入
    if (parentDoc.getElementById('panda-assistant')) return;

    // ===== 注入样式 =====
    const style = parentDoc.createElement('style');
    style.id = 'panda-assistant-style';
    style.textContent = `
        #panda-assistant {
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 99999;
            user-select: none;
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
        }
        #panda-avatar-btn {
            width: 72px;
            height: 72px;
            border-radius: 12px;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            background: #fff;
            padding: 4px;
            display: block;
            border: 2px solid #4CAF50;
            object-fit: cover;
        }
        #panda-avatar-btn:hover {
            transform: scale(1.08);
            box-shadow: 0 6px 20px rgba(0,0,0,0.25);
        }
        #panda-chat-panel {
            display: none;
            position: absolute;
            bottom: 85px;
            right: 0;
            width: 340px;
            max-height: 480px;
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.18);
            overflow: hidden;
            flex-direction: column;
        }
        #panda-chat-panel.open {
            display: flex;
        }
        #panda-chat-header {
            background: linear-gradient(135deg, #2E7D32, #66BB6A);
            color: #fff;
            padding: 14px 16px;
            font-size: 15px;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-shrink: 0;
        }
        #panda-close-btn {
            margin-left: auto;
            cursor: pointer;
            font-size: 18px;
            opacity: 0.8;
            transition: opacity 0.2s;
            background: none;
            border: none;
            color: #fff;
            padding: 0 4px;
        }
        #panda-close-btn:hover { opacity: 1; }
        #panda-chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
            background: #f5f9f5;
            min-height: 200px;
            max-height: 320px;
        }
        .panda-msg {
            margin: 6px 0;
            padding: 10px 14px;
            border-radius: 14px;
            font-size: 13px;
            line-height: 1.6;
            max-width: 88%;
            word-break: break-word;
        }
        .panda-msg.user {
            background: #e3f2fd;
            margin-left: auto;
            border-bottom-right-radius: 4px;
        }
        .panda-msg.bot {
            background: #fff;
            border: 1px solid #e0e0e0;
            border-bottom-left-radius: 4px;
        }
        .panda-msg.system {
            background: #e8f5e9;
            text-align: center;
            font-size: 12px;
            color: #555;
            max-width: 100%;
            border-radius: 8px;
        }
        .panda-msg.error {
            background: #fff3e0;
            text-align: center;
            font-size: 12px;
            color: #e65100;
            max-width: 100%;
            border-radius: 8px;
        }
        #panda-chat-input-area {
            display: flex;
            padding: 10px 12px;
            gap: 8px;
            border-top: 1px solid #e8e8e8;
            background: #fff;
            flex-shrink: 0;
        }
        #panda-chat-input {
            flex: 1;
            padding: 10px 14px;
            border: 1px solid #ddd;
            border-radius: 20px;
            outline: none;
            font-size: 13px;
            transition: border-color 0.2s;
        }
        #panda-chat-input:focus {
            border-color: #4CAF50;
        }
        #panda-chat-send {
            padding: 8px 18px;
            border: none;
            border-radius: 20px;
            background: #2E7D32;
            color: #fff;
            cursor: pointer;
            font-size: 13px;
            font-weight: bold;
            transition: background 0.2s;
        }
        #panda-chat-send:hover { background: #1B5E20; }
        #panda-chat-send:disabled {
            background: #bbb;
            cursor: not-allowed;
        }
        #panda-chat-panel::after {
            content: '';
            position: absolute;
            bottom: -8px;
            right: 28px;
            border-left: 8px solid transparent;
            border-right: 8px solid transparent;
            border-top: 8px solid #fff;
        }
        #panda-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #aaa;
            display: inline-block;
            margin-left: 4px;
        }
        #panda-status-dot.online { background: #4CAF50; }
        #panda-status-dot.offline { background: #f44336; }
    `;
    parentDoc.head.appendChild(style);

    // ===== 创建DOM =====
    const container = parentDoc.createElement('div');
    container.id = 'panda-assistant';
    container.innerHTML = `
        <div id="panda-chat-panel">
            <div id="panda-chat-header">
                <span>&#x1F43C; &#x718A;&#x732B;&#x5C0F;&#x52A9;&#x624B;</span>
                <span id="panda-status-dot" title="AI&#x6A21;&#x578B;&#x72B6;&#x6001;"></span>
                <button id="panda-close-btn">&#x2715;</button>
            </div>
            <div id="panda-chat-messages">
                <div class="panda-msg system">&#x4F60;&#x597D;&#xFF01;&#x6211;&#x662F;&#x718A;&#x732B;&#x5C0F;&#x52A9;&#x624B;&#xFF0C;&#x6709;&#x5173;&#x5927;&#x718A;&#x732B;&#x4E3B;&#x98DF;&#x7AF9;&#x76D1;&#x6D4B;&#x7684;&#x95EE;&#x9898;&#x90FD;&#x53EF;&#x4EE5;&#x95EE;&#x6211;&#x54E6;~</div>
            </div>
            <div id="panda-chat-input-area">
                <input type="text" id="panda-chat-input" placeholder="&#x8F93;&#x5165;&#x4F60;&#x7684;&#x95EE;&#x9898;..." />
                <button id="panda-chat-send">&#x53D1;&#x9001;</button>
            </div>
        </div>
        <img id="panda-avatar-btn" src="%%AVATAR_URI%%" alt="&#x718A;&#x732B;&#x5C0F;&#x52A9;&#x624B;" draggable="false" />
    `;
    parentDoc.body.appendChild(container);

    // ===== 元素引用 =====
    const assistant = parentDoc.getElementById('panda-assistant');
    const avatarBtn = parentDoc.getElementById('panda-avatar-btn');
    const panel = parentDoc.getElementById('panda-chat-panel');
    const closeBtn = parentDoc.getElementById('panda-close-btn');
    const msgBox = parentDoc.getElementById('panda-chat-messages');
    const chatInput = parentDoc.getElementById('panda-chat-input');
    const sendBtn = parentDoc.getElementById('panda-chat-send');
    const statusDot = parentDoc.getElementById('panda-status-dot');

    // ===== 配置 =====
    const LLM_API_URL = "http://localhost:8000/v1/chat/completions";
    const MODEL_NAME = "Qwen-1_8B-Chat";
    const SYSTEM_PROMPT = "你是'熊猫小助手'，一个专注于大熊猫主食竹监测与保护的AI助手。你运行在大熊猫主食竹智能监测与决策支持系统中。请用简洁友好的中文回答用户关于竹林监测、大熊猫保护、遥感分析、GIS地理信息等方面的问题。回答控制在200字以内。";
    const history = [];

    // ===== 检测模型服务状态 =====
    async function checkStatus() {
        try {
            const resp = await fetch(LLM_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: MODEL_NAME,
                    messages: [{ role: 'user', content: 'ping' }],
                    max_tokens: 1
                }),
                signal: AbortSignal.timeout(3000)
            });
            statusDot.className = resp.ok ? 'online' : 'offline';
            statusDot.id = 'panda-status-dot';
        } catch(e) {
            statusDot.className = 'offline';
            statusDot.id = 'panda-status-dot';
        }
    }
    checkStatus();

    // ===== 拖拽 + 点击（区分移动距离） =====
    let dragStartX, dragStartY, elemStartX, elemStartY, hasMoved;

    avatarBtn.addEventListener('mousedown', function(e) {
        e.preventDefault();
        dragStartX = e.clientX;
        dragStartY = e.clientY;
        const rect = assistant.getBoundingClientRect();
        elemStartX = rect.left;
        elemStartY = rect.top;
        hasMoved = false;

        function onMove(ev) {
            const dx = ev.clientX - dragStartX;
            const dy = ev.clientY - dragStartY;
            if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
                hasMoved = true;
                const maxX = parentDoc.documentElement.clientWidth - assistant.offsetWidth;
                const maxY = parentDoc.documentElement.clientHeight - assistant.offsetHeight;
                assistant.style.left = Math.max(0, Math.min(elemStartX + dx, maxX)) + 'px';
                assistant.style.top = Math.max(0, Math.min(elemStartY + dy, maxY)) + 'px';
                assistant.style.bottom = 'auto';
                assistant.style.right = 'auto';
            }
        }

        function onUp() {
            parentDoc.removeEventListener('mousemove', onMove);
            parentDoc.removeEventListener('mouseup', onUp);
            if (!hasMoved) {
                panel.classList.toggle('open');
                if (panel.classList.contains('open')) {
                    chatInput.focus();
                    checkStatus();
                }
            }
        }

        parentDoc.addEventListener('mousemove', onMove);
        parentDoc.addEventListener('mouseup', onUp);
    });

    closeBtn.addEventListener('click', function() {
        panel.classList.remove('open');
    });

    // ===== 消息渲染 =====
    function addMsg(text, cls) {
        const d = parentDoc.createElement('div');
        d.className = 'panda-msg ' + cls;
        d.textContent = text;
        msgBox.appendChild(d);
        msgBox.scrollTop = msgBox.scrollHeight;
        return d;
    }

    // ===== 发送消息 =====
    async function sendMessage() {
        const q = chatInput.value.trim();
        if (!q) return;

        chatInput.value = '';
        addMsg(q, 'user');
        sendBtn.disabled = true;

        history.push({ role: 'user', content: q });

        const thinking = addMsg('正在思考...', 'bot');

        try {
            const messages = [
                { role: 'system', content: SYSTEM_PROMPT },
                ...history.slice(-10)
            ];

            const response = await fetch(LLM_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: MODEL_NAME,
                    messages: messages,
                    temperature: 0.7,
                    max_tokens: 512,
                    stream: false
                }),
                signal: AbortSignal.timeout(30000)
            });

            if (!response.ok) throw new Error('HTTP ' + response.status);

            const data = await response.json();
            const reply = data.choices && data.choices[0] && data.choices[0].message
                ? data.choices[0].message.content
                : '抱歉，我暂时无法回答这个问题。';

            thinking.textContent = reply;
            history.push({ role: 'assistant', content: reply });
            statusDot.className = 'online';
            statusDot.id = 'panda-status-dot';
        } catch (err) {
            thinking.textContent = 'AI助手暂时离线，请确保本地模型服务已启动 (localhost:8000)';
            thinking.className = 'panda-msg error';
            statusDot.className = 'offline';
            statusDot.id = 'panda-status-dot';
            // 移除失败的用户消息记录，避免污染对话历史
            history.pop();
        }

        sendBtn.disabled = false;
        msgBox.scrollTop = msgBox.scrollHeight;
    }

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

})();
</script>
"""


def render_panda_assistant():
    """在Streamlit页面中注入悬浮熊猫小助手AI聊天组件。
    组件通过 window.parent.document 注入到主页面，不受iframe限制。
    注意: height 不能为0，否则浏览器不会渲染iframe，脚本无法执行。
    """
    avatar_uri = _get_avatar_data_uri()
    html = _PANDA_CHAT_HTML_TEMPLATE.replace("%%AVATAR_URI%%", avatar_uri)
    components.html(html, height=2, scrolling=False)
