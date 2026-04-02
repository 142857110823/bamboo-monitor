"""
熊猫小助手 - 悬浮AI聊天组件
使用 st.html(unsafe_allow_javascript=True) 直接注入页面 DOM（非 iframe）。
兼容 Streamlit Cloud (HTTPS) 和本地 (HTTP) 部署。
"""
import os
import base64
import streamlit as st

_AVATAR_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "panda_avatar.png")


def _get_avatar_data_uri():
    if os.path.exists(_AVATAR_PATH):
        with open(_AVATAR_PATH, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    return ""


_COMPONENT_HTML = """
<style>
/* ===== 熊猫小助手容器 ===== */
#panda-assistant {
    position: fixed;
    top: 60px; right: 30px;
    z-index: 999999;
    user-select: none;
    font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
}

/* ===== 头像 ===== */
#panda-avatar-btn {
    width: 64px; height: 64px;
    border-radius: 12px;
    cursor: grab;
    transition: transform 0.2s, box-shadow 0.2s;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    background: #fff;
    padding: 3px;
    display: block;
    border: 2px solid #4CAF50;
    object-fit: cover;
}
#panda-avatar-btn:hover {
    transform: scale(1.08);
    box-shadow: 0 6px 20px rgba(0,0,0,0.25);
}

/* ===== 招呼气泡 ===== */
#panda-greeting {
    position: absolute;
    top: 8px; right: 80px;
    background: #2E7D32;
    color: #fff;
    padding: 8px 14px;
    border-radius: 12px;
    font-size: 13px;
    white-space: nowrap;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    opacity: 0;
    animation: pandaGreetIn 0.4s ease 0.8s forwards;
    pointer-events: none;
}
#panda-greeting::after {
    content: '';
    position: absolute;
    top: 50%; right: -6px;
    transform: translateY(-50%);
    border-top: 6px solid transparent;
    border-bottom: 6px solid transparent;
    border-left: 6px solid #2E7D32;
}
@keyframes pandaGreetIn {
    from { opacity: 0; transform: translateX(10px); }
    to   { opacity: 1; transform: translateX(0); }
}

/* ===== 聊天面板 ===== */
#panda-chat-panel {
    display: none;
    position: absolute;
    top: 80px; right: 0;
    width: 340px;
    max-height: 480px;
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.18);
    overflow: hidden;
    flex-direction: column;
}
#panda-chat-panel.open { display: flex; }
#panda-chat-panel::after {
    content: '';
    position: absolute;
    top: -8px; right: 24px;
    border-left: 8px solid transparent;
    border-right: 8px solid transparent;
    border-bottom: 8px solid #2E7D32;
}

#panda-chat-header {
    background: linear-gradient(135deg, #2E7D32, #66BB6A);
    color: #fff;
    padding: 12px 16px;
    font-size: 15px;
    font-weight: bold;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
}
#panda-status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #aaa;
    display: inline-block;
}
#panda-status-dot.online { background: #4CAF50; }
#panda-status-dot.offline { background: #f44336; }
#panda-close-btn {
    margin-left: auto;
    background: none; border: none;
    color: #fff; font-size: 18px;
    cursor: pointer; opacity: 0.8;
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
}
#panda-chat-input:focus { border-color: #4CAF50; }
#panda-chat-send {
    padding: 8px 18px;
    border: none;
    border-radius: 20px;
    background: #2E7D32;
    color: #fff;
    cursor: pointer;
    font-size: 13px;
    font-weight: bold;
}
#panda-chat-send:hover { background: #1B5E20; }
#panda-chat-send:disabled { background: #bbb; cursor: not-allowed; }
</style>

<div id="panda-assistant">
    <div id="panda-chat-panel">
        <div id="panda-chat-header">
            <span>&#x1F43C; 熊猫小助手</span>
            <span id="panda-status-dot" title="状态"></span>
            <button id="panda-close-btn">&#x2715;</button>
        </div>
        <div id="panda-chat-messages">
            <div class="panda-msg system">你好！我是熊猫小助手，有关大熊猫主食竹监测的问题都可以问我哦~</div>
        </div>
        <div id="panda-chat-input-area">
            <input type="text" id="panda-chat-input" placeholder="输入你的问题..." />
            <button id="panda-chat-send">发送</button>
        </div>
    </div>
    <div id="panda-greeting">嗷呜，本熊已上线。请问有需要帮忙的吗</div>
    <img id="panda-avatar-btn" src="%%AVATAR%%" alt="熊猫小助手" draggable="false" />
</div>

<script>
(function() {
    // 使用页面路径作为唯一标识，确保每个页面都能独立初始化
    var pageId = location.pathname.replace(/[^a-zA-Z0-9]/g, '_');
    var initFlag = '_pandaAssistantInit_' + pageId;
    
    // 检查当前页面是否已初始化
    if (window[initFlag]) {
        console.log('熊猫小助手：当前页面已初始化，跳过 - 页面ID: ' + pageId);
        return;
    }
    
    // DOM加载检测和初始化函数
    function initPandaAssistant() {
        var assistant = document.getElementById('panda-assistant');
        var avatarBtn = document.getElementById('panda-avatar-btn');
        
        // 确保DOM元素存在
        if (!assistant || !avatarBtn) {
            console.log('熊猫小助手：DOM元素未找到，延迟重试 - 页面ID: ' + pageId);
            return false;
        }
        
        // 标记为已初始化
        window[initFlag] = true;
        console.log('熊猫小助手：初始化开始 - 页面ID: ' + pageId);
        
        // 获取其他DOM元素
        var panel     = document.getElementById('panda-chat-panel');
        var closeBtn  = document.getElementById('panda-close-btn');
        var msgBox    = document.getElementById('panda-chat-messages');
        var chatInput = document.getElementById('panda-chat-input');
        var sendBtn   = document.getElementById('panda-chat-send');
        var statusDot = document.getElementById('panda-status-dot');
        var greeting  = document.getElementById('panda-greeting');

        var LLM_URL = 'http://127.0.0.1:8000/v1/chat/completions';
        var isHTTPS = (location.protocol === 'https:');
        var llmOK = false;
        var chatHist = [];

        var KB = [
            {k:['你好','嗨','hello','hi','在吗'], a:'你好呀！我是熊猫小助手，有关大熊猫主食竹监测的问题都可以问我哦~'},
            {k:['你是谁','介绍','自我介绍','什么'], a:'我是熊猫小助手，运行在大熊猫主食竹智能监测与决策支持系统中。我可以回答关于竹林监测、大熊猫保护、遥感分析等方面的问题。'},
            {k:['竹林','竹子','主食竹','bamboo'], a:'大熊猫的主食竹主要包括箭竹、缺苞箭竹和华西箭竹等。本系统通过遥感影像分析竹林的时空分布变化，利用双时相NDVI特征区分竹林的常绿特性。'},
            {k:['大熊猫','熊猫','panda','保护'], a:'大熊猫是我国特有的珍稀濒危物种，被誉为"国宝"。竹子占大熊猫食物来源的99%以上，因此监测竹林资源对大熊猫栖息地保护至关重要。'},
            {k:['王朗','保护区','wanglang'], a:'王朗自然保护区位于四川省绵阳市平武县，是我国最早建立的大熊猫自然保护区之一，面积约322平方公里。'},
            {k:['ndvi','遥感','sentinel','卫星','影像'], a:'本系统采用Sentinel-2卫星多时相遥感影像，提取夏季和冬季NDVI作为特征。竹林在冬季仍保持较高NDVI值。'},
            {k:['模型','随机森林','分类','预测','算法'], a:'本系统采用随机森林分类器，包含100棵决策树，输入双时相NDVI特征，输出竹林/非竹林二分类结果。'},
            {k:['预警','退化','碎片化','风险','alert'], a:'系统会自动检测三类风险：1) 竹林退化预警；2) 低覆盖度预警；3) 碎片化预警。'},
            {k:['导出','下载','报告','export','tif','csv'], a:'数据导出页面支持多种格式：GeoTIFF、JPG图片、CSV/Excel统计报表、TXT分析报告。'},
            {k:['上传','分析','使用','怎么用','操作'], a:'使用步骤：1) 上传GeoTIFF影像；2) 系统自动执行竹林分类；3) 查看交互式地图；4) 查看预警；5) 导出结果。'},
            {k:['gee','google earth engine','地球引擎'], a:'Google Earth Engine是本系统数据预处理的核心平台。'},
            {k:['地图','folium','可视化','空间'], a:'交互式地图基于Folium构建，支持竹林分类结果叠加、保护区标记、预警标注和热力图。'},
            {k:['温度','气温','环境','气候','天气'], a:'大熊猫适宜的环境温度为5-25°C，竹林最佳生长温度为15-22°C，湿度60-80%。'},
            {k:['谢谢','感谢','thanks','thank'], a:'不客气！有任何关于竹林监测的问题随时问我。保护大熊猫，从保护竹林开始！'}
        ];

        function kbSearch(q) {
            var ql = q.toLowerCase();
            for (var i = 0; i < KB.length; i++)
                for (var j = 0; j < KB[i].k.length; j++)
                    if (ql.indexOf(KB[i].k[j]) !== -1) return KB[i].a;
            return '抱歉，这个问题超出了我的知识范围。\\n\\n你可以试试问我：竹林监测、大熊猫保护、NDVI遥感、模型算法、预警机制等话题。';
        }

        function checkLLM() {
            if (isHTTPS) { statusDot.className = 'online'; statusDot.title = '知识库模式'; return; }
            fetch(LLM_URL, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({model:'qwen', messages:[{role:'user',content:'ping'}], max_tokens:1})
            }).then(function(r) { llmOK = r.ok; statusDot.className = r.ok ? 'online' : 'offline'; })
              .catch(function() { llmOK = false; statusDot.className = 'offline'; });
        }
        checkLLM();

        var dragStartX, dragStartY, elemStartX, elemStartY, hasMoved;

        avatarBtn.addEventListener('mousedown', function(e) {
            e.preventDefault();
            dragStartX = e.clientX; dragStartY = e.clientY;
            var rect = assistant.getBoundingClientRect();
            elemStartX = rect.left; elemStartY = rect.top;
            hasMoved = false;
            function onMove(ev) {
                var dx = ev.clientX - dragStartX, dy = ev.clientY - dragStartY;
                if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
                    hasMoved = true;
                    var maxX = document.documentElement.clientWidth - assistant.offsetWidth;
                    var maxY = document.documentElement.clientHeight - assistant.offsetHeight;
                    assistant.style.left = Math.max(0, Math.min(elemStartX + dx, maxX)) + 'px';
                    assistant.style.top  = Math.max(0, Math.min(elemStartY + dy, maxY)) + 'px';
                    assistant.style.right = 'auto';
                }
            }
            function onUp() {
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
                avatarBtn.style.cursor = 'grab';
                if (!hasMoved) {
                    panel.classList.toggle('open');
                    if (panel.classList.contains('open')) {
                        greeting.style.display = 'none';
                        chatInput.focus();
                        checkLLM();
                    }
                }
            }
            avatarBtn.style.cursor = 'grabbing';
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
        });

        avatarBtn.addEventListener('touchstart', function(e) {
            var t = e.touches[0];
            dragStartX = t.clientX; dragStartY = t.clientY;
            var rect = assistant.getBoundingClientRect();
            elemStartX = rect.left; elemStartY = rect.top;
            hasMoved = false;
            function onTouchMove(ev) {
                var t2 = ev.touches[0];
                var dx = t2.clientX - dragStartX, dy = t2.clientY - dragStartY;
                if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
                    hasMoved = true;
                    assistant.style.left = (elemStartX + dx) + 'px';
                    assistant.style.top  = (elemStartY + dy) + 'px';
                    assistant.style.right = 'auto';
                }
            }
            function onTouchEnd() {
                document.removeEventListener('touchmove', onTouchMove);
                document.removeEventListener('touchend', onTouchEnd);
                if (!hasMoved) {
                    panel.classList.toggle('open');
                    if (panel.classList.contains('open')) {
                        greeting.style.display = 'none';
                        chatInput.focus();
                        checkLLM();
                    }
                }
            }
            document.addEventListener('touchmove', onTouchMove, {passive: true});
            document.addEventListener('touchend', onTouchEnd);
        }, {passive: true});

        closeBtn.addEventListener('click', function() { panel.classList.remove('open'); });

        function addMsg(text, cls) {
            var d = document.createElement('div');
            d.className = 'panda-msg ' + cls;
            d.textContent = text;
            msgBox.appendChild(d);
            msgBox.scrollTop = msgBox.scrollHeight;
            return d;
        }

        function handleSend() {
            var q = chatInput.value.trim();
            if (!q) return;
            chatInput.value = '';
            addMsg(q, 'user');
            sendBtn.disabled = true;
            var thinking = addMsg('正在思考...', 'bot');
            if (isHTTPS || !llmOK) {
                setTimeout(function() { thinking.textContent = kbSearch(q); sendBtn.disabled = false; }, 300);
                return;
            }
            chatHist.push({role:'user', content:q});
            var msgs = [{role:'system', content:'你是"熊猫小助手"，专注于大熊猫主食竹监测与保护的AI助手。请用简洁友好的中文回答，控制在200字以内。'}]
                .concat(chatHist.slice(-10));
            fetch(LLM_URL, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({model:'qwen', messages:msgs, temperature:0.7, max_tokens:512, stream:false})
            }).then(function(r) { if (!r.ok) throw new Error(); return r.json(); })
              .then(function(d) {
                var reply = (d.choices && d.choices[0] && d.choices[0].message) ? d.choices[0].message.content : '抱歉，暂时无法回答。';
                thinking.textContent = reply;
                chatHist.push({role:'assistant', content:reply});
                statusDot.className = 'online';
            }).catch(function() {
                thinking.textContent = kbSearch(q); llmOK = false; statusDot.className = 'offline'; chatHist.pop();
            }).finally(function() { sendBtn.disabled = false; msgBox.scrollTop = msgBox.scrollHeight; });
        }

        sendBtn.addEventListener('click', handleSend);
        chatInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
        });

        setTimeout(function() {
            greeting.style.transition = 'opacity 0.5s';
            greeting.style.opacity = '0';
            setTimeout(function() { greeting.style.display = 'none'; }, 500);
        }, 7000);
        
        // 页面卸载时清理状态，确保下次访问能正确初始化
        window.addEventListener('beforeunload', function() {
            window[initFlag] = false;
            console.log('熊猫小助手：页面卸载，清理状态 - 页面ID: ' + pageId);
        });
        
        console.log('熊猫小助手：初始化完成 - 页面ID: ' + pageId);
        return true;
    }
    
    // 立即尝试初始化
    if (!initPandaAssistant()) {
        // 如果失败，延迟重试（最多重试5次）
        var retryCount = 0;
        var maxRetries = 5;
        var retryInterval = setInterval(function() {
            retryCount++;
            if (initPandaAssistant() || retryCount >= maxRetries) {
                clearInterval(retryInterval);
                if (retryCount >= maxRetries) {
                    console.log('熊猫小助手：达到最大重试次数，初始化失败 - 页面ID: ' + pageId);
                }
            }
        }, 500); // 每500ms重试一次
    }
})();
</script>
"""


def render_panda_assistant():
    """在 Streamlit 页面中注入悬浮熊猫小助手 AI 聊天组件。"""
    avatar_uri = _get_avatar_data_uri()
    if not avatar_uri:
        return
    html = _COMPONENT_HTML.replace("%%AVATAR%%", avatar_uri)
    st.html(html, unsafe_allow_javascript=True)
