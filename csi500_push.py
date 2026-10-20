import os, requests, datetime

UT = "fa5fd1943c7b386f172d6893dbfba10b"

INDEXES = [
    ("1.000300", "沪深300",  "000300", "399300"),
    ("1.000905", "中证500",  "000905", "399905"),
    ("0.000852", "中证1000", "000852", "399852"),
]
FIELDS = "f12,f14,f2,f3,f15,f16,f18"


def _dec(v):
    try:
        return float(v) / 100
    except Exception:
        return 0.0


def fetch():
    secids = ",".join(i[0] for i in INDEXES)
    r = requests.get(
        "https://push2.eastmoney.com/api/qt/ulist.np/get",
        params={"fields": FIELDS, "secids": secids, "ut": UT},
        timeout=15,
    )
    d = r.json()
    return d.get("data", {}).get("diff") if isinstance(d.get("data"), dict) else None


def main():
    sendkey = os.environ.get("SERVERCHAN_SENDKEY")
    if not sendkey:
        raise SystemExit("缺少 SERVERCHAN_SENDKEY")

    raw = fetch()
    if not raw:
        requests.post(f"https://sctapi.ftqq.com/{sendkey}.send",
                      data={"title": "A股宽基日报", "desp": "今日非交易日，无行情。"})
        return

    by_code = {n["f12"]: n for n in raw}
    ds = datetime.datetime.now().strftime("%Y-%m-%d")

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

        direction = "涨" if pct >= 0 else "跌"
        sign = "+" if pct >= 0 else ""

        blocks.append(
            f"{name}（{c1} / {c2}）\n"
            f"报 {price:,.2f} 点，{direction} {sign}{pct:.2f}%。"
            f" 日内 {low:,.2f}–{high:,.2f}，昨收 {prev:,.2f}。"
        )

    sep = "————————————"
    desp = f"截至 {ds} 收盘\n\n" + (f"\n{sep}\n".join(blocks))

    requests.post(
        f"https://sctapi.ftqq.com/{sendkey}.send",
        data={"title": "📈 A股宽基收盘", "desp": desp},
        timeout=15,
    )
    print("ok")


if __name__ == "__main__":
    main()
