from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL, TIMESTAMP, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ENUM
from .database import Base
from enum import Enum as PyEnum

class UserRole(PyEnum):
    buyer = "buyer"
    farmer = "farmer"

class User(Base):
    __tablename__ = "User"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(40), nullable=False)
    last_name = Column(String(40), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String, ForeignKey("Phone.phone", onupdate="CASCADE"), nullable=False)
    password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.buyer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    phone_rel = relationship("Phone", back_populates="users")

class Phone(Base):
    __tablename__ = "Phone"
    phone = Column(String, primary_key=True, index=True)
    dnd = Column(Boolean)
    whatsapp = Column(Boolean)

    users = relationship("User", back_populates="phone_rel")

class FarmType(PyEnum):
    FARM = "FARM"
    ORCHARD = "ORCHARD"
    GARDEN = "GARDEN"

class Farm(Base):
    __tablename__='Farm'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('User.id', ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    type = Column(Enum(FarmType), default=FarmType.FARM)  
    name = Column(String(40), nullable=False)  
    description = Column(Text)  
    latitude = Column(DECIMAL(precision=10, scale=8))
    longitude = Column(DECIMAL(precision=10, scale=8))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    user_rel = relationship("User")
    farm_species = relationship("Farm_species", back_populates="farm")
    transactions = relationship("Transaction", back_populates="farm")

class Farm_species(Base):
    __tablename__ = "Farm_species"
    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("Farm.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    sub_species_id = Column(Integer, ForeignKey("Sub_species.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    name = Column(String(40), nullable=False)
    description = Column(Text)
    price = Column(DECIMAL, nullable=False)
    available_quantity = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    farm = relationship("Farm", back_populates="farm_species")
    sub_species = relationship("Sub_species")
    order_items = relationship("Order_item", back_populates="farm_species")

class Sub_species(Base):
    __tablename__ = "Sub_species"
    id = Column(Integer, primary_key=True, index=True)
    species_id = Column(Integer, ForeignKey("Species.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    name = Column(String(40), nullable=False)
    common_name = Column(String(60), nullable=False)
    description = Column(Text, nullable=False)
    growth_rate = Column(String, nullable=False)
    unique_traits = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    species = relationship("Species")

class Species(Base):
    __tablename__ = "Species"
    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(60), ForeignKey("Category.category", onupdate="CASCADE"), nullable=False)
    common_name = Column(String(60), nullable=False)
    scientific_name = Column(String(60), nullable=False)
    description = Column(Text, nullable=False)
    genus = Column(String(50), nullable=False)
    family = Column(String(50), nullable=False)
    optimal_temperature_min = Column(DECIMAL, nullable=False)
    optimal_temperature_max = Column(DECIMAL, nullable=False)
    optimal_humidity = Column(DECIMAL, nullable=False)
    optimal_ph = Column(DECIMAL, nullable=False)
    water_requirement_per_litre = Column(DECIMAL, nullable=False)
    nutritient_requirement_per_kg = Column(DECIMAL, nullable=False)
    lifespan = Column(Integer, nullable=False)
    native_region = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    category = relationship("Category")
    sub_species = relationship("Sub_species", back_populates="species")

class Category(Base):
    __tablename__ = "Category"
    category = Column(String(60), primary_key=True, index=True)
    description = Column(Text)

    species = relationship("Species", back_populates="category")

class Order(Base):
    __tablename__ = "Order"
    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    name = Column(String(40), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    farmer = relationship("User")
    order_items = relationship("Order_item", back_populates="order")

class Order_item(Base):
    __tablename__ = "Order_item"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("Order.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    farm_species_id = Column(Integer, ForeignKey("Farm_species.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(DECIMAL, nullable=False)
    total_price = Column(DECIMAL, nullable=False)

    order = relationship("Order", back_populates="order_items")
    farm_species = relationship("Farm_species", back_populates="order_items")

class Transaction(Base):
    __tablename__ = "Transaction"
    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    farm_id = Column(Integer, ForeignKey("Farm.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("Order.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    total_amount = Column(DECIMAL, nullable=False)
    status = Column(String, nullable=False)
    payment_method = Column(String, nullable=False)
    transaction_date = Column(TIMESTAMP(timezone=True), server_default=func.now())

    buyer = relationship("User")
    farm = relationship("Farm", back_populates="transactions")
    order = relationship("Order")