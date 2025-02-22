from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL, TIMESTAMP, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ENUM
from database import Base
from enum import Enum as PyEnum

class UserRole(PyEnum):
    buyer = "buyer"
    farmer = "farmer"

class User(Base):
    __tablename__ = "User"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(40))
    last_name = Column(String(40))
    phone = Column(String, ForeignKey("Phone.phone"))
    password = Column(String)
    role = Column(Enum(UserRole), default=UserRole.buyer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    phone_rel = relationship("Phone", back_populates="users")


class Phone(Base):
    __tablename__ = "Phone"
    phone = Column(String, primary_key=True, index=True)
    dnd = Column(Boolean)
    whatsapp = Column(Boolean)

    users = relationship("User", back_populates="phone_rel")