import os, requests, datetime

SECIDS = "1.000905,1.000300,0.000852"
FIELDS = "f12,f14,f2,f3,f4,f15,f16,f17,f18"
UT = "fa5fd1943c7b386f172d6893dbfba10b"


def _p(v):
    """修六位数裸值：放大100倍的还原，统一2位小数"""
    try:
        x = float(v)
    except Exception:
        return str(v)
    if x > 100000 and x == int(x):
        x = x / 100
    return f"{x:,.2f}"


def fetch():
    r = requests.get(
        "https://push2.eastmoney.com/api/qt/ulist.np/get",
        params={"fields": FIELDS, "secids": SECIDS, "ut": UT},
        timeout=15,
    )
    d = r.json()
    diff = d.get("data", {}).get("diff") if isinstance(d.get("data"), dict) else None
    return diff


def row(n):
    pct = float(n["f3"])
    return {
        "name": n["f14"], "code": n["f12"],
        "price": _p(n["f2"]),
        "pct": pct,
        "prev": _p(n["f18"]),
        "open": _p(n["f17"]),
        "high": _p(n["f15"]),
        "low":  _p(n["f16"]),
    }


def main():
    sendkey = os.environ.get("SERVERCHAN_SENDKEY")
    if not sendkey:
        raise SystemExit("缺少 SERVERCHAN_SENDKEY")

    raw = fetch()
    if not raw:
        requests.post(f"https://sctapi.ftqq.com/{sendkey}.send",
                      data={"title": "A股日报", "desp": "今日非交易日或无行情，跳过。"})
        return

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"📈 A股核心指数日报", f"更新 {now}", "─" * 18, ""]

    for r in raw:
        x = row(r)
        if x["pct"] > 0:   tag = f"+{x['pct']:.2f}% ▲"
        elif x["pct"] < 0: tag = f"{x['pct']:.2f}% ▼"
        else:               tag = "0.00% —"
        lines += [
            f"{x['name']}({x['code']})",
            f"  点位  {x['price']}    {tag}",
            f"  昨收 {x['prev']}  开 {x['open']}  高 {x['high']}  低 {x['low']}",
            "",
        ]

    avg = sum(row(r)["pct"] for r in raw) / len(raw)
    if avg > 1:   mood = "整体偏强，注意追高"
    elif avg > 0: mood = "小幅回暖，结构行情"
    elif avg > -1:mood = "窄幅震荡，观望为主"
    else:         mood = "整体偏弱，注意风控"
    lines.append(f"👉 {mood}")
    lines.append("")
    lines.append("数据：东方财富 · 仅供参考")

    text = "\n".join(lines)

    resp = requests.post(
        f"https://sctapi.ftqq.com/{sendkey}.send",
        data={"title": "📈 A股指数日报", "desp": text},
        timeout=15,
    )
    print(resp.status_code, resp.text)


if __name__ == "__main__":
    main()
