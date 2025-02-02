from database.models.user import User
from database.base import SessionLocal

def update_users():
    db = SessionLocal()
    try:
        # Получаем всех пользователей
        users = db.query(User).all()
        print(f"Found {len(users)} users")
        
        for user in users:
            print(f"\nUpdating user {user.username} ({user.user_id})")
            print(f"Before update: chat_type={user.chat_type}, yearly_goal={user.yearly_goal}, yearly_progress={user.yearly_progress}")
            
            # Обновляем значения
            if user.yearly_goal is None:
                user.yearly_goal = user.goal_km
            if user.yearly_progress is None:
                user.yearly_progress = 0.0
            if user.chat_type == 'private':
                user.chat_type = 'group'
                
            print(f"After update: chat_type={user.chat_type}, yearly_goal={user.yearly_goal}, yearly_progress={user.yearly_progress}")
        
        # Сохраняем изменения
        db.commit()
        print("\nAll users updated successfully")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_users() 