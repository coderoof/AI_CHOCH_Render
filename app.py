import os
from datetime import datetime
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, send_file
from tvDatafeed import TvDatafeed, Interval
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from sklearn.ensemble import RandomForestClassifier  # Örnek ML algoritması

# ------------------ Flask ------------------
app = Flask(__name__)

# ------------------ TradingView ------------------
tv = TvDatafeed()

# ------------------ Google Drive ------------------
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def drive_service():
    creds = None
    token_path = "/tmp/token.json"
    creds_path = "/tmp/credentials.json"
    
    # credentials.json'u Render Secret File'dan oluştur
    if not os.path.exists(creds_path):
        with open(creds_path, "w") as f:
            f.write(os.environ["GOOGLE_CREDENTIALS_CONTENT"])
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())
    
    service = build('drive', 'v3', credentials=creds)
    return service

def upload_to_drive(file_path, folder_id=None):
    service = drive_service()
    file_metadata = {'name': os.path.basename(file_path)}
    if folder_id:
        file_metadata['parents'] = [folder_id]
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"Yüklendi: {file_path} -> Google Drive ID: {file['id']}")
    return file['id']

# ------------------ Hisse Listesi ------------------
SYMBOLS = ["AKBNK","ASELS","THYAO","KCHOL"]  # Örnek hisseler

# ------------------ Tarama ve AI Model ------------------
def scan_stocks(scan_date_str):
    scan_date = datetime.strptime(scan_date_str, "%Y-%m-%d")
    results = []

    for sym in SYMBOLS:
        try:
            df = tv.get_hist(sym, "BIST", Interval.W1, n_bars=52)  # Son 1 yıl haftalık
            df = df[df.index <= scan_date]
            if df.empty:
                continue

            # AI Feature Örnek: Önceki close ve volume farkları
            df["close_diff"] = df["close"].diff()
            df["vol_diff"] = df["volume"].diff()
            df = df.dropna()

            # RandomForestClassifier örnek tahmin
            X = df[["close_diff", "vol_diff"]]
            y = np.where(df["close"].shift(-1) > df["close"], 1, 0)
            model = RandomForestClassifier(n_estimators=50)
            model.fit(X, y)
            prob_up = model.predict_proba(X.iloc[-1:])[0][1]
            prob_down = 1 - prob_up

            results.append({
                "symbol": sym,
                "date": scan_date_str,
                "close": df["close"].iloc[-1],
                "up_prob": prob_up*100,
                "down_prob": prob_down*100
            })
        except Exception as e:
            print(f"{sym} hatası: {e}")
            continue

    return pd.DataFrame(results)

# ------------------ Flask Routes ------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/scan", methods=["GET"])
def scan():
    scan_date = request.args.get("date")
    results = scan_stocks(scan_date)
    return render_template("index.html", results=results, scan_date=scan_date)

@app.route("/download_excel", methods=["GET"])
def download_excel():
    scan_date = request.args.get("date")
    df = scan_stocks(scan_date)
    file_name = f"scan_{scan_date}.xlsx"
    df.to_excel(file_name, index=False)
    upload_to_drive(file_name)  # Google Drive yükleme
    return send_file(file_name, as_attachment=True)

@app.route("/dashboard_full", methods=["GET"])
def dashboard_full():
    scan_date = request.args.get("date")
    df = scan_stocks(scan_date)
    # Dashboard örneği: basit plotly heatmap
    import plotly.express as px
    fig = px.imshow(df[["up_prob","down_prob"]].T, text_auto=True,
                    labels=dict(x="Hisse", y="Probability", color="%"))
    graph_html_heat = fig.to_html(full_html=False)
    return render_template("dashboard_full.html", scan_date=scan_date, graph_html_heat=graph_html_heat)

# ------------------ Cron Job ------------------
def weekly_dashboard_update():
    today_str = datetime.today().strftime("%Y-%m-%d")
    df = scan_stocks(today_str)
    file_name = f"weekly_scan_{today_str}.xlsx"
    df.to_excel(file_name, index=False)
    upload_to_drive(file_name)
    print("Weekly update completed.")

# ------------------ Run Flask ------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "weekly_dashboard_update":
        weekly_dashboard_update()
    else:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
