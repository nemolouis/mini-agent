from collections import Counter

def top_words(text, n):
    words = text.split()
    counts = Counter(words)
    return [w for w, _ in sorted(counts.items(), key=lambda kv: kv[1])[:n]]
