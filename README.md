# AirShare - 基于 Python 的局域网加密共享服务 (HTTPS & PIN 加固)

一个极简、美观、采用 Apple 设计语言风格的局域网轻共享工具。**集成 TLS/HTTPS 链路加密与 Access Code 访问口令防护**，在保障传输隐私与安全的前提下，方便在手机、电脑和平板设备之间快速传输文本便签、截图和文件。

---

## 🔒 隐私与安全加固特性

1. **TLS / HTTPS 原生加密 (防中间人窃听/抓包)**
   - 无需安装配置 Nginx、Apache 或 Caddy！
   - 应用启动时使用标准 `cryptography` 库自动生成并保存长达 10 年有效的 TLS/SSL 自签名证书 (`certs/cert.pem` & `certs/key.pem`)。
   - 所有在局域网内传输的文本、截图与文件数据均为 end-to-end 密文传输。

2. **Apple 风格 Access Code 访问口令**
   - 默认访问口令为 **`8888`**（可通过环境变量 `SHARE_CODE` 自定义设置）。
   - 首次访问时弹窗提示输入口令，输入正确后自动记录在本地浏览器（LocalStorage）。
   - 后续访问无需重复输入；未验证或口令错误的请求均会被服务端拒绝（401 Unauthorized）。

---

## 🌟 核心功能

- 🎨 **Apple 设计风格**：SF Pro 字体排版、毛玻璃（Glassmorphism）视觉效果、流体分段控制与精致的 Toast 提示。
- 📝 **文本加密便签**：支持在线编辑、一键复制全文、快速清空与局域网多设备间自动定时同步。
- 📋 **剪贴板截图直接粘贴**：截图后直接按 `Cmd + V` / `Ctrl + V` 即可将剪贴板图片自动加密上传并展示。
- 📁 **拖拽与文件共享**：支持各种文件/图片拖拽上传，带缩略图预览、在线查看、下载与删除管理。
- ⚡ **默认 HTTPS 端口 10240**：启动自动探测打印 `https://<局域网IP>:10240` 访问链接。

---

## 📁 项目目录结构

```text
py_http_share/
├── app.py              # Flask 服务端（HTTPS SSL 配置 / PIN 鉴权 / REST API）
├── .env                # 环境变量配置（口令、端口等，不会提交到 Git）
├── certs/              # 自动生成的 TLS 证书与私钥目录 (cert.pem / key.pem)
├── templates/
│   └── index.html      # 前端界面（PIN 输入框 / 毛玻璃 UI / 剪贴板监听）
├── uploads/            # 存储上传的文件与图片
├── data/               # 存储共享便签数据
└── README.md           # 项目说明文档
```

---

## 🚀 快速开始与使用

### 1. 配置环境变量（推荐）

创建 `.env` 文件（已添加到 `.gitignore`，不会误提交）：

```bash
# 访问口令（必改！不要使用默认值）
SHARE_CODE="your_strong_password"

# 服务端口（可选，默认 10240）
PORT=10240
```

### 2. 安装依赖 & 启动服务

```bash
# 安装依赖（包含 python-dotenv）
pip install -r requirements.txt

# 启动 HTTPS 服务（.env 文件中的变量会自动加载）
python3 app.py
```

终端启动日志：
```text
============================================================
 🚀 AirShare HTTPS Service (Encrypted & Protected)
 🔑 Access Code:    8888
 🔒 Encryption:     TLS/HTTPS (SSL enabled)
 🌐 Local Access:    https://127.0.0.1:10240
 📱 LAN Access:      https://192.168.1.100:10240
============================================================
```

### 3. 浏览器首次访问说明

由于使用的是局域网自签名 SSL 证书，手机或电脑浏览器首次打开 `https://<局域网IP>:10240` 时会提示"证书不受信任"或"您的连接不是私密连接"：

- **Chrome / Edge / 微信内内置浏览器**：点击 **"高级"** -> 点击 **"继续前往/继续访问 (不安全)"** 即可进入。
- **Safari (iOS / macOS)**：点击 **"显示详细信息"** -> 点击 **"访问此网站"** -> 输入本机解锁密码/面容ID确认即可。

进站后在 Apple 风格的 Pin Modal 中输入口令（默认 `8888`），即可开始使用。

---

## ⚡ 消除 Flask 开发服务器警告

启动服务时你可能会看到这样一条警告：

```
WARNING: This is a development server. Do not use it in a
production deployment. Use a production WSGI server instead.
```

这是 Flask 开发服务器的善意提醒 —— 并非报错，但如果你希望消除它，这里有三种方案供你选择。

### 方案一：设置环境变量 `FLASK_DEBUG=1`

Flask 仅在 `debug=False` 时打印这条警告。将 `debug` 设为 `True` 即可消除。

#### 方式 A：启动时指定

```bash
FLASK_DEBUG=1 python app.py
```

#### 方式 B：在 `.env` 文件中添加

```ini
FLASK_DEBUG=1
```

#### 方式 C：在 `app.py` 中修改

将最后一行改为：

```python
app.run(host="0.0.0.0", port=port, ssl_context=ssl_ctx, debug=True)
```

| 方式 | 优点 | 缺点 |
|------|------|------|
| **A** | 零改动，仅当前有效 | 每次启动都要加 |
| **B** | 持久化，方便集中管理 | 需创建 `.env` 文件 |
| **C** | 彻底关闭 | 修改了代码 |

> ⚠️ `debug=True` 会开启 Flask 的自动重载（hot-reload）和更详细的调试信息输出。这不建议在生产环境中长期开启，因为自动重载消耗额外的系统资源。

### 方案二：使用生产级 WSGI 服务器（⭐ 推荐）

真正消除该警告的规范做法是使用生产级 WSGI 服务器（如 Waitress 或 Gunicorn）。这样你将获得**多 worker 并发、请求排队、优雅重启**等生产级能力。

#### Waitress

```bash
# 安装
pip install waitress

# 启动（保留 self-signed SSL）
waitress-serve --host=0.0.0.0 --port=10240 --url-scheme=https \
  --certfile=certs/share.local.crt --keyfile=certs/share.local.key app:app
```

也可以修改 `app.py`，让启动逻辑自动 fallback：

```python
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10240))
    ips = get_lan_ips()
    ssl_ctx = generate_self_signed_cert()

    print("=" * 60)
    print(" 🚀 AirShare HTTPS Service (Encrypted & Protected)")
    print(f" 🔑 Access Code:    {ACCESS_CODE}")
    print(f" 🔒 Encryption:     TLS/HTTPS (SSL enabled)")
    print(f" 🌐 Local Access:    https://127.0.0.1:{port}")
    for ip in ips:
        print(f" 📱 LAN Access:      https://{ip}:{port}")
    print("=" * 60)

    try:
        from waitress import serve
        print(" ⚡ Using Waitress production server")
        if ssl_ctx == "adhoc":
            serve(app, host="0.0.0.0", port=port, url_scheme="https")
        else:
            serve(app, host="0.0.0.0", port=port, url_scheme="https",
                  certfile=ssl_ctx[0], keyfile=ssl_ctx[1])
    except ImportError:
        app.run(host="0.0.0.0", port=port, ssl_context=ssl_ctx, debug=False)
```

#### Gunicorn

```bash
# 安装
pip install gunicorn

# 启动（Gunicorn 直接绑定证书）
gunicorn -w 4 -b 0.0.0.0:10240 app:app \
  --keyfile certs/share.local.key \
  --certfile certs/share.local.crt
```

> 提示：`-w 4` 表示 4 个 worker 进程，可根据 CPU 核心数调整。

> ⚠️ Waitress 的 SSL 支持依赖系统 OpenSSL，部分 Linux 发行版需安装 `libssl-dev` 或 `openssl-devel`。

### 方案三：忽略它（并不是错误）

这条警告只是一个善意的提醒，**不是报错**。Flask 自带的 Werkzeug 开发服务器功能完整、支持 SSL 自签名证书开箱即用、在局域网（最多 5-10 人）场景下性能完全够用。

```python
# 已知风险的情况下可安心使用
app.run(host="0.0.0.0", port=port, ssl_context=ssl_ctx, debug=False)
```

### 方案总结

| 方案 | 适合场景 |
|------|----------|
| **方案一** | 就想让警告消失，最小改动 |
| **方案二（推荐）** | 追求生产级健壮性，或强迫症 |
| **方案三** | 无所谓，继续用 |

> **安全提示：** 无论哪种方案，都不要将 `debug=True` 部署到公网或暴露给不可信用户。自签名证书对于内部局域网完全 OK，但如果需要公网访问，建议使用 Let's Encrypt 等受信任的 CA 签名。
