import argparse
from app.db.session import SessionLocal
from app.db import base
from app.models.users import User, Role
from app.models.treasury import Treasury
from app.core.security import hash_password


def create_admin(username: str, full_name: str, password: str):
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter_by(username=username).first()
        if existing_user:
            print(f"❌ User '{username}' already exists.")
            return

        # Create admin user
        hashed_pw = hash_password(password)
        admin = User(
            username=username,
            full_name=full_name,
            hashed_password=hashed_pw,
            role=Role.admin,
            is_admin=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        # Create empty treasury for the new admin
        treasury = Treasury(employee_id=admin.id, balance=0.0)
        db.add(treasury)
        db.commit()

        print(f"✅ Admin '{username}' created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an admin user.")
    parser.add_argument("username", help="The admin's username")
    parser.add_argument("full_name", help="The admin's full name")
    parser.add_argument("password", help="The admin's password")
    args = parser.parse_args()

    create_admin(args.username, args.full_name, args.password)
