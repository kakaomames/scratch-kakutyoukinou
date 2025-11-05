import json
import requests
import urllib.parse
from flask import Flask, jsonify, request, render_template_string, send_file
import io # ダウンロードのためにバイトデータを扱う

# ----------------------------------------------------------------------
# 1. セットアップと定数の定義
# ----------------------------------------------------------------------

app = Flask(__name__)

# 外部APIのベースURL
TURBOWARP_API_BASE = "https://trampoline.turbowarp.org/api/projects/"
# プロジェクト本体を取得するためのCURLコマンドのベースURL (ユーザー指定)
BASE_URL = "https://xeroxapp032.vercel.app/run?cmd=curl%20"
print(f"BASE_URL:{BASE_URL}")

# ----------------------------------------------------------------------
# 2. HTMLテンプレートの定義 (index.html, license.html)
# ----------------------------------------------------------------------

# index.html
INDEX_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>Scratchプロジェクトデータ取得</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        input[type="text"] { width: 80%; padding: 10px; margin-right: 10px; }
        button { padding: 10px 20px; cursor: pointer; }
        pre { background-color: #f4f4f4; padding: 15px; border-radius: 5px; white-space: pre-wrap; word-break: break-all; }
        .result-section { margin-top: 20px; border-top: 2px solid #ccc; padding-top: 15px; }
        .download-link, .license-link { margin-top: 15px; display: block; }
    </style>
</head>
<body>
    <h1>Scratchプロジェクトデータ解析</h1>
    <p>プロジェクトのURLを入力してください（トークン付きも可）。</p>
    
    <input type="text" id="projectUrl" placeholder="例: https://projects.scratch.mit.edu/123456789?token=..." value="https://projects.scratch.mit.edu/846673644">
    <button onclick="getData()">データ取得</button>
    
    <a href="/license" target="_blank" class="license-link">ライセンス（免責事項）を確認する</a>

    <div id="result" class="result-section" style="display:none;">
        <h2>📝 解析結果</h2>
        <pre id="jsonOutput"></pre>
        
        <p>
            ⚠️ **ダウンロードステップ:** トークンが切れる前に、以下のボタンをクリックしてプロジェクトデータを取得してください。
        </p>
        <button id="downloadButton" onclick="downloadFile()" style="padding: 15px; background-color: #4CAF50; color: white; border: none; border-radius: 5px;">
            💾 プロジェクトファイル (.sb3) をダウンロード
        </button>
    </div>

    <script>
        // ボタンクリックでAPIを呼び出す関数
        function getData() {
            const fullUrl = document.getElementById('projectUrl').value;
            // URLからプロジェクトIDを抽出 (正規表現でID部分のみを取得)
            const match = fullUrl.match(/projects\.scratch\.mit\.edu\/(\d+)/);
            if (!match) {
                alert("有効なScratchプロジェクトURLを入力してください。");
                return;
            }
            const projectId = match[1];
            
            // Flask APIへGETリクエスト
            fetch(`/projects/${projectId}`)
                .then(response => response.json())
                .then(data => {
                    // 取得したJSONデータを整形して表示
                    document.getElementById('jsonOutput').textContent = 
                        JSON.stringify(data, null, 2);
                    document.getElementById('result').style.display = 'block';
                    
                    // ダウンロードボタンに data_url を保持させる
                    const downloadButton = document.getElementById('downloadButton');
                    downloadButton.setAttribute('data-url', data.data_url);
                    
                    alert('データ取得完了！トークンを確認し、ダウンロードに進んでください。');
                })
                .catch(error => {
                    console.error('API Error:', error);
                    document.getElementById('jsonOutput').textContent = 
                        'データの取得に失敗しました。プロジェクトIDを確認してください。';
                    document.getElementById('result').style.display = 'block';
                });
        }
        
        // ダウンロード処理関数
        function downloadFile() {
            const downloadButton = document.getElementById('downloadButton');
            const dataUrl = downloadButton.getAttribute('data-url');
            
            if (!dataUrl || dataUrl.includes("トークンが見つからなかった")) {
                alert("トークンがないため、ダウンロードできません。トークン付きのURLで再試行してください。");
                return;
            }
            
            // data_urlをクエリパラメータとして /dl に渡し、ダウンロードを開始させる
            window.location.href = `/dl?data_url=${encodeURIComponent(dataUrl)}`;
        }
    </script>
</body>
</html>
"""

# license.html
LICENSE_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>ライセンスと免責事項</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #CC0000; }
        p { line-height: 1.6; }
    </style>
</head>
<body>
    <h1>⚠️ ライセンスと免責事項 ⚠️</h1>
    <p>
        **このサイトを使って得たデータ（Scratchプロジェクトファイルなど）において、我々は一切の責任を負いません。**
    </p>
    <p>
        プロジェクトファイルの利用は、元のプロジェクト作者の意図およびScratchの利用規約（著作権、コミュニティガイドライン）に従ってください。
    </p>
    <p>
        本サービスは、あくまで解析とデータ取得の補助を目的としています。ファイルの内容、著作権、および利用によって生じるいかなる問題についても、利用者の責任となります。
    </p>
    <a href="/">ホームに戻る</a>
</body>
</html>
"""


# ----------------------------------------------------------------------
# 3. ルートの定義
# ----------------------------------------------------------------------

# 3-1. ホームページ / (index.html)
@app.route('/')
def index():
    """ホームページを表示し、プロジェクトURL入力を受け付ける。"""
    return render_template_string(INDEX_HTML)
print(f"Flask Route: / (index) を定義しました。")


# 3-2. ライセンス /license (license.html)
@app.route('/license')
def license_page():
    """免責事項ページを表示する。"""
    return render_template_string(LICENSE_HTML)
print(f"Flask Route: /license を定義しました。")


# 3-3. プロジェクト情報取得 API /projects/<id> (前回と同一ロジック)
@app.route('/projects/<int:project_id>', methods=['GET', 'POST'])
def get_project_data(project_id):
    """TurboWarp APIからプロジェクト情報を取得し、整形して返す。"""
    
    # ... [前回の get_project_data のロジックとほぼ同じ] ...
    
    api_url = f"{TURBOWARP_API_BASE}{project_id}"
    print(f"APIリクエストURL:{api_url}")

    # Curlコマンドのログ出力 (ご要望のログとしてprint)
    curl_command = f"curl -v -L {api_url}"
    print(f"Curl実行シミュレーション: {curl_command}")

    try:
        response = requests.get(api_url)
        response.raise_for_status() 
        raw_data = response.json()
        print(f"raw_dataを正常に取得しました。ID:{raw_data.get('id')}")

    except requests.exceptions.RequestException as e:
        error_message = f"APIからのデータ取得中にエラーが発生しました: {e}"
        print(f"エラー:{error_message}")
        return jsonify({"error": error_message}), 500

    project_token = raw_data.get("project_token", "N/A")
    print(f"project_token:{project_token}")
    
    # データの整形とdata_urlの生成 (省略せずすべて含めます)
    sorted_data = {
        "id": raw_data.get("id"),
        "title": raw_data.get("title"),
        "project_token": project_token,
        "description": raw_data.get("description"),
        "instructions": raw_data.get("instructions"),
        "visibility": raw_data.get("visibility"),
        "public": raw_data.get("public"),
        "comments_allowed": raw_data.get("comments_allowed"),
        "is_published": raw_data.get("is_published"),
        
        "author_id": raw_data.get("author", {}).get("id"),
        "author_username": raw_data.get("author", {}).get("username"),
        "author_scratchteam": raw_data.get("author", {}).get("scratchteam"),
        "author_joined": raw_data.get("author", {}).get("history", {}).get("joined"),
        "author_profile_images": raw_data.get("author", {}).get("profile", {}).get("images", {}),
        
        "image": raw_data.get("image"),
        "images": raw_data.get("images", {}),
        "history": raw_data.get("history", {}),
        "stats": raw_data.get("stats", {}),
        "remix": raw_data.get("remix", {}),
        "tags": raw_data.get("tags", []),
    }
    
    if project_token and project_token != "N/A":
        project_data_url = f"https://projects.scratch.mit.edu/{project_id}?token={project_token}"
        encoded_project_data_url = urllib.parse.quote_plus(project_data_url)
        DATA_URL = f"{BASE_URL}{encoded_project_data_url}"
        print(f"DATA_URL:{DATA_URL}")
        sorted_data["data_url"] = DATA_URL
    else:
        sorted_data["data_url"] = "トークンが見つからなかったため、プロジェクトデータ本体のURLは生成できませんでした。"
        print(f"data_url:トークンなしで生成できませんでした。")

    return jsonify(sorted_data)
print(f"Flask Route: /projects/<int:project_id> (API) を定義しました。")


# 3-4. ダウンロード処理 /dl
@app.route('/dl')
def download_project():
    """data_url (Curlコマンド) を実行し、結果をダウンロードファイルとして返す。"""
    
    # クエリパラメータから data_url を取得
    data_url = request.args.get('data_url')
    print(f"data_url (Curl実行リンク):{data_url}")
    
    if not data_url:
        return "エラー: ダウンロードURLが指定されていません。", 400
    
    # Curlコマンドを実行するリンクへアクセス (つまり、プロジェクトファイルを取得)
    curl_command_url = data_url
    print(f"Curl実行: curl -v -L {curl_command_url}") # ログ出力

    try:
        # data_url (外部Curl実行サービス) へリクエストを送信
        # これにより、外部サービスが Scratch プロジェクトファイルを取得し、その内容を返します。
        dl_response = requests.get(curl_command_url, stream=True)
        dl_response.raise_for_status()
        
        # 取得したデータをバイトストリームとして扱う
        file_data = io.BytesIO(dl_response.content)
        
        # プロジェクトIDと拡張子を付けてファイル名を決定
        # プロジェクトIDは data_url からも抽出可能
        import re
        match = re.search(r'projects\.scratch\.mit\.edu/(\d+)', data_url)
        project_id = match.group(1) if match else "unknown"
        filename = f"{project_id}.sb3"
        print(f"ダウンロードファイル名:{filename}")
        
        # ファイルとしてユーザーに送り返す (ダウンロードを強制)
        # Content-Dispositionでダウンロードを指示
        return send_file(
            file_data,
            mimetype="application/x.scratch.sb3",
            as_attachment=True,
            download_name=filename
        )

    except requests.exceptions.RequestException as e:
        error_message = f"プロジェクトファイル取得中にエラーが発生しました: {e}"
        print(f"エラー:{error_message}")
        return f"プロジェクトファイルのダウンロードに失敗しました。トークンの有効期限を確認してください。エラー: {e}", 500

print(f"Flask Route: /dl (ダウンロード) を定義しました。")
print("\n" + "="*40)
print("✨ Flaskアプリの構築完了 ✨")
print("="*40)


if __name__ == '__main__':
    # デバッグモードで実行
    app.run(debug=True)
