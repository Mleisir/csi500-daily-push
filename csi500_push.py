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


def _fmt_price(raw):
    """东方财富 f2 类字段：有的返整数放大100倍，有的已是实数，统一处理"""
    try:
        v = float(raw)
    except Exception:
        return raw
    # 判断：>100000 且能整除100的，多半是放大值
    if v > 100000 and v == int(v):
        v = v / 100
    return f"{v:,.2f}"

def fmt_row(node):
    return {
        "code": node["f12"],
        "name": node["f14"],
        "price": _fmt_price(node["f2"]),
        "pct": float(node["f3"]),
        "chg": float(node["f4"]),
        "high": _fmt_price(node["f15"]),
        "low": _fmt_price(node["f16"]),
        "open": _fmt_price(node["f17"]),
        "prev_close": _fmt_price(node["f18"]),
    }


def build_html(rows):
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M")

    blocks = []
    for r in rows:
        pct = r["pct"]
        if pct > 0:
            color, arrow = "#e74c3c", "▲"   # 红涨
        elif pct < 0:
            color, arrow = "#27ae60", "▼"   # 绿跌
        else:
            color, arrow = "#888", "—"

        pct_str = f"{pct:+.2f}%"
        blocks.append(f"""
<div style="background:#fafafa;border-radius:12px;padding:14px 16px;margin:10px 0;
            box-shadow:0 1px 3px rgba(0,0,0,.06);font-family:-apple-system,sans-serif;">
  <div style="font-size:16px;font-weight:600;color:#222;">{r['name']}
    <span style="font-size:13px;color:#999;margin-left:6px;">{r['code']}</span>
  </div>
  <div style="margin-top:8px;display:flex;justify-content:space-between;align-items:baseline;">
    <span style="font-size:26px;font-weight:700;color:#222;">{r['price']}</span>
    <span style="font-size:16px;font-weight:600;color:{color};">{arrow}{pct_str}</span>
  </div>
  <div style="margin-top:8px;font-size:13px;color:#666;display:flex;justify-content:space-between;">
    <span>昨收 {r['prev_close']}</span>
    <span>开 {r['open']}</span>
    <span>高 {r['high']}</span>
    <span>低 {r['low']}</span>
  </div>
</div>""")

    # 情绪
    avg = sum(r["pct"] for r in rows) / len(rows)
    if avg > 1:   mood = "📈 全线偏强，注意追高"
    elif avg > 0: mood = "🌤 小幅偏暖，结构性行情"
    elif avg > -1:mood = "⏸ 窄幅震荡，观望为主"
    else:         mood = "📉 偏弱整理，注意风控"

    html = f"""<!DOCTYPE html><html><body style="background:#f5f5f5;padding:0;margin:0;">
<div style="padding:12px 14px;background:#111;color:#fff;">
  <div style="font-size:15px;">📈 A股核心指数日报</div>
  <div style="font-size:12px;color:#aaa;margin-top:4px;">{date_str} · 仅收盘快照</div>
</div>
{''.join(blocks)}
<div style="padding:12px 16px;font-size:13px;color:#555;line-height:1.7;">
{mood}
</div>
<div style="padding:8px 16px 16px;font-size:11px;color:#bbb;">数据：东方财富 · 不构成投资建议</div>
</body></html>"""
    return html

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

def push(title, content_html):
    sendkey = os.environ["SERVERCHAN_SENDKEY"]
    # Server酱：title 纯文本，desp 传 HTML
    r = requests.post(
        f"https://sctapi.ftqq.com/{sendkey}.send",
        data={"title": title, "desp": content_html},   # ← 直接塞 HTML
        timeout=15,
    )
    print(r.status_code, r.text)


def main():
    rows_raw = fetch_quotes()
    if rows_raw is None:
        push("📈 A股日报", "今日非交易日，跳过。")
        return
    rows = [fmt_row(n) for n in rows_raw]
    html = build_html(rows)
    push("📈 A股核心指数日报", html)


if __name__ == "__main__":
    main()
