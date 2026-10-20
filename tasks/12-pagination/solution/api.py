from paging import page_slice, total_pages


def list_users(users, page=1, size=10):
    pages = total_pages(len(users), size)
    return {
        "items": page_slice(users, page, size),
        "page": page,
        "total_pages": pages,
        "has_next": page < pages,
    }
