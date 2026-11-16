"""One-off: create the first admin user directly in the DB (no self-registration endpoint exists)."""
import bcrypt
from models import User, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from config import settings


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw[:72].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


engine = create_engine(settings.DATABASE_URL)
session = Session(bind=engine)

existing = session.query(User).filter(User.username == "admin@gmail.com").first()
if not existing:
    session.add(User(username="admin@gmail.com", password_hash=hash_password("admin@123"), roles=["admin"]))
    session.commit()
    print("Created admin@gmail.com / admin@123")
else:
    print("admin@gmail.com already exists")

session.close()
