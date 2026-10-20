def total_pages(n_items, size):
    return n_items // size


def page_slice(items, page, size):
    start = page * size
    return items[start:start + size]
