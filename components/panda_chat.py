"""
熊猫小助手 - 悬浮AI聊天组件
通过 st.markdown(unsafe_allow_html=True) 直接注入到 Streamlit 页面，
不依赖 iframe，兼容 Streamlit Cloud (HTTPS) 和本地 (HTTP) 部署。
"""
import os
import base64
import streamlit as st

_AVATAR_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "panda_avatar.png")


def _get_avatar_data_uri():
    """读取熊猫头像图片并返回 base64 data URI。"""
    if os.path.exists(_AVATAR_PATH):
        with open(_AVATAR_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{b64}"
    return "https://img.icons8.com/emoji/96/panda-emoji.png"


def render_panda_assistant():
    """在Streamlit页面中注入悬浮熊猫小助手AI聊天组件。"""
    avatar_uri = _get_avatar_data_uri()

    html = f'''
<style>
#panda-assistant {{
    position: fixed;
    top: 60px;
    right: 30px;
    z-index: 99999;
    user-select: none;
    font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
}}
#panda-avatar-btn {{
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
}}
#panda-avatar-btn:hover {{
    transform: scale(1.08);
    box-shadow: 0 6px 20px rgba(0,0,0,0.25);
}}
#panda-chat-panel {{
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
}}
#panda-chat-panel.open {{
    display: flex;
}}
#panda-chat-header {{
    background: linear-gradient(135deg, #2E7D32, #66BB6A);
    color: #fff;
    padding: 14px 16px;
    font-size: 15px;
    font-weight: bold;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
}}
#panda-close-btn {{
    margin-left: auto;
    cursor: pointer;
    font-size: 18px;
    opacity: 0.8;
    transition: opacity 0.2s;
    background: none;
    border: none;
    color: #fff;
    padding: 0 4px;
}}
#panda-close-btn:hover {{ opacity: 1; }}
#panda-chat-messages {{
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    background: #f5f9f5;
    min-height: 200px;
    max-height: 320px;
}}
.panda-msg {{
    margin: 6px 0;
    padding: 10px 14px;
    border-radius: 14px;
    font-size: 13px;
    line-height: 1.6;
    max-width: 88%;
    word-break: break-word;
}}
.panda-msg.user {{
    background: #e3f2fd;
    margin-left: auto;
    border-bottom-right-radius: 4px;
}}
.panda-msg.bot {{
    background: #fff;
    border: 1px solid #e0e0e0;
    border-bottom-left-radius: 4px;
}}
.panda-msg.system {{
    background: #e8f5e9;
    text-align: center;
    font-size: 12px;
    color: #555;
    max-width: 100%;
    border-radius: 8px;
}}
.panda-msg.error {{
    background: #fff3e0;
    text-align: center;
    font-size: 12px;
    color: #e65100;
    max-width: 100%;
    border-radius: 8px;
}}
#panda-chat-input-area {{
    display: flex;
    padding: 10px 12px;
    gap: 8px;
    border-top: 1px solid #e8e8e8;
    background: #fff;
    flex-shrink: 0;
}}
#panda-chat-input {{
    flex: 1;
    padding: 10px 14px;
    border: 1px solid #ddd;
    border-radius: 20px;
    outline: none;
    font-size: 13px;
    transition: border-color 0.2s;
}}
#panda-chat-input:focus {{
    border-color: #4CAF50;
}}
#panda-chat-send {{
    padding: 8px 18px;
    border: none;
    border-radius: 20px;
    background: #2E7D32;
    color: #fff;
    cursor: pointer;
    font-size: 13px;
    font-weight: bold;
    transition: background 0.2s;
}}
#panda-chat-send:hover {{ background: #1B5E20; }}
#panda-chat-send:disabled {{
    background: #bbb;
    cursor: not-allowed;
}}
#panda-chat-panel::after {{
    content: '';
    position: absolute;
    top: -8px;
    right: 28px;
    border-left: 8px solid transparent;
    border-right: 8px solid transparent;
    border-bottom: 8px solid #2E7D32;
}}
#panda-status-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #aaa;
    display: inline-block;
    margin-left: 4px;
}}
#panda-status-dot.online {{ background: #4CAF50; }}
#panda-status-dot.offline {{ background: #f44336; }}
#panda-greeting {{
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
}}
#panda-greeting::after {{
    content: '';
    position: absolute;
    top: 50%;
    right: -6px;
    transform: translateY(-50%);
    border-top: 6px solid transparent;
    border-bottom: 6px solid transparent;
    border-left: 6px solid #2E7D32;
}}
@keyframes pandaGreetIn {{
    from {{ opacity: 0; transform: translateX(10px); }}
    to {{ opacity: 1; transform: translateX(0); }}
}}
@keyframes pandaGreetOut {{
    from {{ opacity: 1; }}
    to {{ opacity: 0; }}
}}
</style>

<div id="panda-assistant">
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
    <img id="panda-avatar-btn" src="{avatar_uri}" alt="&#x718A;&#x732B;&#x5C0F;&#x52A9;&#x624B;" draggable="false" />
</div>

<script>
(function() {{
    // 避免重复绑定
    if (window._pandaAssistantInit) return;
    window._pandaAssistantInit = true;

    var assistant = document.getElementById('panda-assistant');
    var avatarBtn = document.getElementById('panda-avatar-btn');
    var panel = document.getElementById('panda-chat-panel');
    var closeBtn = document.getElementById('panda-close-btn');
    var msgBox = document.getElementById('panda-chat-messages');
    var chatInput = document.getElementById('panda-chat-input');
    var sendBtn = document.getElementById('panda-chat-send');
    var statusDot = document.getElementById('panda-status-dot');

    if (!assistant || !avatarBtn) return;

    // ===== 配置 =====
    var LLM_API_URL = "http://localhost:8000/v1/chat/completions";
    var MODEL_NAME = "Qwen-1_8B-Chat";
    var SYSTEM_PROMPT = "\u4f60\u662f'\u718a\u732b\u5c0f\u52a9\u624b'\uff0c\u4e00\u4e2a\u4e13\u6ce8\u4e8e\u5927\u718a\u732b\u4e3b\u98df\u7af9\u76d1\u6d4b\u4e0e\u4fdd\u62a4\u7684AI\u52a9\u624b\u3002\u8bf7\u7528\u7b80\u6d01\u53cb\u597d\u7684\u4e2d\u6587\u56de\u7b54\u7528\u6237\u5173\u4e8e\u7af9\u6797\u76d1\u6d4b\u3001\u5927\u718a\u732b\u4fdd\u62a4\u3001\u9065\u611f\u5206\u6790\u7b49\u65b9\u9762\u7684\u95ee\u9898\u3002\u56de\u7b54\u63a7\u5236\u5728200\u5b57\u4ee5\u5185\u3002";
    var chatHistory = [];
    var isHTTPS = location.protocol === 'https:';

    // ===== 离线知识库 =====
    var KB = [
        {{ keys: ['\u4f60\u597d','\u55e8','hello','hi','\u5728\u5417'], answer: '\u4f60\u597d\u5440\uff01\u6211\u662f\u718a\u732b\u5c0f\u52a9\u624b\uff0c\u6709\u5173\u5927\u718a\u732b\u4e3b\u98df\u7af9\u76d1\u6d4b\u7684\u95ee\u9898\u90fd\u53ef\u4ee5\u95ee\u6211\u54e6~' }},
        {{ keys: ['\u4f60\u662f\u8c01','\u4ecb\u7ecd','\u81ea\u6211\u4ecb\u7ecd','\u4ec0\u4e48'], answer: '\u6211\u662f\u718a\u732b\u5c0f\u52a9\u624b\uff0c\u8fd0\u884c\u5728\u5927\u718a\u732b\u4e3b\u98df\u7af9\u667a\u80fd\u76d1\u6d4b\u4e0e\u51b3\u7b56\u652f\u6301\u7cfb\u7edf\u4e2d\u3002\u6211\u53ef\u4ee5\u56de\u7b54\u5173\u4e8e\u7af9\u6797\u76d1\u6d4b\u3001\u5927\u718a\u732b\u4fdd\u62a4\u3001\u9065\u611f\u5206\u6790\u7b49\u65b9\u9762\u7684\u95ee\u9898\u3002' }},
        {{ keys: ['\u7af9\u6797','\u7af9\u5b50','\u4e3b\u98df\u7af9','bamboo'], answer: '\u5927\u718a\u732b\u7684\u4e3b\u98df\u7af9\u4e3b\u8981\u5305\u62ec\u7bad\u7af9\u3001\u7f3a\u82de\u7bad\u7af9\u548c\u534e\u897f\u7bad\u7af9\u7b49\u3002\u672c\u7cfb\u7edf\u901a\u8fc7\u9065\u611f\u5f71\u50cf\u5206\u6790\u7af9\u6797\u7684\u65f6\u7a7a\u5206\u5e03\u53d8\u5316\uff0c\u76ee\u524d\u76d1\u6d4b\u533a\u57df\u4e3a\u738b\u6717\u81ea\u7136\u4fdd\u62a4\u533a\uff0c\u5229\u7528\u53cc\u65f6\u76f8NDVI\u7279\u5f81\u533a\u5206\u7af9\u6797\u7684\u5e38\u7eff\u7279\u6027\u3002' }},
        {{ keys: ['\u5927\u718a\u732b','\u718a\u732b','panda','\u4fdd\u62a4'], answer: '\u5927\u718a\u732b\u662f\u6211\u56fd\u7279\u6709\u7684\u73cd\u7a00\u6fd2\u5371\u7269\u79cd\uff0c\u88ab\u8a89\u4e3a\u201c\u56fd\u5b9d\u201d\u3002\u7af9\u5b50\u5360\u5927\u718a\u732b\u98df\u7269\u6765\u6e90\u768499%\u4ee5\u4e0a\uff0c\u56e0\u6b64\u76d1\u6d4b\u7af9\u6797\u8d44\u6e90\u5bf9\u5927\u718a\u732b\u6816\u606f\u5730\u4fdd\u62a4\u81f3\u5173\u91cd\u8981\u3002\u672c\u7cfb\u7edf\u53ef\u81ea\u52a8\u8bc6\u522b\u7af9\u6797\u9000\u5316\u3001\u788e\u7247\u5316\u7b49\u98ce\u9669\u3002' }},
        {{ keys: ['\u738b\u6717','\u4fdd\u62a4\u533a','wanglang'], answer: '\u738b\u6717\u81ea\u7136\u4fdd\u62a4\u533a\u4f4d\u4e8e\u56db\u5ddd\u7701\u7ef5\u9633\u5e02\u5e73\u6b66\u53bf\uff0c\u662f\u6211\u56fd\u6700\u65e9\u5efa\u7acb\u7684\u5927\u718a\u732b\u81ea\u7136\u4fdd\u62a4\u533a\u4e4b\u4e00\uff0c\u9762\u79ef\u7ea6322\u5e73\u65b9\u516c\u91cc\u3002\u4fdd\u62a4\u533a\u5185\u6709\u4e30\u5bcc\u7684\u7af9\u6797\u8d44\u6e90\uff0c\u662f\u5927\u718a\u732b\u91cd\u8981\u7684\u6816\u606f\u5730\u3002' }},
        {{ keys: ['ndvi','\u9065\u611f','sentinel','\u536b\u661f','\u5f71\u50cf'], answer: '\u672c\u7cfb\u7edf\u91c7\u7528Sentinel-2\u536b\u661f\u591a\u65f6\u76f8\u9065\u611f\u5f71\u50cf\uff0c\u63d0\u53d6\u590f\u5b63\u548c\u51ac\u5b63NDVI\u4f5c\u4e3a\u7279\u5f81\u3002\u7af9\u6797\u5728\u51ac\u5b63\u4ecd\u4fdd\u6301\u8f83\u9ad8NDVI\u503c\uff08\u5e38\u7eff\u7279\u6027\uff09\uff0c\u800c\u843d\u53f6\u6797NDVI\u663e\u8457\u4e0b\u964d\uff0c\u5229\u7528\u8fd9\u4e00\u5dee\u5f02\u53ef\u6709\u6548\u533a\u5206\u7af9\u6797\u3002' }},
        {{ keys: ['\u6a21\u578b','\u968f\u673a\u68ee\u6797','\u5206\u7c7b','\u9884\u6d4b','\u7b97\u6cd5'], answer: '\u672c\u7cfb\u7edf\u91c7\u7528\u968f\u673a\u68ee\u6797\u5206\u7c7b\u5668\uff0c\u5305\u542b100\u68f5\u51b3\u7b56\u6811\uff0c\u8f93\u5165\u53cc\u65f6\u76f8NDVI\u7279\u5f81\uff0c\u8f93\u51fa\u7af9\u6797/\u975e\u7af9\u6797\u4e8c\u5206\u7c7b\u7ed3\u679c\u3002\u6a21\u578b\u5728\u9a8c\u8bc1\u96c6\u4e0a\u8868\u73b0\u826f\u597d\uff0c\u9002\u7528\u4e8e\u5927\u9762\u79ef\u7af9\u6797\u8d44\u6e90\u5feb\u901f\u76d1\u6d4b\u3002' }},
        {{ keys: ['\u9884\u8b66','\u9000\u5316','\u788e\u7247\u5316','\u98ce\u9669','alert'], answer: '\u7cfb\u7edf\u4f1a\u81ea\u52a8\u68c0\u6d4b\u4e09\u7c7b\u98ce\u9669\uff1a1) \u7af9\u6797\u9000\u5316\u9884\u8b66\uff1b2) \u4f4e\u8986\u76d6\u5ea6\u9884\u8b66\uff1b3) \u788e\u7247\u5316\u9884\u8b66\u3002\u6bcf\u6761\u9884\u8b66\u5305\u542b\u4f4d\u7f6e\u3001\u5f71\u54cd\u9762\u79ef\u548c\u5de1\u62a4\u5efa\u8bae\u3002' }},
        {{ keys: ['\u5bfc\u51fa','\u4e0b\u8f7d','\u62a5\u544a','export','tif','csv'], answer: '\u6570\u636e\u5bfc\u51fa\u9875\u9762\u652f\u6301\u591a\u79cd\u683c\u5f0f\uff1aGeoTIFF\u3001JPG\u56fe\u7247\u3001CSV/Excel\u7edf\u8ba1\u62a5\u8868\u3001TXT\u5206\u6790\u62a5\u544a\u3002\u6240\u6709\u6587\u4ef6\u5747\u5305\u542b\u5206\u6790\u65f6\u95f4\u548c\u6a21\u578b\u7248\u672c\u4fe1\u606f\u3002' }},
        {{ keys: ['\u4e0a\u4f20','\u5206\u6790','\u4f7f\u7528','\u600e\u4e48\u7528','\u64cd\u4f5c'], answer: '\u4f7f\u7528\u6b65\u9aa4\uff1a1) \u5728\u201c\u6570\u636e\u4e0a\u4f20\u4e0e\u5206\u6790\u201d\u9875\u9762\u4e0a\u4f20GeoTIFF\u5f71\u50cf\uff1b2) \u7cfb\u7edf\u81ea\u52a8\u6267\u884c\u7af9\u6797\u5206\u7c7b\uff1b3) \u5728\u201c\u4ea4\u4e92\u5f0f\u5730\u56fe\u201d\u67e5\u770b\u7a7a\u95f4\u5206\u5e03\uff1b4) \u5728\u201c\u9884\u8b66\u4e0e\u4efb\u52a1\u201d\u67e5\u770b\u98ce\u9669\u533a\u57df\uff1b5) \u5728\u201c\u6570\u636e\u5bfc\u51fa\u201d\u4e0b\u8f7d\u7ed3\u679c\u3002' }},
        {{ keys: ['gee','google earth engine','\u5730\u7403\u5f15\u64ce'], answer: 'Google Earth Engine\u662f\u672c\u7cfb\u7edf\u6570\u636e\u9884\u5904\u7406\u7684\u6838\u5fc3\u5e73\u53f0\uff0c\u7528\u4e8e\u83b7\u53d6\u548c\u5904\u7406Sentinel-2\u591a\u65f6\u76f8\u9065\u611f\u5f71\u50cf\uff0c\u751f\u6210\u53cc\u65f6\u76f8NDVI\u5408\u6210\u7279\u5f81\u3002' }},
        {{ keys: ['\u5730\u56fe','folium','\u53ef\u89c6\u5316','\u7a7a\u95f4'], answer: '\u4ea4\u4e92\u5f0f\u5730\u56fe\u57fa\u4e8eFolium\u6784\u5efa\uff0c\u652f\u6301\uff1a\u7af9\u6797\u5206\u7c7b\u7ed3\u679c\u53e0\u52a0\u663e\u793a\u3001\u4fdd\u62a4\u533a\u6807\u8bb0\u3001\u9884\u8b66\u4f4d\u7f6e\u6807\u6ce8\u3001\u70ed\u529b\u56fe\u5c55\u793a\u7af9\u6797\u5bc6\u5ea6\u5206\u5e03\u3002\u652f\u6301\u56fe\u5c42\u63a7\u5236\u548c\u591a\u79cd\u5e95\u56fe\u5207\u6362\u3002' }},
        {{ keys: ['\u8c22\u8c22','\u611f\u8c22','thanks','thank'], answer: '\u4e0d\u5ba2\u6c14\uff01\u6709\u4efb\u4f55\u5173\u4e8e\u7af9\u6797\u76d1\u6d4b\u7684\u95ee\u9898\u968f\u65f6\u95ee\u6211\u3002\u4fdd\u62a4\u5927\u718a\u732b\uff0c\u4ece\u4fdd\u62a4\u7af9\u6797\u5f00\u59cb\uff01' }}
    ];
    function kbSearch(q) {{
        var ql = q.toLowerCase();
        for (var i = 0; i < KB.length; i++) {{
            for (var j = 0; j < KB[i].keys.length; j++) {{
                if (ql.indexOf(KB[i].keys[j]) !== -1) return KB[i].answer;
            }}
        }}
        return '\u62b1\u6b49\uff0c\u8fd9\u4e2a\u95ee\u9898\u8d85\u51fa\u4e86\u6211\u7684\u77e5\u8bc6\u8303\u56f4\u3002\\n\\n\u4f60\u53ef\u4ee5\u8bd5\u8bd5\u95ee\u6211\uff1a\u7af9\u6797\u76d1\u6d4b\u3001\u5927\u718a\u732b\u4fdd\u62a4\u3001NDVI\u9065\u611f\u3001\u6a21\u578b\u7b97\u6cd5\u3001\u9884\u8b66\u673a\u5236\u3001\u6570\u636e\u5bfc\u51fa\u7b49\u8bdd\u9898\u3002';
    }}

    // ===== 检测模型服务状态 =====
    var llmAvailable = false;
    function checkStatus() {{
        if (isHTTPS) {{
            statusDot.className = 'online';
            statusDot.title = '\u77e5\u8bc6\u5e93\u6a21\u5f0f';
            return;
        }}
        fetch(LLM_API_URL, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ model: MODEL_NAME, messages: [{{ role: 'user', content: 'ping' }}], max_tokens: 1 }})
        }}).then(function(resp) {{
            llmAvailable = resp.ok;
            statusDot.className = resp.ok ? 'online' : 'offline';
        }}).catch(function() {{
            llmAvailable = false;
            statusDot.className = 'offline';
        }});
    }}
    checkStatus();

    // ===== 拖拽 + 点击 =====
    var dragStartX, dragStartY, elemStartX, elemStartY, hasMoved;

    avatarBtn.addEventListener('mousedown', function(e) {{
        e.preventDefault();
        dragStartX = e.clientX;
        dragStartY = e.clientY;
        var rect = assistant.getBoundingClientRect();
        elemStartX = rect.left;
        elemStartY = rect.top;
        hasMoved = false;

        function onMove(ev) {{
            var dx = ev.clientX - dragStartX;
            var dy = ev.clientY - dragStartY;
            if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {{
                hasMoved = true;
                var maxX = document.documentElement.clientWidth - assistant.offsetWidth;
                var maxY = document.documentElement.clientHeight - assistant.offsetHeight;
                assistant.style.left = Math.max(0, Math.min(elemStartX + dx, maxX)) + 'px';
                assistant.style.top = Math.max(0, Math.min(elemStartY + dy, maxY)) + 'px';
                assistant.style.bottom = 'auto';
                assistant.style.right = 'auto';
            }}
        }}

        function onUp() {{
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            if (!hasMoved) {{
                panel.classList.toggle('open');
                if (panel.classList.contains('open')) {{
                    chatInput.focus();
                    checkStatus();
                }}
            }}
        }}

        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    }});

    closeBtn.addEventListener('click', function() {{
        panel.classList.remove('open');
    }});

    // ===== 消息渲染 =====
    function addMsg(text, cls) {{
        var d = document.createElement('div');
        d.className = 'panda-msg ' + cls;
        d.textContent = text;
        msgBox.appendChild(d);
        msgBox.scrollTop = msgBox.scrollHeight;
        return d;
    }}

    // ===== 发送消息 =====
    function sendMessage() {{
        var q = chatInput.value.trim();
        if (!q) return;

        chatInput.value = '';
        addMsg(q, 'user');
        sendBtn.disabled = true;

        var thinking = addMsg('\u6b63\u5728\u601d\u8003...', 'bot');

        if (isHTTPS || !llmAvailable) {{
            thinking.textContent = kbSearch(q);
            sendBtn.disabled = false;
            msgBox.scrollTop = msgBox.scrollHeight;
            return;
        }}

        chatHistory.push({{ role: 'user', content: q }});

        var messages = [{{ role: 'system', content: SYSTEM_PROMPT }}].concat(chatHistory.slice(-10));

        fetch(LLM_API_URL, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ model: MODEL_NAME, messages: messages, temperature: 0.7, max_tokens: 512, stream: false }})
        }}).then(function(resp) {{
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            return resp.json();
        }}).then(function(data) {{
            var reply = (data.choices && data.choices[0] && data.choices[0].message)
                ? data.choices[0].message.content
                : '\u62b1\u6b49\uff0c\u6211\u6682\u65f6\u65e0\u6cd5\u56de\u7b54\u8fd9\u4e2a\u95ee\u9898\u3002';
            thinking.textContent = reply;
            chatHistory.push({{ role: 'assistant', content: reply }});
            statusDot.className = 'online';
        }}).catch(function() {{
            thinking.textContent = kbSearch(q);
            thinking.className = 'panda-msg bot';
            llmAvailable = false;
            statusDot.className = 'offline';
            chatHistory.pop();
        }}).finally(function() {{
            sendBtn.disabled = false;
            msgBox.scrollTop = msgBox.scrollHeight;
        }});
    }}

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', function(e) {{
        if (e.key === 'Enter' && !e.shiftKey) {{
            e.preventDefault();
            sendMessage();
        }}
    }});
}})();
</script>
'''

    st.markdown(html, unsafe_allow_html=True)
