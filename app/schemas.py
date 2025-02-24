from pydantic import BaseModel
from pydantic.networks import EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr  
    
class UserCreate(UserBase):
    phone: str  
    password: str  
    role: str = "buyer"  

class UserUpdate(UserBase):
    first_name: Optional[str] = None 
    last_name: Optional[str] = None 
    email: Optional[EmailStr] = None 
    phone: Optional[str] = None 
    new_password: Optional[str] = None  
    role: Optional[str] = None  

class User(UserBase):      
        id: int  
        created_at: datetime  
        role: str
        
        class Config:
            from_attributes = True  

class FarmBase(BaseModel):
    farmer_id: int
    type: str
    name: str
    description: str
    latitude: float
    longitude: float

class FarmCreate(FarmBase):
    pass

class FarmUpdate(FarmBase):
    type: Optional[str] = None 
    name: Optional[str] = None 
    description: Optional[str] = None 
    latitude: Optional[float] = None  
    longitude: Optional[float] = None  

class Farm(FarmBase):
    id: int
    created_at: datetime
        
    class Config:
        from_attributes = True  

class FarmSpeciesBase(BaseModel):
    farm_id: int
    sub_species_id: int
    name: str
    description: Optional[str] = None
    price: float
    available_quantity: int

class FarmSpeciesCreate(FarmSpeciesBase):
    pass

class FarmSpeciesUpdate(FarmSpeciesBase):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    available_quantity: Optional[int] = None

class FarmSpecies(FarmSpeciesBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True 

class SpeciesBase(BaseModel):
    category_id: int
    common_name: str
    scientific_name: str
    description: str
    genus: str
    family: str
    optimal_temperature_min: float
    optimal_temperature_max: float
    optimal_humidity: float
    optimal_ph: float
    water_requirement_per_litre: float
    nutritient_requirement_per_kg: float
    lifespan: int
    native_region: str

class SpeciesCreate(SpeciesBase):
    pass

class SpeciesUpdate(SpeciesBase):
    common_name: Optional[str] = None
    scientific_name: Optional[str] = None
    description: Optional[str] = None
    genus: Optional[str] = None
    family: Optional[str] = None
    optimal_temperature_min: Optional[float] = None
    optimal_temperature_max: Optional[float] = None
    optimal_humidity: Optional[float] = None
    optimal_ph: Optional[float] = None
    water_requirement_per_litre: Optional[float] = None
    nutritient_requirement_per_kg: Optional[float] = None
    lifespan: Optional[int] = None
    native_region: Optional[str] = None

class Species(SpeciesBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True 

class SubSpeciesBase(BaseModel):
    species_id: int
    name: str
    common_name: str
    description: str
    growth_rate: str
    unique_traits: str

class SubSpeciesCreate(SubSpeciesBase):
    pass

class SubSpeciesUpdate(SubSpeciesBase):
    name: Optional[str] = None
    common_name: Optional[str] = None
    description: Optional[str] = None
    growth_rate: Optional[str] = None
    unique_traits: Optional[str] = None

class SubSpecies(SubSpeciesBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True 

class OrderBase(BaseModel):
    farmer_id: int
    name: str
    description: str

class OrderCreate(OrderBase):
    pass

class OrderUpdate(OrderBase):
    name: Optional[str] = None
    description: Optional[str] = None

class Order(OrderBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True 

class OrderItemBase(BaseModel):
    order_id: int
    farm_species_id: int
    quantity: int
    price: float

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemUpdate(OrderItemBase):
    quantity: Optional[int] = None
    price: Optional[float] = None

class OrderItem(OrderItemBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True 

class TransactionBase(BaseModel):
    buyer_id: int
    order_id: int
    farm_id: int
    total_amount: float
    status: str
    payment_method: str

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(TransactionBase):
    total_amount: Optional[float] = None
    status: Optional[str] = None
    payment_method: Optional[str] = None

class Transaction(TransactionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True 