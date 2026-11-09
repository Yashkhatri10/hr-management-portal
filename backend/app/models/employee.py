from sqlalchemy import Boolean, Column, Integer, String

from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False)
    department = Column(String, nullable=False)
    location = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Active")
    manager = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
