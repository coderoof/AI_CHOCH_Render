import os
from flask import Flask, request, render_template, jsonify
import pandas as pd
from datetime import datetime
from tvDatafeed import TvDatafeed, Interval

# Flask uygulaması
app = Flask(__name__)

# TradingView bağlantısı
tv = TvDatafeed()

# Tarama yapılacak hisseler
symbols = ["AKBNK", "THYAO", "SASA", "HEKTS", "ASELS", "BIMAS"]

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/scan', methods=["POST"])
def scan():
    try:
        scan_date_str = request.form.get("scan_date")
        if not scan_date_str:
            return jsonify({"error": "Tarih girilmedi!"}), 400

        scan_date = datetime.strptime(scan_date_str, "%Y-%m-%d")

        results = []
        for symbol in symbols:
            try:
                df = tv.get_hist(
                    symbol=symbol,
                    exchange='BIST',
                    interval=Interval.in_1_week,  # ✅ haftalık veri
                    n_bars=1000
                )

                if df is None or df.empty:
                    continue

                df = df[df.index <= scan_date]
                if df.empty:
                    continue

                last = df.iloc[-1]
                results.append({
                    "symbol": symbol,
                    "date": last.name.strftime("%Y-%m-%d"),
                    "open": round(last["open"], 2),
                    "close": round(last["close"], 2),
                    "high": round(last["high"], 2),
                    "low": round(last["low"], 2)
                })

            except Exception as e:
                print(f"{symbol} hatası: {e}")
                continue

        results_df = pd.DataFrame(results)
        return render_template("index.html",
                               results=results_df.to_dict(orient="records"),
                               scan_date=scan_date_str)
    except Exception as e:
        print("Tarama hatası:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
