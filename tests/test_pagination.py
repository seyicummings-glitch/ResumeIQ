from app.models.models import User
from app.services.pagination import paginate, page_response


def _make_users(db_session, count):
    for i in range(count):
        db_session.add(User(email=f"user{i}@example.com", hashed_password="x", full_name=f"User {i}"))
    db_session.commit()


def test_paginate_returns_requested_page_and_total(db_session):
    _make_users(db_session, 25)
    query = db_session.query(User).order_by(User.id)

    items, total = paginate(query, page=1, page_size=10)
    assert total == 25
    assert len(items) == 10
    assert [u.email for u in items] == [f"user{i}@example.com" for i in range(10)]

    items_page_3, total_page_3 = paginate(query, page=3, page_size=10)
    assert total_page_3 == 25
    assert len(items_page_3) == 5


def test_paginate_clamps_page_and_page_size(db_session):
    _make_users(db_session, 5)
    query = db_session.query(User).order_by(User.id)

    items, total = paginate(query, page=0, page_size=1000)
    assert total == 5
    assert len(items) == 5  # page_size clamped down to at most 100, but only 5 rows exist

    items_negative_page, _ = paginate(query, page=-3, page_size=2)
    assert len(items_negative_page) == 2  # negative page clamps to 1


def test_page_response_shape():
    envelope = page_response(items=[1, 2, 3], total=10, page=2, page_size=3)
    assert envelope == {"items": [1, 2, 3], "total": 10, "page": 2, "pageSize": 3}
