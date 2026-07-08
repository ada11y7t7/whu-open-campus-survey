# 武大开放入校政策调研 · 在线问卷

## 文件说明

| 文件 | 用途 |
|------|------|
| `survey.html` | 问卷网页，包含全部逻辑（分层抽题、条件跳转、身份路由） |
| `backend.py` | Flask 后端，接收并存储答卷数据 |
| `requirements.txt` | Python 依赖 |
| `survey_responses.jsonl` | 答卷数据文件（运行后端后自动生成） |

## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动后端

```bash
python backend.py
```

服务器运行在 `http://localhost:5000`。

### 3. 打开问卷

**本地测试**：直接用浏览器打开 `survey.html`。  
不连后端也能正常填写——提交时数据会保存在浏览器 localStorage 中，不会丢失。

**连接后端**：在 `survey.html` 开头加上：
```html
<script>window.SURVEY_BACKEND_URL = 'http://你的服务器IP:5000';</script>
```

### 4. 分享出去

如果想让别人通过微信 / 浏览器填写，需要把 `survey.html` 部署到公网可访问的地址。几个方案：

| 方案 | 难度 | 说明 |
|------|------|------|
| **ngrok 内网穿透** | 低 | 本地运行 `ngrok http 5000`，获得公网 URL，把 `survey.html` 放到 Flask 的 static 目录即可 |
| **校园服务器** | 中 | 部署到学校提供的服务器上 |
| **Vercel / Cloudflare Pages** | 中 | 静态托管 `survey.html`，后端另部署或使用 serverless |

### 部署到 Flask 的静态目录（推荐最简单方案）

修改 `backend.py`，在文件头部加入：

```python
from flask import send_from_directory

@app.route('/')
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'survey.html')
```

然后访问 `http://你的IP:5000/` 就是问卷页面，提交自动走同源后端。

## 接口说明

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/submit` | 提交问卷（JSON body） |
| GET | `/api/stats` | 查看已收集答卷数 |
| GET | `/api/export` | 导出全部答卷为 JSON |

## 数据格式

每份答卷存储为一行 JSON：

```json
{
  "submitted_at": "2026-07-08T12:00:00.000Z",
  "received_at": "2026-07-08T12:00:01.000Z",
  "answers": {
    "Q1": "武汉大学本科生",
    "Q2": "21",
    "Q3": "男",
    "Q4": "是",
    "A3": "偶尔",
    "B1": "比较支持",
    "C1": "没变化",
    "D2": ["网络直播", "大规模聚集拍照"],
    "E2": ["参观校园风光", "拍照打卡"],
    "F1": "略利于弊",
    "C2": "略有变差",
    "G1": "食堂比以前挤了很多",
    "G2": "建议周末限流"
  },
  "ua_explanations": {},
  "meta": {
    "questions_shown": ["Q1","Q2","Q3","Q4","A3","B1","C1","D2","E2","F1","C2","G1","G2"],
    "c2_shown": true
  }
}
```

## 问卷逻辑概要

- **分层随机抽题**：A~F 六个维度各随机抽 1 题，共 6 题
- **E 维度身份路由**：本科生/研究生/教职工 → E2（观察公众视角）；社会公众/校友/其他 → E1（自述来访目的）
- **C2 条件跳转**：仅 Q4 选"是"（开放前来过）者可见
- **"无法回答"兜底**：每道选择题末尾均有，选中后可填选说明
- **C1 追问**：若选"减少"，追问原因
