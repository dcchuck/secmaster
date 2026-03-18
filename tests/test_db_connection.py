from sqlmodel import text


def test_db_connection(session):
    result = session.exec(text("SELECT 1")).scalar()
    assert result == 1
