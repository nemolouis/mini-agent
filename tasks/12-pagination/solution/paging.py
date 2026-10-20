def total_pages(n_items, size):
    return -(-n_items // size)


def page_slice(items, page, size):
    if page < 1:
        raise ValueError("page must be >= 1")
    start = (page - 1) * size
    return items[start:start + size]
