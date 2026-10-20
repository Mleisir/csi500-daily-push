import os, requests, datetime

UT = "fa5fd1943c7b386f172d6893dbfba10b"


def _dec(v):
    """东方财富字段统一÷100"""
    try:
        return float(v) / 100
    except Exception:
        return 0.0


def main():
    sendkey = os.environ.get("SERVERCHAN_SENDKEY")
    if not sendkey:
        raise SystemExit("缺少 SERVERCHAN_SENDKEY")

    # 只抓中证500
    r = requests.get(
        "https://push2.eastmoney.com/api/qt/ulist.np/get",
        params={
            "fields": "f12,f14,f2,f3,f15,f16,f18",
            "secids": "1.000905",
            "ut": UT,
        },
        timeout=15,
    )
    d = r.json()
    diff = d.get("data", {}).get("diff") if isinstance(d.get("data"), dict) else None
    if not diff:
        requests.post(f"https://sctapi.ftqq.com/{sendkey}.send",
                      data={"title": "中证500日报", "desp": "今日非交易日，无行情。"})
        return

    n = diff[0]
    ds    = datetime.datetime.now().strftime("%Y-%m-%d")
    price = _dec(n["f2"])
    pct   = _dec(n["f3"])
    high  = _dec(n["f15"])
    low   = _dec(n["f16"])
    prev  = _dec(n["f18"])

    direction = "涨" if pct >= 0 else "跌"
    sign = "+" if pct >= 0 else ""

    # ===== 就这两行，不多不少 =====
    line1 = f"截至 {ds} 收盘，中证500（000905 / 399905）报 {price:,.2f} 点，{direction} {sign}{pct:.2f}%。"
    line2 = f"日内区间：{low:,.2f} – {high:,.2f}；昨收 {prev:,.2f}。"

    desp = f"{line1}\n\n{line2}"

    requests.post(
        f"https://sctapi.ftqq.com/{sendkey}.send",
        data={"title": "📈 中证500收盘", "desp": desp},
        timeout=15,
    )


if __name__ == "__main__":
    main()
