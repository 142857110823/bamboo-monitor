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
            top: 60px;
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
            top: 85px;
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
            top: -8px;
            right: 28px;
            border-left: 8px solid transparent;
            border-right: 8px solid transparent;
            border-bottom: 8px solid #2E7D32;
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
        #panda-greeting {
            position: absolute;
            top: 8px;
            right: 85px;
            background: #2E7D32;
            color: #fff;
            padding: 8px 14px;
            border-radius: 12px;
            font-size: 13px;
            white-space: nowrap;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            opacity: 0;
            animation: pandaGreetIn 0.4s ease 0.5s forwards, pandaGreetOut 0.5s ease 6s forwards;
            pointer-events: none;
        }
        #panda-greeting::after {
            content: '';
            position: absolute;
            top: 50%;
            right: -6px;
            transform: translateY(-50%);
            border-top: 6px solid transparent;
            border-bottom: 6px solid transparent;
            border-left: 6px solid #2E7D32;
        }
        @keyframes pandaGreetIn {
            from { opacity: 0; transform: translateX(10px); }
            to { opacity: 1; transform: translateX(0); }
        }
        @keyframes pandaGreetOut {
            from { opacity: 1; }
            to { opacity: 0; }
        }
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
        <div id="panda-greeting">&#x55F7;&#x545C;&#xFF0C;&#x672C;&#x718A;&#x5DF2;&#x4E0A;&#x7EBF;&#x3002;&#x8BF7;&#x95EE;&#x6709;&#x9700;&#x8981;&#x5E2E;&#x5FD9;&#x7684;&#x5417;</div>
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
    const isHTTPS = window.parent.location.protocol === 'https:';

    // ===== 离线知识库（云端HTTPS模式使用） =====
    const KB = [
        { keys: ['你好','嗨','hello','hi','在吗'], answer: '你好呀！我是熊猫小助手，有关大熊猫主食竹监测的问题都可以问我哦~' },
        { keys: ['你是谁','介绍','自我介绍','什么'], answer: '我是熊猫小助手，运行在大熊猫主食竹智能监测与决策支持系统中。我可以回答关于竹林监测、大熊猫保护、遥感分析等方面的问题。' },
        { keys: ['竹林','竹子','主食竹','bamboo'], answer: '大熊猫的主食竹主要包括箭竹、缺苞箭竹和华西箭竹等。本系统通过遥感影像分析竹林的时空分布变化，目前监测区域为王朗自然保护区，利用双时相NDVI特征区分竹林的常绿特性。' },
        { keys: ['大熊猫','熊猫','panda','保护'], answer: '大熊猫是我国特有的珍稀濒危物种，被誉为"国宝"。竹子占大熊猫食物来源的99%以上，因此监测竹林资源对大熊猫栖息地保护至关重要。本系统可自动识别竹林退化、碎片化等风险。' },
        { keys: ['王朗','保护区','wanglang'], answer: '王朗自然保护区位于四川省绵阳市平武县，是我国最早建立的大熊猫自然保护区之一，面积约322平方公里。保护区内有丰富的竹林资源，是大熊猫重要的栖息地。' },
        { keys: ['ndvi','遥感','sentinel','卫星','影像'], answer: '本系统采用Sentinel-2卫星多时相遥感影像，提取夏季和冬季NDVI（归一化植被指数）作为特征。竹林在冬季仍保持较高NDVI值（常绿特性），而落叶林NDVI显著下降，利用这一差异可有效区分竹林。' },
        { keys: ['模型','随机森林','分类','预测','算法'], answer: '本系统采用随机森林（Random Forest）分类器，包含100棵决策树，输入双时相NDVI特征（夏季+冬季），输出竹林/非竹林二分类结果。模型在验证集上表现良好，适用于大面积竹林资源快速监测。' },
        { keys: ['预警','退化','碎片化','风险','alert'], answer: '系统会自动检测三类风险：1) 竹林退化预警 - 发现NDVI异常下降区域；2) 低覆盖度预警 - 竹林稀疏区域；3) 碎片化预警 - 竹林斑块破碎化严重区域。每条预警包含位置、影响面积和巡护建议。' },
        { keys: ['导出','下载','报告','export','tif','csv'], answer: '数据导出页面支持多种格式：GeoTIFF（含地理坐标的分类栅格）、JPG图片（适合报告插图）、CSV/Excel统计报表、TXT分析报告。所有文件均包含分析时间和模型版本信息。' },
        { keys: ['上传','分析','使用','怎么用','操作'], answer: '使用步骤：1) 在"数据上传与分析"页面上传GeoTIFF格式的双时相NDVI影像；2) 系统自动执行竹林分类推理；3) 在"交互式地图"查看空间分布；4) 在"预警与任务"查看风险区域；5) 在"数据导出"下载结果。' },
        { keys: ['gee','google earth engine','地球引擎'], answer: 'Google Earth Engine（GEE）是本系统数据预处理的核心平台，用于获取和处理Sentinel-2多时相遥感影像，生成双时相NDVI合成特征。GEE的云端计算能力使得大面积遥感数据处理更加高效。' },
        { keys: ['地图','folium','可视化','空间'], answer: '交互式地图基于Folium构建，支持：竹林分类结果叠加显示、保护区标记、预警位置标注、热力图展示竹林密度分布。支持图层控制、透明度调节和多种底图切换。' },
        { keys: ['谢谢','感谢','thanks','thank'], answer: '不客气！有任何关于竹林监测的问题随时问我。保护大熊猫，从保护竹林开始！' },
    ];
    function kbSearch(q) {
        var ql = q.toLowerCase();
        for (var i = 0; i < KB.length; i++) {
            for (var j = 0; j < KB[i].keys.length; j++) {
                if (ql.indexOf(KB[i].keys[j]) !== -1) return KB[i].answer;
            }
        }
        return '抱歉，这个问题超出了我的知识范围。本地部署模式下可连接通义千问获得更丰富的回答哦~\n\n你可以试试问我：竹林监测、大熊猫保护、NDVI遥感、模型算法、预警机制、数据导出等话题。';
    }

    // ===== 检测模型服务状态 =====
    var llmAvailable = false;
    async function checkStatus() {
        if (isHTTPS) {
            statusDot.className = 'online';
            statusDot.id = 'panda-status-dot';
            statusDot.title = '知识库模式';
            llmAvailable = false;
            return;
        }
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
            llmAvailable = resp.ok;
            statusDot.className = resp.ok ? 'online' : 'offline';
            statusDot.id = 'panda-status-dot';
        } catch(e) {
            llmAvailable = false;
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

        const thinking = addMsg('正在思考...', 'bot');

        // 云端HTTPS模式 或 本地模型不可用 → 使用知识库
        if (isHTTPS || !llmAvailable) {
            var reply = kbSearch(q);
            thinking.textContent = reply;
            sendBtn.disabled = false;
            msgBox.scrollTop = msgBox.scrollHeight;
            return;
        }

        // 本地HTTP模式 → 调用通义千问模型
        history.push({ role: 'user', content: q });

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
            // 模型调用失败，回退到知识库
            thinking.textContent = kbSearch(q);
            thinking.className = 'panda-msg bot';
            llmAvailable = false;
            statusDot.className = 'offline';
            statusDot.id = 'panda-status-dot';
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
