import requests
import time
from pytrends.request import TrendReq
from duckduckgo_search import DDGS

# ==================== 🛠️ 1. 用户配置区（请在此处填入你的 Key） ====================
    # --- 企业微信应用配置 ---
CONFIG = {
    "WECHAT_WORK_CORPID": os.getenv("WECHAT_WORK_CORPID"),
    "WECHAT_WORK_SECRET": os.getenv("WECHAT_WORK_SECRET"),
    "WECHAT_WORK_AGENTID": int(os.getenv("WECHAT_WORK_AGENTID", 0)),
}

# ==================== 📱 2. 企业微信推送模块 ====================

class WeChatWorkPush:
    def __init__(self, corpid, secret, agentid):
        self.corpid = corpid
        self.secret = secret
        self.agentid = agentid
        self.access_token = None
        self.token_expires_time = 0

    def get_access_token(self):
        """
        获取/刷新企业微信 API 的 Access Token
        """
        if self.access_token and time.time() < self.token_expires_time:
            return self.access_token

        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corpid}&corpsecret={self.secret}"
        try:
            res = requests.get(url, timeout=10).json()
            if res.get("errcode") == 0:
                self.access_token = res.get("access_token")
                # Token 有效期通常为 7200 秒，提早 200 秒刷新
                self.token_expires_time = time.time() + res.get("expires_in", 7200) - 200
                return self.access_token
            else:
                print(f"❌ 获取企业微信 Token 失败: {res.get('errmsg')}")
                return None
        except Exception as e:
            print(f"❌ 请求企业微信 Token 网络异常: {e}")
            return None

    def send_markdown(self, markdown_content):
        """
        发送 Markdown 格式消息到企业微信/个人微信
        """
        token = self.get_access_token()
        if not token:
            print("⚠️ 未能获取到有效的 Access Token，取消推送")
            return

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        data = {
            "touser": "@all",           # 发送给企业内部所有人（即绑定的个人微信）
            "msgtype": "markdown",
            "agentid": self.agentid,
            "markdown": {
                "content": markdown_content
            }
        }
        
        try:
            res = requests.post(url, json=data, timeout=10).json()
            if res.get("errcode") == 0:
                print("📲 【推送成功】消息已发送至你的微信！")
            else:
                print(f"❌ 发送失败: {res.get('errmsg')} (错误码: {res.get('errcode')})")
        except Exception as e:
            print(f"❌ 企业微信发送异常: {e}")

# 初始化推送对象
wechat_pusher = WeChatWorkPush(
    corpid=CONFIG["WECHAT_WORK_CORPID"],
    secret=CONFIG["WECHAT_WORK_SECRET"],
    agentid=CONFIG["WECHAT_WORK_AGENTID"]
)

# ==================== 🔍 3. 核心分析模块 ====================

def get_upcoming_steam_games():
    """
    抓取 Steam/SteamDB 未来上线且具备潜力的游戏列表
    """
    mock_upcoming_games = [
        {"name": "Mistfall Hunter", "release_days": 14, "followers": 35000},
        {"name": "Chronos Legacy", "release_days": 21, "followers": 18000},
        {"name": "Small Indie Test", "release_days": 5, "followers": 800},
        {"name": "Overhyped AAA Game", "release_days": 10, "followers": 150000}
    ]
    
    # 📝 条件过滤：只留“距离上线 7~30 天”且“关注量 1w ~ 5w”的蓝海黑马
    targets = [
        g for g in mock_upcoming_games 
        if 7 <= g["release_days"] <= 30 and 10000 <= g["followers"] <= 50000
    ]
    return targets


def check_google_trends(game_name):
    """
    【信号 1】调用 Google Trends 验证近 7 天搜索量是否急剧陡升
    """
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
    """
    【信号 2】方案2：使用 DuckDuckGo 零成本验证搜索缺口
    """
    print(f"  ├─ [2/2] 正在通过 DuckDuckGo 验证竞争缺口: {game_name} guide...")
    query = f"{game_name} guide"
    
    try:
        # 获取搜索前 10 个结果
        results = list(DDGS().text(query, max_results=10))
        
        # UGC 平台列表（非专业独立攻略站）
        ugc_domains = ["reddit.com", "youtube.com", "bilibili.com", "twitter.com", "x.com", "steamcommunity.com"]
        
        pro_sites_count = 0
        for item in results:
            link = item.get("href", "")
            if not any(ugc in link for ugc in ugc_domains):
                pro_sites_count += 1
                
        # 如果专业独立攻略站 < 2 个，说明有巨大缺口
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
    print("🤖 自动新游黑马&建站缺口监控脚本已启动")
    print("==================================================\n")
    
    games = get_upcoming_steam_games()
    print(f"🔍 初始筛选出 {len(games)} 款符合基础指标的新游戏...\n")
    
    for game in games:
        game_name = game["name"]
        print(f"👉 正在评估游戏: 《{game_name}》")
        
        # 1. 验证趋势
        if check_google_trends(game_name):
            # 2. 验证缺口
            if check_search_competition(game_name):
                # 3. 构造 Markdown 并发送企业微信推送
                markdown_msg = f"""🎯 **【新游黑马建站提醒】**
> **游戏名称**：<font color="info">{game_name}</font>
> **上线倒计时**：{game['release_days']} 天
> **Steam 关注量**：{game['followers']} 人
> **Google Trends**：近 7 天搜索急剧陡升 📈
> **竞争缺口**：首页大部分为论坛/视频，<font color="warning">无专业攻略站</font> 🕳️

💡 **建议**：符合蓝海指标，可以立刻开始建站！"""
                
                if CONFIG["WECHAT_WORK_CORPID"] != "YOUR_CORPID_HERE":
                    wechat_pusher.send_markdown(markdown_msg)
                else:
                    print("\n📢 [未填写 CorpID，控制台模拟推送消息]:")
                    print(markdown_msg + "\n")
            else:
                print(f"⏩ 跳过 《{game_name}》：竞争较大")
        else:
            print(f"⏩ 跳过 《{game_name}》：热度未达陡升条件")
            
        print("-" * 40)

if __name__ == "__main__":
    run_pipeline()