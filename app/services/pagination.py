"""Shared pagination helper for admin list endpoints. Every new admin list route
builds its filtered SQLAlchemy query first, then calls paginate() on it and
wraps the result with page_response() for a consistent {items, total, page,
pageSize} envelope across the whole admin API."""
from sqlalchemy.orm import Query


def paginate(query: Query, page: int, page_size: int) -> tuple[list, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = query.order_by(None).count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def page_response(items: list, total: int, page: int, page_size: int) -> dict:
    return {"items": items, "total": total, "page": page, "pageSize": page_size}
