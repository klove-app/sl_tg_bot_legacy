import os
from config.config import DATABASE_NAME

print(f"\nCurrent working directory: {os.getcwd()}")
print(f"Database path from config: {DATABASE_NAME}")
print(f"Database file exists: {os.path.exists(DATABASE_NAME)}")

if os.path.exists(DATABASE_NAME):
    print(f"Database file size: {os.path.getsize(DATABASE_NAME)} bytes")
    
# Проверяем наличие других .db файлов
db_files = [f for f in os.listdir('.') if f.endswith('.db')]
print("\nAll .db files in current directory:")
for db_file in db_files:
    print(f"- {db_file} ({os.path.getsize(db_file)} bytes)") 