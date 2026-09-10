import os
import time
import socket
import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

app = Flask(__name__)

# ===== 1. 访问口令配置 (可自行修改或通过环境变量 SHARE_CODE 传入) =====
ACCESS_CODE = os.environ.get("SHARE_CODE", "888888")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATA_FOLDER = os.path.join(BASE_DIR, "data")
CERT_DIR = os.path.join(BASE_DIR, "certs")
CERT_FILE = os.path.join(CERT_DIR, "share.local.crt")
KEY_FILE = os.path.join(CERT_DIR, "share.local.key")
TEXT_FILE = os.path.join(DATA_FOLDER, "shared_text.txt")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(CERT_DIR, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB limit per request


# ===== 2. 鉴权装饰器 =====
def check_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # 允许获取公开视图与验证接口
        if request.endpoint in ("index", "verify_code"):
            return f(*args, **kwargs)

        token = request.headers.get("X-Access-Code") or request.args.get("code")
        if token != ACCESS_CODE:
            return jsonify({"error": "Unauthorized", "message": "口令验证失败"}), 401
        return f(*args, **kwargs)

    return decorated


# ===== 3. 自签名 TLS 证书自动生成函数 =====
def generate_self_signed_cert():
    """使用 cryptography 自动生成可持久化保存的 TLS 证书与私钥"""
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return (CERT_FILE, KEY_FILE)

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        # 生成私钥
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # 证书主题
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AirShare Local"),
                x509.NameAttribute(NameOID.COMMON_NAME, "AirShare LAN Server"),
            ]
        )

        # 证书有效期 10 年
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(
                datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(days=3650)
            )
            .sign(key, hashes.SHA256())
        )

        # 保存私钥
        with open(KEY_FILE, "wb") as f:
            f.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        # 保存证书
        with open(CERT_FILE, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"🔒 已在 {CERT_DIR} 自动生成持久化 HTTPS (TLS) 证书")
        return (CERT_FILE, KEY_FILE)
    except Exception as e:
        print(f"⚠️ 无法生成自定义证书: {e}，回退为 Flask 临时 adhoc 模式")
        return "adhoc"


def get_lan_ips():
    lan_ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        if ip and not ip.startswith("127."):
            lan_ips.append(ip)
        s.close()
    except Exception:
        pass

    if not lan_ips:
        lan_ips.append("127.0.0.1")
    return lan_ips


def get_text_data():
    if not os.path.exists(TEXT_FILE):
        return {"content": "", "updated_at": None}
    try:
        with open(TEXT_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        mtime = os.path.getmtime(TEXT_FILE)
        updated_at = datetime.datetime.fromtimestamp(mtime).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return {"content": content, "updated_at": updated_at}
    except Exception:
        return {"content": "", "updated_at": None}


def save_text_data(content):
    with open(TEXT_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    mtime = os.path.getmtime(TEXT_FILE)
    return datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/verify", methods=["POST"])
def verify_code():
    data = request.get_json() or {}
    code = data.get("code", "")
    if code == ACCESS_CODE:
        return jsonify({"status": "success", "token": ACCESS_CODE})
    return jsonify({"status": "error", "message": "口令错误"}), 401


@app.route("/api/info", methods=["GET"])
@check_auth
def get_info():
    port = int(os.environ.get("PORT", 10240))
    ips = get_lan_ips()
    return jsonify(
        {"port": port, "ips": ips, "urls": [f"https://{ip}:{port}" for ip in ips]}
    )


@app.route("/api/text", methods=["GET", "POST", "DELETE"])
@check_auth
def handle_text():
    if request.method == "GET":
        return jsonify(get_text_data())
    elif request.method == "POST":
        data = request.get_json() or {}
        content = data.get("content", "")
        updated_at = save_text_data(content)
        return jsonify(
            {"status": "success", "content": content, "updated_at": updated_at}
        )
    elif request.method == "DELETE":
        save_text_data("")
        return jsonify({"status": "success", "content": "", "updated_at": None})


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}


def format_file_size(bytes_size):
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"


@app.route("/api/files", methods=["GET", "DELETE"])
@check_auth
def handle_files():
    if request.method == "DELETE":
        deleted_count = 0
        try:
            for name in os.listdir(app.config["UPLOAD_FOLDER"]):
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted_count += 1
            return jsonify(
                {
                    "status": "success",
                    "message": f"已清空所有文件 ({deleted_count} 个)",
                    "deleted_count": deleted_count,
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # GET request - list files with optional pagination
    files_info = []
    try:
        filenames = os.listdir(app.config["UPLOAD_FOLDER"])
        regular_files = [
            name
            for name in filenames
            if os.path.isfile(os.path.join(app.config["UPLOAD_FOLDER"], name))
        ]
        regular_files.sort(
            key=lambda x: os.path.getmtime(
                os.path.join(app.config["UPLOAD_FOLDER"], x)
            ),
            reverse=True,
        )

        total = len(regular_files)
        page = request.args.get("page", type=int)
        limit = request.args.get("limit", default=12, type=int)

        if page is not None:
            if page < 1:
                page = 1
            if limit < 1:
                limit = 12
            total_pages = (total + limit - 1) // limit if total > 0 else 1
            start = (page - 1) * limit
            end = start + limit
            target_files = regular_files[start:end]
        else:
            total_pages = 1
            target_files = regular_files

        for name in target_files:
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], name)
            stat = os.stat(file_path)
            ext = os.path.splitext(name)[1].lower()
            files_info.append(
                {
                    "name": name,
                    "size_bytes": stat.st_size,
                    "size_formatted": format_file_size(stat.st_size),
                    "mod_time": datetime.datetime.fromtimestamp(
                        stat.st_mtime
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "is_image": ext in IMAGE_EXTENSIONS,
                    "url": f"/uploads/{name}?code={ACCESS_CODE}",
                }
            )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    response_data = {
        "files": files_info,
        "total": total,
    }
    if page is not None:
        response_data["page"] = page
        response_data["limit"] = limit
        response_data["total_pages"] = total_pages

    return jsonify(response_data)



@app.route("/api/upload", methods=["POST"])
@check_auth
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    uploaded_files = request.files.getlist("file")
    saved_files = []

    for file in uploaded_files:
        if file.filename == "":
            continue
        filename = secure_filename(file.filename)
        if not filename:
            ext = ".png"
            if file.mimetype == "image/jpeg":
                ext = ".jpg"
            elif file.mimetype == "image/gif":
                ext = ".gif"
            elif file.mimetype == "image/webp":
                ext = ".webp"
            filename = f"paste_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

        target_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(target_path):
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{int(time.time())}{ext}"
            target_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        file.save(target_path)
        stat = os.stat(target_path)
        ext = os.path.splitext(filename)[1].lower()

        saved_files.append(
            {
                "name": filename,
                "size_bytes": stat.st_size,
                "size_formatted": format_file_size(stat.st_size),
                "mod_time": datetime.datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "is_image": ext in IMAGE_EXTENSIONS,
                "url": f"/uploads/{filename}?code={ACCESS_CODE}",
            }
        )

    return jsonify({"status": "success", "files": saved_files})


@app.route("/uploads/<path:filename>")
@check_auth
def download_file(filename):
    as_attachment = request.args.get("download", "0") == "1"
    return send_from_directory(
        app.config["UPLOAD_FOLDER"], filename, as_attachment=as_attachment
    )


@app.route("/api/files/<path:filename>", methods=["DELETE"])
@check_auth
def delete_file(filename):
    secure_name = secure_filename(filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_name)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            os.remove(file_path)
            return jsonify({"status": "success", "message": f"Deleted {filename}"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "File not found"}), 404


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

    app.run(host="0.0.0.0", port=port, ssl_context=ssl_ctx, debug=False)
