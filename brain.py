import os
import time
import random
import json
from openai import OpenAI

# ==========================================
# 🎯 核心配置区：请在这里填写你的 DeepSeek 信息
# ==========================================
# 从环境变量读取 API Key，避免把敏感信息硬编码进仓库。
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# 如果没有提供 API Key，友好提示并退出。
if not DEEPSEEK_API_KEY:
    raise SystemExit("请设置环境变量 DEEPSEEK_API_KEY 后再运行（示例：export DEEPSEEK_API_KEY=sk_xxx）")

# 初始化 DeepSeek 客户端（注意不要在日志中打印 API Key）
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# 5个小人的 MBTI 初始状态
players_status = {
    "A": {"mbti": "ESTP (企业家)", "hp": 100, "weapon": "拳头", "status": "健康"},
    "B": {"mbti": "INFP (调停者)", "hp": 100, "weapon": "拳头", "status": "健康"},
    "C": {"mbti": "INTJ (建筑师)", "hp": 100, "weapon": "拳头", "status": "健康"},
    "D": {"mbti": "ENFP (竞选者)", "hp": 100, "weapon": "拳头", "status": "健康"},
    "E": {"mbti": "ISTJ (物流师)", "hp": 100, "weapon": "拳头", "status": "健康"}
}

# 🤖 模拟弹幕生成器 (代替 YouTube 直播)
def generate_mock_danmu():
    names = ["A", "B", "C", "D", "E"]
    events = [
        "天上掉下了辐射陨石！",
        "空投箱掉落在地图中央！",
        "地震发生了，地面裂开！",
        "废土上刮起了狂风！"
    ]
    
    # 随机组合一些观众弹幕
    mock_chats = [
        f"观众_{random.randint(100,999)}: 让 {random.choice(names)} 去打 {random.choice(names)}！",
        f"乐子人: {random.choice(names)} 赶紧去搜刮物资啊，别发呆了！",
        f"战术大师: {random.choice(names)} 赶紧举盾躲避，感觉要出事！",
        f"上帝视角: {random.choice(events)}"
    ]
    return mock_chats

# 🧠 向 DeepSeek 索要剧情剧本
def ask_deepseek_for_story(danmu_list):
    print("\n[🧠 大脑] 正在把弹幕打包发给 DeepSeek 进行推演...")
    
    # 构建丢给 AI 的设定（System Prompt）
    system_prompt = """
    你是一个高自由度末日废土大逃杀游戏的虚拟导演（AI Game Master）。
    场上有5个像素小人，分别对应不同的 MBTI 性格，他们会受到观众弹幕的影响。
    
    你的任务：
    1. 结合当前的【场上状态】和最新的【观众弹幕】，推演接下来的1个回合（约5秒内）发生的剧情。
    2. 你必须严格符合角色的 MBTI 性格（例如：ESTP冲动好斗，INFP悲观温柔，INTJ冷酷理智）。
    3. 观众的弹幕拥有最高指挥权！如果观众说发生灾难（如陨石、外星人），世界就会真的发生灾难，并影响小人。
    4. 你需要决定这5秒内，谁打了谁、谁搜刮到了什么（如平底锅、霰弹枪）、谁掉了多少血（HP）。
    
    请【必须】严格以以下 JSON 格式输出，不要带有任何多余的解释或 Markdown 格式（严禁包含 ```json 等字样）：
    {
      "world_event": "全局大事件描述（如果没有则写'平静'）",
      "characters": {
        "A": {"dialogue": "小人要说的话（符合MBTI）", "hp_change": -10, "action": "具体动作(attack/scavenge/hide/run)", "new_weapon": "新武器名字(若无则不变)"},
        "B": {"dialogue": "...", "hp_change": 0, "action": "...", "new_weapon": "..."},
        "C": {"dialogue": "...", "hp_change": 0, "action": "...", "new_weapon": "..."},
        "D": {"dialogue": "...", "hp_change": 0, "action": "...", "new_weapon": "..."},
        "E": {"dialogue": "...", "hp_change": 0, "action": "...", "new_weapon": "..."}
      }
    }
    """
    
    user_content = f"【当前场上状态】:\n{json.dumps(players_status, ensure_ascii=False)}\n\n【最新收集到的观众弹幕】:\n" + "\n".join(danmu_list)
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat", # 或者是 deepseek-reasoner
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7,
            stream=False
        )
        
        # 得到 AI 返回的纯文本 JSON
        result_text = response.choices[0].message.content.strip()
        return json.loads(result_text)
    except Exception as e:
        print(f"❌ 调用 DeepSeek 失败: {e}")
        return None

# 🔄 游戏主循环 (每 8 秒跑一轮)
def main_loop():
    print("🚀 AI废土大逃杀『大脑核心』已启动！")
    round_count = 1
    
    while True:
        print(f"\n================ 🌀 第 {round_count} 回合 ================")
        
        # 1. 模拟 YouTube 弹幕涌入
        chats = generate_mock_danmu()
        print("📥 [弹幕池] 当前收集到的观众弹幕:")
        for c in chats:
            print(f"  {c}")
            
        # 2. 调用 DeepSeek 推演剧情
        script = ask_deepseek_for_story(chats)
        
        if script:
            print("\n🎬 [DeepSeek 剧本生成成功！]")
            print(f"🌍 全局大事件: {script.get('world_event')}")
            
            # 3. 根据 DeepSeek 的指示，更新我们本地的玩家血量和状态
            chars = script.get("characters", {})
            for name, p_info in chars.items():
                if name in players_status:
                    # 更新血量
                    players_status[name]["hp"] += p_info.get("hp_change", 0)
                    if players_status[name]["hp"] <= 0:
                        players_status[name]["hp"] = 0
                        players_status[name]["status"] = "死亡"
                    
                    # 更新武器
                    if p_info.get("new_weapon") and p_info.get("new_weapon") != "...":
                        players_status[name]["weapon"] = p_info["new_weapon"]
                        
                    print(f"👤 {name} ({players_status[name]['mbti']}) 执行了 [{p_info.get('action')}]")
                    print(f"   💬 台词: \"{p_info.get('dialogue')}\"")
                    print(f"   🩸 血量变化: {p_info.get('hp_change', 0)} -> 当前HP: {players_status[name]['hp']} | 🛠️ 武器: {players_status[name]['weapon']}")
            
            # 4. 为了前端展示更友好，这里补充战况日志，并将胜利者写入最终剧本
            battle_log = []
            for name, p_info in chars.items():
                if name in players_status:
                    status_line = f"{name} {players_status[name]['mbti']} 执行了 [{p_info.get('action')}]"
                    if p_info.get('dialogue'):
                        status_line += f"，说: \"{p_info.get('dialogue')}\""
                    if p_info.get('hp_change', 0) != 0:
                        status_line += f"，HP 变化 {p_info.get('hp_change')}"
                    if p_info.get('new_weapon') and p_info.get('new_weapon') not in ['...', '无']:
                        status_line += f"，获得武器 {p_info.get('new_weapon')}"
                    battle_log.append(status_line)
            script['battle_log'] = battle_log
            alive = [n for n, p in players_status.items() if p['hp'] > 0]
            if len(alive) <= 1:
                script['game_over'] = True
                script['winner'] = alive[0] if alive else None
                script['world_event'] = script.get('world_event', '决赛结果已出')

            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "game_script.json")
            tmp_path = os.path.join(current_dir, "game_script.json.tmp")

            # 先写到临时文件里，网页完全察觉不到
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(script, f, ensure_ascii=False, indent=2)

            # 写完的一瞬间，以微秒级速度替换过去，完美避开网页的抓取！
            os.replace(tmp_path, json_path)
                
        else:
            print("⚠️ 本回合剧本难产，跳过...")
            
        # 检查游戏是否结束
        alive = [n for n, p in players_status.items() if p["hp"] > 0]
        if len(alive) <= 1:
            print(f"\n🏆 游戏结束！幸存者是: {alive if alive else '无人'}")
            break
            
        round_count += 1
        time.sleep(8) # 每8秒推演一次剧情

if __name__ == "__main__":
    main_loop()