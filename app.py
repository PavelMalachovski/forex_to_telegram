from flask import Flask
import get_important_forex_news

app = Flask(__name__)

@app.route('/')
def index():
    return '🟢 Forex News Bot is alive!'

@app.route('/run')
def run_script():
    try:
        get_forex_news_test.main()
        return '✅ Script executed successfully!'
    except Exception as e:
        return f'❌ Error occurred: {str(e)}'

if __name__ == '__main__':
    app.run(debug=True)
