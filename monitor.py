import os
import requests
import time
from pytrends.request import TrendReq
from duckduckgo_search import DDGS

# ==================== 🛠️ 1. 读取 GitHub Secrets 配置 ====================
CONFIG = {
    # 只需要配置群机器人的 Webhook 链接
    "ROBOT_WEBHOOK": os.getenv("WECHAT_ROBOT_WEBHOOK"),
}

# ==================== 📱 2. 企业微信群机器人推送模块 ====================

def send_to_wechat_robot(markdown_content):
    """
    通过企业微信群机器人发送 Markdown 消息（零 IP 白名单限制）
    """
    webhook_url = CONFIG["ROBOT_WEBHOOK"]
    if not webhook_url:
        print("⚠️ 未配置 WECHAT_ROBOT_WEBHOOK，跳过微信推送")
        return

    data = {
        "msgtype": "markdown",
        "markdown": {
            "content": markdown_content
        }
    }
    
    try:
        res = requests.post(webhook_url, json=data, timeout=10).json()
        if res.get("errcode") == 0:
            print("📲 【推送成功】消息已通过群机器人发送至企业微信！")
        else:
            print(f"❌ 群机器人发送失败: {res.get('errmsg')} (错误码: {res.get('errcode')})")
    except Exception as e:
        print(f"❌ 机器人发送请求网络异常: {e}")

# ==================== 🔍 3. 核心分析模块 ====================

def get_upcoming_steam_games():
    """ 抓取 Steam/SteamDB 未来上线且具备潜力的游戏列表 """
    mock_upcoming_games = [
        {"name": "Mistfall Hunter", "release_days": 14, "followers": 35000},
        {"name": "Chronos Legacy", "release_days": 21, "followers": 18000},
        {"name": "Small Indie Test", "release_days": 5, "followers": 800},
        {"name": "Overhyped AAA Game", "release_days": 10, "followers": 150000}
    ]
    
    targets = [
        g for g in mock_upcoming_games 
        if 7 <= g["release_days"] <= 30 and 10000 <= g["followers"] <= 50000
    ]
    return targets


def check_google_trends(game_name):
    """ 【信号 1】调用 Google Trends 验证近 7 天搜索量是否急剧陡升 """
    print(f"  ├─ [1/2] 正在检测 Google Trends 趋势: {game_name}...")
    try:
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
        pytrends.build_payload([game_name], timeframe='now 7-d', geo='')
        data = pytrends.interest_over_time()
        
        if data.empty or len(data[game_name]) < 4:
            print("  │  └─ ❌ 搜索数据不足")
            return False
            
        early_avg = data[game_name].iloc[:3].mean()
        recent_avg = data[game_name].iloc[-3:].mean()
        
        if early_avg > 0 and (recent_avg / early_avg) >= 2.0:
            print("  │  └─ ✅ 趋势符合：近 7 天热度急剧陡升！")
            return True
        elif early_avg == 0 and recent_avg > 10:
            print("  │  └─ ✅ 趋势符合：近期搜索突破爆发！")
            return True
        else:
            print("  │  └─ ❌ 趋势平缓，未达陡升标准")
            return False
    except Exception as e:
        print(f"  │  └─ ⚠️ Trends API 请求受限或异常 ({e})，跳过")
        return False


def check_search_competition(game_name):
    """ 【信号 2】使用 DuckDuckGo 零成本验证搜索缺口 """
    print(f"  ├─ [2/2] 正在通过 DuckDuckGo 验证竞争缺口: {game_name} guide...")
    query = f"{game_name} guide"
    
    try:
        results = list(DDGS().text(query, max_results=10))
        ugc_domains = ["reddit.com", "youtube.com", "bilibili.com", "twitter.com", "x.com", "steamcommunity.com"]
        
        pro_sites_count = 0
        for item in results:
            link = item.get("href", "")
            if not any(ugc in link for ugc in ugc_domains):
                pro_sites_count += 1
                
        if pro_sites_count < 2:
            print(f"  │  └─ ✅ 竞争符合：首页独立攻略站仅 {pro_sites_count} 个，存在蓝海缺口！")
            return True
        else:
            print(f"  │  └─ ❌ 竞争激烈：已有 {pro_sites_count} 个专业攻略站占位")
            return False
    except Exception as e:
        print(f"  │  └─ ⚠️ DuckDuckGo 搜索超时或失败: {e}")
        return False

# ==================== 🚀 4. 主运行逻辑 ====================

def run_pipeline():
    print("==================================================")
    print("🤖 自动新游黑马&建站缺口监控脚本（机器人版）已启动")
    print("==================================================\n")
    
    # 1. 发送一条测试/启动消息验证连通性
    test_msg = "🤖 **【监控系统已启动】**\nGitHub Actions 正在执行今天的新游蓝海缺口评估..."
    send_to_wechat_robot(test_msg)
    
    games = get_upcoming_steam_games()
    print(f"🔍 初始筛选出 {len(games)} 款符合基础指标的新游戏...\n")
    
    for game in games:
        game_name = game["name"]
        print(f"👉 正在评估游戏: 《{game_name}》")
        
        if check_google_trends(game_name):
            if check_search_competition(game_name):
                markdown_msg = f"""🎯 **【新游黑马建站提醒】**
> **游戏名称**：<font color="info">{game_name}</font>
> **上线倒计时**：{game['release_days']} 天
> **Steam 关注量**：{game['followers']} 人
> **Google Trends**：近 7 天搜索急剧陡升 📈
> **竞争缺口**：首页大部分为论坛/视频，<font color="warning">无专业攻略站</font> 🕳️

💡 **建议**：符合蓝海指标，可以立刻开始建站！"""
                send_to_wechat_robot(markdown_msg)
            else:
                print(f"⏩ 跳过 《{game_name}》：竞争较大")
        else:
            print(f"⏩ 跳过 《{game_name}》：热度未达陡升条件")
            
        print("-" * 40)

if __name__ == "__main__":
    run_pipeline()
