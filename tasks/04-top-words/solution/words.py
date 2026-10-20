from collections import Counter


def top_words(text, n):
    counts = Counter(text.lower().split())
    return [w for w, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]
