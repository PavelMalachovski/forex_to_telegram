import sqlite3

conn = sqlite3.connect('news.db')
cursor = conn.cursor()

# Выводим все записи
cursor.execute("SELECT * FROM news")
rows = cursor.fetchall()

for row in rows:
    print("Date:", row[0])
    print("Time:", row[1])
    print("Currency:", row[2])
    print("Event:", row[3])
    print("Forecast:", row[4])
    print("Previous:", row[5])
    print("Actual:", row[6])
    print("Impact:", row[7])
    print("Analysis:", row[8])
    print("-" * 40)

conn.close()
