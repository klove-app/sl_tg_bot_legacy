from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from datetime import datetime
import uvicorn

from database.models.running_log import RunningLog
from database.models.challenge import Challenge
from database.models.user import User
from config.config import ADMIN_IDS

app = FastAPI()

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="webapp/static"), name="static")

# Настраиваем шаблоны
templates = Jinja2Templates(directory="webapp/templates")

# Главная страница
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# API endpoints
@app.get("/api/stats/summary")
async def get_summary_stats():
    year = datetime.now().year
    stats = RunningLog.get_total_stats(year)
    return {
        "runs_count": stats["runs_count"],
        "total_km": float(stats["total_km"]),
        "users_count": stats["users_count"],
        "avg_km": float(stats["avg_km"])
    }

@app.get("/api/stats/monthly")
async def get_monthly_stats():
    year = datetime.now().year
    month = datetime.now().month
    result = []
    
    for m in range(1, month + 1):
        stats = RunningLog.get_total_stats(year, m)
        result.append({
            "month": m,
            "total_km": float(stats["total_km"]),
            "runs_count": stats["runs_count"]
        })
    
    return result

@app.get("/api/stats/runners")
async def get_top_runners():
    year = datetime.now().year
    runners = RunningLog.get_top_runners(year=year, limit=10)
    result = []
    
    for runner in runners:
        user = User.get_by_id(runner["user_id"])
        result.append({
            "username": user.username if user else "Unknown",
            "total_km": float(runner["total_km"]),
            "runs_count": runner["runs_count"]
        })
    
    return result

@app.get("/api/stats/challenges")
async def get_challenges():
    challenges = Challenge.get_active_challenges()
    result = []
    
    for challenge in challenges:
        total_km = float(challenge.get_total_progress() or 0)
        goal_km = float(challenge.goal_km or 0)
        result.append({
            "title": challenge.title,
            "goal_km": goal_km,
            "total_km": total_km
        })
    
    return result

@app.get("/api/stats/chats")
async def get_chat_stats():
    year = datetime.now().year
    stats = RunningLog.get_chat_stats_all(year)
    result = []
    
    for chat in stats:
        result.append({
            "chat_id": str(chat["chat_id"])[-6:],
            "total_km": float(chat["total_km"]),
            "runs_count": chat["runs_count"]
        })
    
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000) 