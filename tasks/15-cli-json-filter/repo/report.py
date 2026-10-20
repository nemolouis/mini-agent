def summarize(rows):
    total = sum(r["amount"] for r in rows)
    return {
        "count": len(rows),
        "total": total,
        "average": total / len(rows) if rows else 0,
    }


def format_text(s):
    return f"count={s['count']} total={s['total']} average={s['average']:.2f}"
