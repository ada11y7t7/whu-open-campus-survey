# 部署到 PythonAnywhere（免费 · 永久 URL）

PythonAnywhere 免费套餐提供：
- 永久 URL：`https://你的用户名.pythonanywhere.com`
- 文件持久保存（不会因重启丢失数据）
- 国内可正常访问
- 无需信用卡，仅需邮箱注册

---

## 第一步：注册

1. 打开 [pythonanywhere.com](https://www.pythonanywhere.com)
2. 点击 **"Start running Python online"** → **"Create a Beginner account"**
3. 填写用户名、邮箱、密码（用户名会出现在 URL 里，想个好记的）
4. 验证邮箱后登录

---

## 第二步：上传文件

1. 登录后进入 **"Files"** 标签页
2. 在左侧目录树中，进入 `/home/你的用户名/`
3. 点击 **"Open Bash console here"** 打开终端
4. 在终端中创建目录并上传文件：

**方式 A — 用 Git（推荐）**：
```bash
# 先把 survey 文件夹推送到 GitHub，然后在 PythonAnywhere 终端：
git clone https://github.com/你的用户名/你的仓库.git
```

**方式 B — 直接上传**：
在 Files 页面点击 **"Upload a file"**，逐一上传以下文件到 `/home/你的用户名/survey/`：
- `backend.py`
- `survey.html`
- `survey_qr.png`
- `report_generator.py`
- `generate_qr.py`
- `requirements.txt`

5. 安装依赖：
```bash
pip install --user flask flask-cors
```

---

## 第三步：配置 Web 应用

1. 进入 **"Web"** 标签页
2. 点击 **"Add a new web app"**
3. 域名选默认的 `你的用户名.pythonanywhere.com` → Next
4. 框架选 **"Flask"**
5. Python 版本选 **Python 3.10**（或最新可用版本）
6. Flask 项目路径填：`/home/你的用户名/survey`
7. 点击 **"Next"** → 完成创建

---

## 第四步：修改 WSGI 配置

在 Web 标签页找到 **"Code"** 部分，点击 WSGI 配置文件的链接（通常是 `/var/www/你的用户名_pythonanywhere_com_wsgi.py`）。

**删掉文件里所有内容**，替换为：

```python
import sys

# 把项目目录加入 Python 搜索路径
project_dir = '/home/你的用户名/survey'
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# 从 backend.py 导入 Flask app
from backend import app as application
```

保存文件（Ctrl+S 或点击 Save）。

---

## 第五步：启动

在 Web 标签页顶部，点击绿色 **"Reload"** 按钮。

稍等几秒后，访问 `https://你的用户名.pythonanywhere.com` 就能看到问卷了。

---

## 验证

| 地址 | 内容 |
|------|------|
| `https://你的用户名.pythonanywhere.com/` | 问卷页面 |
| `https://你的用户名.pythonanywhere.com/qr` | 二维码展示页 |
| `https://你的用户名.pythonanywhere.com/api/stats` | 答卷数量 |
| `https://你的用户名.pythonanywhere.com/api/export` | 导出全部数据 |

---

## 更新二维码

部署成功后，在本地运行以下命令，用永久 URL 重新生成二维码：

```bash
python generate_qr.py "https://你的用户名.pythonanywhere.com"
```

然后用这张新二维码去分发。

---

## 数据备份

PythonAnywhere 免费套餐文件是持久保存的，但建议定期备份：

```bash
# 在 PythonAnywhere 终端运行
cp survey_responses.jsonl ~/backup_$(date +%Y%m%d).jsonl
```

或者定期在本地运行导出命令：

```bash
curl -o backup.json https://你的用户名.pythonanywhere.com/api/export
```

---

## 常见问题

**Q: 应用访问很慢？**
A: 免费套餐的 Web 应用在 3 个月不活跃后会被暂停。只要有人填问卷就会保持活跃。

**Q: URL 能自定义吗？**
A: 免费套餐只能用 `用户名.pythonanywhere.com`。付费套餐支持自定义域名。

**Q: 能同时用 localtunnel 和 PythonAnywhere 吗？**
A: 可以。本地开发时用 localtunnel 测试，正式分发用 PythonAnywhere。

---

## 替代方案

如果 PythonAnywhere 不可用，备选：

| 平台 | 特点 | 免费持久存储 |
|------|------|------------|
| [Render.com](https://render.com) | 更快的部署体验 | ❌ 免费版硬盘临时 |
| [Fly.io](https://fly.io) | 全球节点 | ✅ 3GB 永久卷 |
| 校园服务器 | 最稳定 | ✅ |
