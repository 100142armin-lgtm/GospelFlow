# -*- coding: utf-8 -*-
"""
GospelFlow 本地服务与中继引擎
- 纯 Python 官方标准库（零依赖，无需安装任何 pip 包）
- 完美解决 Ollama 本地跨域和 Google Apps Script 302 重定向跨域问题
- 自动检测局域网 IP，支持团队局域网共享使用
"""

import sys
import os
import json
import socket
import urllib.request
import urllib.error
import urllib.parse
import re
import webbrowser
from http.server import SimpleHTTPRequestHandler, HTTPServer

# 确保无论是源码运行还是 PyInstaller 打包为 exe，工作目录均指向程序所在真实目录
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# 兼容 pythonw 无窗口静默运行 (防止 print 报错退出)
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

PORT = 3000
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

# GitHub 官方仓库与高速 CDN / 镜像加速更新节点
UPDATE_REPO_RAW = "https://raw.githubusercontent.com/100142armin-lgtm/GospelFlow/main"
UPDATE_REPO_CDN = "https://cdn.jsdelivr.net/gh/100142armin-lgtm/GospelFlow@main"
UPDATE_REPO_MIRROR = "https://ghproxy.net/https://raw.githubusercontent.com/100142armin-lgtm/GospelFlow/main"

def fetch_remote_file(relative_path):
    """自动通过官方和全球加速节点拉取 GitHub 上的最新文件"""
    urls = [
        f"{UPDATE_REPO_RAW}/{relative_path}",
        f"{UPDATE_REPO_CDN}/{relative_path}",
        f"{UPDATE_REPO_MIRROR}/{relative_path}"
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'GospelFlow-Updater/1.1'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return resp.read().decode('utf-8')
        except Exception:
            continue
    raise Exception(f"无法连接到 GitHub 获取更新文件: {relative_path}")

def get_local_ip():
    """获取本机局域网 IP 地址"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 不需要真正建立连接
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

class GospelFlowHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # 允许跨域和本地访问
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        # 1. 代理转发给本地 Ollama (完全杜绝浏览器 CORS 拦截)
        if self.path.startswith('/api/ollama/'):
            sub_path = self.path[len('/api/ollama/'):]
            target_url = f"{OLLAMA_BASE_URL}/{sub_path}"
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            try:
                req = urllib.request.Request(
                    target_url,
                    data=post_data,
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=120) as response:
                    res_body = response.read()
                    self.send_response(response.status)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(res_body)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                err_payload = json.dumps({'error': f'连接本地 Ollama 异常: {str(e)}'}, ensure_ascii=False).encode('utf-8')
                self.wfile.write(err_payload)
            return

        # 2. 代理转发给 Google 表格 Webhook (解决 Google Apps Script 的 302 跨域问题)
        if self.path.startswith('/api/sheets/proxy'):
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                req_json = json.loads(post_data.decode('utf-8'))
                target_url = req_json.get('targetUrl')
                payload = req_json.get('payload', {})
                method = req_json.get('method', 'GET').upper()

                if not target_url:
                    raise ValueError('未提供有效的 Google 表格 Webhook 链接')

                # 如果传入的是常规 Google 表格网页链接且是 GET 请求，自动转为 GViz JSON 查询
                if method == 'GET' and '/spreadsheets/d/' in target_url:
                    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', target_url)
                    if match:
                        s_id = match.group(1)
                        parsed = urllib.parse.urlparse(target_url)
                        q = urllib.parse.parse_qs(parsed.query)
                        sheet_param = q.get('sheet', [''])[0]
                        target_url = f"https://docs.google.com/spreadsheets/d/{s_id}/gviz/tq?tqx=out:json"
                        if sheet_param:
                            target_url += f"&sheet={urllib.parse.quote(sheet_param)}"

                if method == 'GET':
                    req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
                else:
                    data_bytes = json.dumps(payload).encode('utf-8')
                    req = urllib.request.Request(target_url, data=data_bytes, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})

                with urllib.request.urlopen(req, timeout=30) as response:
                    res_body = response.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(res_body)

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                err_payload = json.dumps({'status': 'error', 'message': f'Google 表格中继请求异常: {str(e)}'}, ensure_ascii=False).encode('utf-8')
                self.wfile.write(err_payload)
            return

        # 2.9 安全退出后台服务
        if self.path.startswith('/api/shutdown'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success', 'message': 'GospelFlow 服务正在退出...'}, ensure_ascii=False).encode('utf-8'))
            def kill_soon():
                import time
                time.sleep(0.5)
                os._exit(0)
            import threading
            threading.Thread(target=kill_soon).start()
            return

        # 3. 在线一键更新与代码热替换
        if self.path == '/api/update/apply':
            try:
                new_html = fetch_remote_file("index.html")
                if "<title>GospelFlow" not in new_html:
                    raise ValueError("下载的代码校验未通过 (未检测到 GospelFlow 标记)")

                # 自动备份旧版
                if os.path.exists("index.html"):
                    try:
                        with open("index.html.bak", "w", encoding="utf-8") as bak:
                            with open("index.html", "r", encoding="utf-8") as orig:
                                bak.write(orig.read())
                    except Exception:
                        pass

                # 写入最新 index.html
                with open("index.html", "w", encoding="utf-8") as f:
                    f.write(new_html)

                # 同步更新本地 version.json
                try:
                    new_version_str = fetch_remote_file("version.json")
                    with open("version.json", "w", encoding="utf-8") as f:
                        f.write(new_version_str)
                except Exception:
                    pass

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success', 'message': '代码已成功热更新至最新版本！'}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': f'在线更新失败: {str(e)}'}, ensure_ascii=False).encode('utf-8'))
            return

        super().do_POST()

    def do_GET(self):
        # 0.0 安全退出后台服务
        if self.path.startswith('/api/shutdown'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success', 'message': 'GospelFlow 服务正在退出...'}, ensure_ascii=False).encode('utf-8'))
            def kill_soon():
                import time
                time.sleep(0.5)
                os._exit(0)
            import threading
            threading.Thread(target=kill_soon).start()
            return

        # 0. 获取本机信息与局域网共享 IP
        if self.path == '/api/info':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            info_data = {
                'local_ip': get_local_ip(),
                'port': PORT,
                'lan_url': f"http://{get_local_ip()}:{PORT}"
            }
            self.wfile.write(json.dumps(info_data).encode('utf-8'))
            return

        # 0.1 检查 GitHub 官方远程更新
        if self.path == '/api/update/check':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()

            # 读取本地当前版本号
            local_version = "1.0.0"
            try:
                if os.path.exists("version.json"):
                    with open("version.json", "r", encoding="utf-8") as f:
                        local_version = json.load(f).get("version", "1.0.0")
            except Exception:
                pass

            try:
                remote_json_str = fetch_remote_file("version.json")
                remote_data = json.loads(remote_json_str)
                remote_version = remote_data.get("version", "1.0.0")

                has_update = (remote_version.strip() != local_version.strip())
                resp_payload = {
                    "has_update": has_update,
                    "current_version": local_version,
                    "latest_version": remote_version,
                    "release_notes": remote_data.get("release_notes", "最新版本优化"),
                    "updated_at": remote_data.get("updated_at", "")
                }
            except Exception as e:
                resp_payload = {
                    "has_update": False,
                    "current_version": local_version,
                    "error": str(e)
                }

            self.wfile.write(json.dumps(resp_payload, ensure_ascii=False).encode('utf-8'))
            return

        # 1. 检查本地 Ollama 状态探针
        if self.path == '/api/ollama/ping':
            try:
                req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = resp.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(data)
            except Exception as e:
                self.send_response(503)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'offline', 'error': str(e)}).encode('utf-8'))
            return

        # 2. 代理中继 Google 表格 GViz 查询
        if self.path.startswith('/api/sheets/gviz'):
            parsed_path = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_path.query)
            sheet_id = query_params.get('sheetId', [''])[0]
            sheet_name = query_params.get('sheet', [''])[0]
            gid = query_params.get('gid', [''])[0]

            if not sheet_id:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'error': '缺少 sheetId 参数'}).encode('utf-8'))
                return

            gviz_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:json"
            if sheet_name:
                gviz_url += f"&sheet={urllib.parse.quote(sheet_name)}"
            if gid:
                gviz_url += f"&gid={urllib.parse.quote(gid)}"

            try:
                req = urllib.request.Request(gviz_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(data)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
            return

        super().do_GET()

def run():
    os.chdir(BASE_DIR)
    server_address = ('0.0.0.0', PORT)

    local_ip = get_local_ip()
    local_url = f"http://localhost:{PORT}"

    # 尝试绑定端口；若端口已被占用（说明已有后台实例），直接打开浏览器即可，不报错退出
    try:
        httpd = HTTPServer(server_address, GospelFlowHandler)
    except OSError:
        try:
            webbrowser.open(local_url)
        except Exception:
            pass
        sys.exit(0)

    try:
        webbrowser.open(local_url)
    except Exception:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        import traceback
        err_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server_error.log')
        with open(err_path, 'w', encoding='utf-8') as f:
            traceback.print_exc(file=f)

