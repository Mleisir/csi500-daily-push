"""
中证500 + 沪深300 + 中证1000 每日收盘日报
数据来源：东方财富 push2 接口（免费，无需 Key）
推送：PushPlus → 微信服务号
"""
import os
import requests
import datetime

# ============ 配置 ============
SENDKEY = os.environ.get("SERVERCHAN_SENDKEY")
if not SENDKEY:
    raise SystemExit("缺少环境变量 SERVERCHAN_SENDKEY")

# secids 说明：
# 1.000905 = 中证500（上交所口径）
# 1.000300 = 沪深300
# 0.000852 = 中证1000（深交所口径用 0.）
SECIDS = "1.000905,1.000300,0.000852"
FIELDS = "f12,f14,f2,f3,f4,f15,f16,f17,f18"

UT = "fa5fd1943c7b386f172d6893dbfba10b"  # 固定即可

def fetch_quotes():
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fields": FIELDS,
        "secids": SECIDS,
        "ut": UT,
    }
    r = requests.get(url, params=params, timeout=15)
    r.encoding = "utf-8"
    r.raise_for_status()
    data = r.json()
    if data.get("rc") != 0 or not data.get("data", {}).get("diff"):
        raise SystemExit(f"行情接口返回异常: {data}")
    return data["data"]["diff"]


def fmt_row(node):
    """把单个指数节点整理成 dict"""
    return {
        "code": node["f12"],
        "name": node["f14"],
        "price": node["f2"],
        "pct": node["f3"],        # 涨跌幅 %
        "chg": node["f4"],        # 涨跌额
        "high": node["f15"],
        "low": node["f16"],
        "open": node["f17"],
        "prev_close": node["f18"],
    }


def build_markdown(rows):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    weekday = "一二三四五五六日"[datetime.datetime.now().weekday()]
    date_cn = f"{now}（周{weekday}）"

    lines = [
        f"# 📈 A股核心指数日报",
        "",
        f"更新时间：**{date_cn}**",
        "",
        "| 指数 | 最新点位 | 涨跌幅 | 涨跌额 | 昨收 | 今日高 | 今日低 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    summary = []
    for r in rows:
        pct = r["pct"]
        arrow = "🔴" if pct > 0 else ("🟢" if pct < 0 else "⚪️")
        pct_str = f"{pct:+.2f}%"
        chg_str = f"{r['chg']:+.2f}"
        lines.append(
            f"| {r['name']}({r['code']}) "
            f"| **{r['price']}** "
            f"| {arrow}{pct_str} "
            f"| {chg_str} "
            f"| {r['prev_close']} "
            f"| {r['high']} "
            f"| {r['low']} |"
        )
        summary.append((r["name"], pct))

    lines += [
        "",
        "## 🧭 一句话点评",
        "",
    ]

    # 简单情绪判断
    avg = sum(p for _, p in summary) / len(summary)
    if avg > 1.0:
        mood = "🟢 全线偏强，市场情绪积极，注意追高风险。"
    elif avg > 0:
        mood = "🔵 小幅上涨，结构性行情为主，控制仓位。"
    elif avg > -1.0:
        mood = "⚪️ 窄幅震荡，观望为主，等待方向明确。"
    else:
        mood = "🔴 普遍走弱，注意风控，避免盲目抄底。"

    lines.append(f"> {mood}")
    lines.append("")
    lines.append("---")
    lines.append(
        "<small>数据来源：东方财富行情接口 · "
        "仅供研究参考，不构成投资建议</small>"
    )

    return "\n".join(lines)

def push(title, content):
    sendkey = os.environ.get("SERVERCHAN_SENDKEY")
    if not sendkey:
        raise SystemExit("缺少 SERVERCHAN_SENDKEY")

    # Turbo 版接口
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    data = {
        "title": title,            # 标题，别带换行
        "desp": content,           # 正文，支持 Markdown
    }
    r = requests.post(url, data=data, timeout=15)
    print(r.status_code, r.text)
    # 成功时返回 JSON 里 code == 0


def main():
    rows = [fmt_row(n) for n in fetch_quotes()]
    md = build_markdown(rows)
    push("📈 A股核心指数日报", md)
    print("done")


if __name__ == "__main__":
    main()
