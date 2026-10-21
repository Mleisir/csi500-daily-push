import os
import time
import requests
import datetime

UT = "fa5fd1943c7b386f172d6893dbfba10b"

# 监控指数列表：(secid, 显示名称, 代码1, 代码2)
INDEXES = [
    ("1.000300",   "沪深300",  "000300", "399300"),
    ("1.000905",   "中证500",  "000905", "399905"),
    ("0.000852",   "中证1000", "000852", "399852"),
    ("124.HSTECH", "恒生科技", "HSTECH", "HSTECH"),
    ("0.399989",   "中证医疗", "399989", "399989"),
    ("1.000933",   "中证医药", "000933", "000933"),
]

FIELDS = "f12,f14,f2,f3,f15,f16,f18"

# 关键关注点位配置
TARGET_POINT_ZZ500 = 4800.0


def _dec(v):
    try:
        return float(v) / 100
    except Exception:
        return 0.0


def fetch():
    secids = ",".join(i[0] for i in INDEXES)
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {"fields": FIELDS, "secids": secids, "ut": UT}
    
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=20)
            d = r.json()
            return d.get("data", {}).get("diff") if isinstance(d.get("data"), dict) else None
        except Exception as e:
            print(f"网络请求出错 (尝试 {attempt + 1}/3): {e}")
            if attempt < 2:
                time.sleep(3)
            else:
                return None


def main():
    sendkey = os.environ.get("SERVERCHAN_SENDKEY")
    if not sendkey:
        raise SystemExit("缺少 SERVERCHAN_SENDKEY")

    ds = datetime.datetime.now().strftime("%Y-%m-%d")
    raw = fetch()
    
    if not raw:
        print("未能获取到行情数据，可能为网络超时或非交易日。")
        return

    by_code = {n["f12"]: n for n in raw}
    blocks = []

    for secid, name, c1, c2 in INDEXES:
        code = secid.split(".")[1]
        n = by_code.get(code)
        if not n:
            continue
        price = _dec(n["f2"])
        pct   = _dec(n["f3"])
        high  = _dec(n["f15"])
        low   = _dec(n["f16"])
        prev  = _dec(n["f18"])

        sign = "+" if pct >= 0 else ""
        emoji = "🔴" if pct >= 0 else "🟢"
        
        # 基础数据卡片
        card_lines = [
            f"{emoji} **{name}** (`{c1}`)",
            f"> 现价 **{price:,.2f}** ｜ 涨跌 **{sign}{pct:.2f}%**",
            f"> 日内 `{low:,.2f} ~ {high:,.2f}` ｜ 昨收 `{prev:,.2f}`"
        ]

        # 针对中证500增加“关键点位（4800点）”专属动态标注（符号与文案分两行展示）
        if code == "000905":
            diff = price - TARGET_POINT_ZZ500
            diff_pct = (diff / TARGET_POINT_ZZ500) * 100

            if diff < 0:
                text = f"低于目标 {abs(diff):,.2f} 点 (-{abs(diff_pct):,.2f}%)，可加大力度购买！"
            elif diff == 0:
                text = f"今日精准平收于 4800 点！"
            else:
                text = f"距离目标点位还差 +{diff:,.2f} 点 (+{diff_pct:.2f}%)"

            # 换行
            card_lines.append(f"\n📍 关键位 4800：{text}")

        blocks.append("\n".join(card_lines))

    sep = "\n\n" + "—" * 18 + "\n\n"
    desp = f"📅 **截至 {ds} 收盘**\n\n" + sep.join(blocks)

    requests.post(
        f"https://sctapi.ftqq.com/{sendkey}.send",
        data={"title": f"📈 A股主要宽基收盘播报", "desp": desp},
        timeout=15,
    )
    print("ok")


if __name__ == "__main__":
    main()
