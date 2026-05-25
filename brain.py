"""
AI废土大逃杀 — 指令驱动版

模式：
- 用户从输入框发送指令 → 调 DeepSeek 生成剧情 + 状态变化
- 无指令时 → 角色自动待机（预设文本轮播，不调DS）
- 每15分钟自动触发一次"世界事件"增加变数（调DS）
"""

import os
import time
import threading
import http.server
import socketserver
import json
import random
from openai import OpenAI

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMANDS_PATH = os.path.join(CURRENT_DIR, "commands.json")
SCRIPT_PATH = os.path.join(CURRENT_DIR, "game_script.json")

# ===== DeepSeek 客户端 =====
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
client = None
if DEEPSEEK_API_KEY:
    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        print("✅ DeepSeek 客户端已初始化")
    except Exception:
        client = None

if not client:
    print("⚠️ 未设置 DEEPSEEK_API_KEY，可在浏览器中通过 /set_api_key 注入")
    print("   不注入则指令只更新状态，不生成叙事文本")

def get_client():
    global client
    if client:
        return client
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    try:
        client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
        return client
    except Exception:
        return None

# ===== 角色初始状态 =====
players_status = {
    "A": {"mbti": "ESTP 企业家", "hp": 100, "weapon": "拳头", "status": "健康"},
    "B": {"mbti": "INFP 调停者", "hp": 100, "weapon": "拳头", "status": "健康"},
    "C": {"mbti": "INTJ 建筑师", "hp": 100, "weapon": "拳头", "status": "健康"},
    "D": {"mbti": "ENFP 竞选者", "hp": 100, "weapon": "拳头", "status": "健康"},
    "E": {"mbti": "ISTJ 物流师", "hp": 100, "weapon": "拳头", "status": "健康"},
}

# ===== 预设待机气泡（不调DS，循环使用） =====
IDLE_BUBBLES = {
    "A": ["哼……", "来啊！", "有点无聊", "谁想找死？", "这破地方"],
    "B": ["好累……", "我想回家", "那边有声音", "……", "还能撑多久"],
    "C": ["观察中", "有意思", "别轻举妄动", "计算胜率中", "……策略优先"],
    "D": ["大家加油！", "嘿！", "我还能打", "冲啊！", "别放弃！"],
    "E": ["按计划行事", "警戒中", "物资优先", "保持队形", "……没问题"],
}

# ===== 武器伤害表 =====
WEAPON_DAMAGE = {
    "拳头": 8, "铁管": 12, "木棍": 10, "钢管": 14, "小刀": 15,
    "霰弹枪": 25, "手枪": 18, "步枪": 22, "冲锋枪": 20,
    "砍刀": 18, "平底锅": 10, "木盾": 5,
}

# ===== JSON 读写 =====
def load_json(path):
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ===== 指令解析与应用 =====
def apply_command(cmd):
    """根据用户指令直接修改状态，返回叙事文本"""
    rid = cmd.get("role", "")
    action = cmd.get("action", "")
    target = cmd.get("target", "")

    if rid not in players_status:
        return f"角色 {rid} 不存在"

    p = players_status[rid]
    narrative_parts = []

    if action == "attack" and target and target in players_status:
        t = players_status[target]
        if t["hp"] <= 0:
            return f"{rid} 攻击了 {target}，但 {target} 已经倒下了。"
        atk_weapon = p.get("weapon", "拳头")
        base_damage = WEAPON_DAMAGE.get(atk_weapon, 8)
        damage = random.randint(int(base_damage * 0.7), int(base_damage * 1.3))
        t["hp"] = max(0, t["hp"] - damage)
        t["status"] = "死亡" if t["hp"] <= 0 else "受伤" if t["hp"] < 30 else "健康"
        narrative_parts.append(
            f"{rid} 用 {atk_weapon} 攻击了 {target}，造成 {damage} 点伤害！"
            f" {target} 剩余 HP: {t['hp']}"
        )
        if t["hp"] <= 0:
            narrative_parts.append(f"💀 {target} 倒下了！")
        return "\n".join(narrative_parts)

    elif action == "scavenge":
        # 搜刮：可能获得武器或回血
        found_weapons = ["铁管", "小刀", "手枪", "霰弹枪", "砍刀", "平底锅"]
        if random.random() < 0.4:
            new_w = random.choice(found_weapons)
            p["weapon"] = new_w
            narrative_parts.append(f"{rid} 搜刮到了 {new_w}！")
        if random.random() < 0.2:
            heal = random.randint(5, 15)
            p["hp"] = min(100, p["hp"] + heal)
            narrative_parts.append(f"{rid} 找到了急救物资，回复了 {heal} HP。")
        if not narrative_parts:
            narrative_parts.append(f"{rid} 搜了一圈，没什么收获。")
        return "\n".join(narrative_parts)

    elif action == "hide":
        narrative_parts.append(f"{rid} 躲了起来，暂时安全。")
        return "\n".join(narrative_parts)

    elif action == "run":
        narrative_parts.append(f"{rid} 向远处跑去。")
        return "\n".join(narrative_parts)

    elif action == "defend":
        narrative_parts.append(f"{rid} 摆出防御姿态。")
        return "\n".join(narrative_parts)

    elif action == "heal" and target and target in players_status:
        t = players_status[target]
        heal = random.randint(5, 15)
        t["hp"] = min(100, t["hp"] + heal)
        t["status"] = "健康" if t["hp"] > 30 else "受伤"
        narrative_parts.append(f"{rid} 帮助了 {target}，{target} 回复了 {heal} HP。")
        return "\n".join(narrative_parts)

    else:
        return f"{rid} 执行了指令: {action}"


# ===== 构建待机剧本 =====
LAST_EVENT_TIME = time.time()
EVENT_INTERVAL = 900  # 15分钟

def build_idle_script():
    """无指令时写入待机状态，角色冒气泡+随机小动作"""
    global LAST_EVENT_TIME

    chars = {}
    for rid, p in players_status.items():
        if p["hp"] <= 0:
            chars[rid] = {
                "dialogue": "……", "hp_change": 0,
                "action": "dead", "new_weapon": "..."
            }
        else:
            bubble = random.choice(IDLE_BUBBLES.get(rid, ["……"]))
            actions = ["idle", "wander", "rest"]
            chars[rid] = {
                "dialogue": bubble, "hp_change": 0,
                "action": random.choice(actions), "new_weapon": "..."
            }

    # 15分钟触发一次世界事件
    now = time.time()
    world_event = "废土上一片寂静……"
    if now - LAST_EVENT_TIME >= EVENT_INTERVAL:
        world_events = [
            "远处传来爆炸声，地面微微震动。",
            "一架无人机从天空掠过，投下了一个箱子。",
            "辐射风暴正在逼近，空气中弥漫着不安。",
            "废墟中传来无线电信号，断断续续。",
            "夜幕降临，温度骤降。",
        ]
        world_event = random.choice(world_events)
        LAST_EVENT_TIME = now

    script = {
        "world_event": world_event,
        "characters": chars,
        "idle": True,
    }
    save_json(SCRIPT_PATH, script)


# ===== 调用 DeepSeek 生成剧情 =====
def ask_deepseek_for_story(cmd, story_context=""):
    """根据用户指令调用DS生成剧情"""
    cl = get_client()
    if not cl:
        return None

    system_prompt = """你是AI废土大逃杀的叙事导演。
场上有5个角色（A ESTP企业家 / B INFP调停者 / C INTJ建筑师 / D ENFP竞选者 / E ISTJ物流师），
他们在废土上为生存而战。

根据用户指令和当前状态，生成一段简短但生动的剧情。
你的输出必须严格是以下JSON格式，不要有多余文字：

{
  "narrative": "一段生动的剧情描述",
  "characters": {
    "A": {"dialogue": "角色台词", "hp_change": 0, "action": "动作", "new_weapon": "新武器或无则..."},
    ...
  }
}

注意：
- hp_change 正数为回血，负数为扣血
- 动作可以是 attack/scavenge/hide/run/defend/dead/idle
- 如果角色死亡，hp_change 要让他 hp 归零
- 武器只在获得新武器时填写，否则写"..."
"""

    user_content = json.dumps({
        "current_state": players_status,
        "story_context": story_context,
        "user_command": cmd,
    }, ensure_ascii=False)

    try:
        resp = cl.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.8,
        )
        result = json.loads(resp.choices[0].message.content.strip())
        return result
    except Exception as e:
        print(f"DS调用失败: {e}")
        return None


def apply_ds_result(script):
    """将DS生成的结果应用到玩家状态并写入文件"""
    chars = script.get("characters", {})
    if not chars:
        return

    for name, info in chars.items():
        if name not in players_status:
            continue
        p = players_status[name]
        p["hp"] += info.get("hp_change", 0)
        p["hp"] = max(0, min(100, p["hp"]))
        p["status"] = "死亡" if p["hp"] <= 0 else "受伤" if p["hp"] < 30 else "健康"
        if info.get("new_weapon") and info["new_weapon"] not in ["...", "无"]:
            p["weapon"] = info["new_weapon"]

    # 构建战报
    battle_log = []
    for name, info in chars.items():
        if name in players_status:
            line = f"{name} {players_status[name]['mbti']} {info.get('action', 'idle')}"
            if info.get("dialogue"):
                line += f' "{info["dialogue"]}"'
            if info.get("hp_change", 0) != 0:
                line += f" HP{info['hp_change']:+d}"
            battle_log.append(line)

    alive = [n for n, p in players_status.items() if p["hp"] > 0]
    script["battle_log"] = battle_log
    if len(alive) <= 1:
        script["game_over"] = True
        script["winner"] = alive[0] if alive else None

    save_json(SCRIPT_PATH, script)


# ===== HTTP 服务器 =====
class Handler(http.server.BaseHTTPRequestHandler):
    def _json(self, code=200, data=None):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        if data is not None:
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self._json(200)

    def do_GET(self):
        if self.path.startswith("/commands"):
            self._json(200, load_json(COMMANDS_PATH))
        elif self.path.startswith("/status"):
            self._json(200, {"players": players_status})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        from urllib.parse import urlparse
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))

        if parsed.path.startswith("/set_api_key"):
            key = body.get("key")
            if not key:
                self._json(400, {"error": "missing key"})
                return
            os.environ["DEEPSEEK_API_KEY"] = key
            try:
                global client
                client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
                self._json(200, {"ok": True})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if parsed.path.startswith("/command"):
            role = body.get("role")
            if not role:
                self._json(400, {"error": "missing role"})
                return
            cmds = load_json(COMMANDS_PATH)
            cmds[role] = body
            save_json(COMMANDS_PATH, cmds)
            self._json(200, {"ok": True})
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, *args):
        pass


def start_http(port=9001):
    try:
        s = socketserver.ThreadingTCPServer(("127.0.0.1", port), Handler)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        print(f"🔌 HTTP: 127.0.0.1:{port}")
    except Exception as e:
        print(f"⚠️ HTTP启动失败: {e}")


# ===== 主循环 =====
def main():
    global LAST_EVENT_TIME
    print("🚀 指令驱动版已启动")
    print("   有指令 → 调DS生成剧情")
    print("   无指令 → 角色自动待机（预设气泡，不调DS）")
    start_http()

    # 初始剧本
    init_chars = {r: {"dialogue": "待命中…", "hp_change": 0, "action": "idle", "new_weapon": "..."} for r in players_status}
    save_json(SCRIPT_PATH, {"world_event": "5个幸存者在废土上游荡。", "characters": init_chars})

    LAST_EVENT_TIME = time.time()
    last_idle_time = time.time()
    IDLE_INTERVAL = 8  # 秒，无指令时前端刷新间隔
    story_context = []

    while True:
        # 检查游戏是否结束
        alive = [n for n, p in players_status.items() if p["hp"] > 0]
        if len(alive) <= 1:
            print(f"🏆 游戏结束！{alive[0] if alive else '无人'}")
            save_json(SCRIPT_PATH, {"world_event": "决赛结束", "game_over": True, "winner": alive[0] if alive else None})
            break

        now = time.time()
        has_commands = bool(load_json(COMMANDS_PATH))

        if has_commands:
            # 有指令 → 消费并处理
            cmds = load_json(COMMANDS_PATH)
            print(f"\n🎯 收到 {len(cmds)} 条指令: {list(cmds.keys())}")

            # 先尝试调DS
            cmd_text = "; ".join([f"{k}: {v.get('action')} {v.get('target','')}" for k, v in cmds.items()])
            script = ask_deepseek_for_story(cmd_text, story_context[-3:])

            if script:
                print(f"📖 DS剧情: {script.get('narrative', '')[:60]}...")
                story_context.append(script.get("narrative", ""))
                if len(story_context) > 10:
                    story_context = story_context[-10:]
                apply_ds_result(script)
            else:
                # DS不可用 → 本地计算
                print("⚠️ DS不可用，使用本地计算")
                log_lines = []
                chars = {}
                for rid, cmd in cmds.items():
                    narrative = apply_command(cmd)
                    log_lines.append(narrative)
                    # 构建输出
                    if rid in players_status:
                        p = players_status[rid]
                        hp_change = 0  # apply_command 已经直接改了玩家状态
                        chars[rid] = {
                            "dialogue": narrative.split("\n")[0] if narrative else "...",
                            "hp_change": 0,
                            "action": cmd.get("action", "idle"),
                            "new_weapon": "...",
                        }
                        if cmd.get("target"):
                            chars[rid]["target"] = cmd["target"]
                # 补充未在指令中的角色
                for rid in players_status:
                    if rid not in chars:
                        p = players_status[rid]
                        chars[rid] = {
                            "dialogue": random.choice(IDLE_BUBBLES.get(rid, ["……"])),
                            "hp_change": 0,
                            "action": "idle",
                            "new_weapon": "...",
                        }
                script = {
                    "world_event": "指令执行",
                    "narrative": "\n".join(log_lines),
                    "characters": chars,
                }
                apply_ds_result(script)

            save_json(COMMANDS_PATH, {})
            last_idle_time = now

        else:
            # 无指令 → 待机模式，定时刷新气泡
            if now - last_idle_time >= IDLE_INTERVAL:
                build_idle_script()
                last_idle_time = now

        time.sleep(2)


if __name__ == "__main__":
    main()
