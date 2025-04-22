from flask import Flask
import get_important_forex_news
import os

app = Flask(__name__)

@app.route('/')
def index():
    return '🟢 Forex News Bot is alive!'

@app.route('/run')
def run_script():
    try:
        get_important_forex_news.main()
        return '✅ Script executed successfully!'
    except Exception as e:
        return f'❌ Error occurred: {str(e)}'

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
