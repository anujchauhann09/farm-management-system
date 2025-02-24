import logging
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .database import engine, get_db
from . import models, schemas

logging.basicConfig(
    filename="app.log",  
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World!"}

@app.post("/api/v1/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Received request to create user")

    phone_entry = db.query(models.Phone).filter(models.Phone.phone == user.phone).first()

    if not phone_entry:
        try:
            new_phone = models.Phone(phone=user.phone)
            db.add(new_phone)
            db.commit()
            db.refresh(new_phone)
            logger.info(f"Phone number {user.phone} was not found, so it was added to Phone table.")
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Failed to insert phone number {user.phone}: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed to register phone number.")

    try:
        db_user = models.User(**user.dict())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"User created successfully: ID {db_user.id}, Phone {db_user.phone}")
        return db_user

    except IntegrityError as e:
        db.rollback()  
        logger.error(f"Database integrity error while creating user: {str(e)}")
        raise HTTPException(status_code=400, detail="User creation failed due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    logger.info(f"Received request to read user with ID: {user_id}")
    
    try:
        db_user = db.query(models.User).filter(models.User.id == user_id).first()
        
        if db_user is None:
            logger.error("User not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        return db_user

    except Exception as e:
        logger.critical(f"Unexpected error while reading user with ID {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")


@app.get("/api/v1/users/", response_model=list[schemas.User])
def read_users_list(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"Received request to read users with skip={skip} and limit={limit}")
    
    try:
        users = db.query(models.User).offset(skip).limit(limit).all()
        return users

    except Exception as e:
        logger.critical(f"Unexpected error while reading users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")


@app.patch("/api/v1/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    logger.info(f"Received request to partially update user with ID: {user_id}")
    
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        logger.error("User not found")
        raise HTTPException(status_code=404, detail="User not found")

    if user.first_name is not None:
        db_user.first_name = user.first_name
    if user.last_name is not None:
        db_user.last_name = user.last_name
    if user.email is not None:
        db_user.email = user.email  
    if user.role is not None:
        db_user.role = user.role  
    if user.new_password is not None:
        db_user.password = user.new_password

    if user.phone is not None:
        phone_entry = db.query(models.Phone).filter(models.Phone.phone == user.phone).first()
        
        if not phone_entry:
            try:
                new_phone = models.Phone(phone=user.phone)
                db.add(new_phone)
                logger.info(f"Phone number {user.phone} was not found, so it was added to Phone table.")
            except IntegrityError as e:
                db.rollback()
                logger.error(f"Failed to insert phone number {user.phone}: {str(e)}")
                raise HTTPException(status_code=400, detail="Failed to register phone number.")
        
        db_user.phone = user.phone  
    
    try:
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"User updated successfully: ID {db_user.id}")
        
    except Exception as e:
        logger.error(f"Failed to update user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update user.")

    return db_user

@app.delete("/api/v1/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    logger.info(f"Received request to delete user with ID: {user_id}")

    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if db_user is None:
        logger.error("User not found")
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        db.delete(db_user)
        db.commit()
        
        logger.info(f"User deleted successfully: ID {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to delete user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete user.")
    
    return {"message": "User deleted successfully"}

@app.post("/api/v1/users/{user_id}/farms/", response_model=schemas.Farm)
def create_farm(user_id: int, farm_data: schemas.FarmCreate, db: Session = Depends(get_db)):
    logger.info(f"Received request to create farm")

    # current_user = get_current_user(db, user_id)
    current_user = db.query(models.User).filter_by(id=user_id).first()
    
    if not current_user or current_user.role != models.UserRole.farmer:
        logger.error("User does not have farmer role.")
        raise HTTPException(status_code=403, detail="Only farmers can create farms.")

    try:
        new_farm = models.Farm(
            user_id=current_user.id,
            name=farm_data.name,
            description=farm_data.description,
            latitude=farm_data.latitude,
            longitude=farm_data.longitude,
        )
        
        db.add(new_farm)
        db.commit()
        db.refresh(new_farm)

        logger.info(f"Farm created successfully by user ID {current_user.id}: {new_farm.name}")
        return new_farm

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while creating farm: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to create farm due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while creating farm: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}/farms/{farm_id}", response_model=schemas.Farm)
def read_farm(user_id: int, farm_id: int, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} requested to read farm with ID {farm_id}.")
    
    try:
        farm = db.query(models.Farm).filter(models.Farm.id == farm_id, models.Farm.user_id == user_id).first()
        
        if not farm:
            logger.warning(f"Farm with ID {farm_id} not found for user ID {user_id} or user does not own it.")
            raise HTTPException(status_code=404, detail="Farm not found or you do not have permission to access this farm.")
        
        return farm

    except Exception as e:
        logger.critical(f"Unexpected error while reading farm with ID {farm_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/farms/", response_model=list[schemas.Farm])
def read_farms_list(db: Session = Depends(get_db)):
    logger.info("Received request to read all farms.")
    
    try:
        farms = db.query(models.Farm).all()
        logger.info(f"Successfully retrieved {len(farms)} farms.")
        return farms

    except Exception as e:
        logger.critical(f"Unexpected error while reading farms: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.patch("/api/v1/users/{user_id}/farms/{farm_id}", response_model=schemas.Farm)
def update_farm(user_id: int, farm_id: int, farm_data: schemas.FarmUpdate, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} requested to update farm with ID {farm_id}.")
    
    try:
        farm = db.query(models.Farm).filter(models.Farm.id == farm_id, models.Farm.user_id == user_id).first()
        
        if not farm:
            logger.warning(f"Farm with ID {farm_id} not found for user ID {user_id} or user does not own it.")
            raise HTTPException(status_code=404, detail="Farm not found or you do not have permission to update this farm.")
        
        if farm_data.type is not None:
            farm.type = farm_data.type
        if farm_data.name is not None:
            farm.name = farm_data.name
        if farm_data.description is not None:
            farm.description = farm_data.description
        if farm_data.latitude is not None:
            farm.latitude = farm_data.latitude
        if farm_data.longitude is not None:
            farm.longitude = farm_data.longitude

        db.commit()
        db.refresh(farm)
        
        logger.info(f"Farm with ID {farm_id} updated successfully by user ID {user_id}.")
        return farm

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while updating farm: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to update farm due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while updating farm: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.delete("/api/v1/users/{user_id}/farms/{farm_id}", response_model=dict)
def delete_farm(user_id: int, farm_id: int, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} requested to delete farm with ID {farm_id}.")
    
    try:
        farm = db.query(models.Farm).filter(models.Farm.id == farm_id, models.Farm.user_id == user_id).first()
        
        if not farm:
            logger.warning(f"Farm with ID {farm_id} not found for user ID {user_id} or user does not own it.")
            raise HTTPException(status_code=404, detail="Farm not found or you do not have permission to delete this farm.")
        
        db.delete(farm)
        db.commit()
        
        logger.info(f"Farm with ID {farm_id} deleted successfully by user ID {user_id}.")
        return {"detail": "Farm deleted successfully."}

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while deleting farm: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/api/v1/users/{user_id}/farms/{farm_id}/farm_species/", response_model=schemas.FarmSpecies)
def create_farm_species(user_id: int, farm_id: int, species_data: schemas.FarmSpeciesCreate, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} requested to create a farm species in farm ID {farm_id}.")

    current_user = db.query(models.User).filter_by(id=user_id).first()
    farm = db.query(models.Farm).filter(models.Farm.id == farm_id, models.Farm.user_id == user_id).first()

    if not current_user or not farm:
        logger.error("User does not have permission to create species in this farm.")
        raise HTTPException(status_code=403, detail="You do not have permission to create species in this farm.")

    try:
        new_species = models.Farm_species(
            farm_id=farm.id,
            # sub_species_id=species_data.sub_species_id,
            name=species_data.name,
            description=species_data.description,
            price=species_data.price,
            available_quantity=species_data.available_quantity,
        )
        
        db.add(new_species)
        db.commit()
        db.refresh(new_species)

        logger.info(f"Farm species created successfully by user ID {user_id}: {new_species.name}")
        return new_species

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while creating farm species: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to create farm species due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while creating farm species: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}/farms/{farm_id}/farm_species/{farm_species_id}", response_model=schemas.FarmSpecies)
def read_farm_species(user_id: int, farm_id: int, species_id: int, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} requested to read farm species with ID {species_id} in farm ID {farm_id}.")

    try:
        species = db.query(models.Farm_species).filter(
            models.Farm_species.id == species_id,
            models.Farm_species.farm_id == farm_id
        ).first()

        if not species:
            logger.warning(f"Farm species with ID {species_id} not found in farm ID {farm_id}.")
            raise HTTPException(status_code=404, detail="Farm species not found.")

        return species

    except Exception as e:
        logger.critical(f"Unexpected error while reading farm species with ID {species_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}/farms/{farm_id}/farm_species/", response_model=list[schemas.FarmSpecies])
def read_farm_species_list(user_id: int, farm_id: int, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} requested to read all farm species in farm ID {farm_id}.")

    try:
        species_list = db.query(models.Farm_species).filter(models.Farm_species.farm_id == farm_id).all()
        logger.info(f"Successfully retrieved {len(species_list)} species for farm ID {farm_id}.")
        return species_list

    except Exception as e:
        logger.critical(f"Unexpected error while reading all farm species for farm ID {farm_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.patch("/api/v1/users/{user_id}/farms/{farm_id}/farm_species/{farm_species_id}", response_model=schemas.FarmSpecies)
def update_farm_species(user_id: int, farm_id: int, species_id: int, species_data: schemas.FarmSpeciesUpdate, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} requested to update farm species with ID {species_id} in farm ID {farm_id}.")

    try:
        species = db.query(models.Farm_species).filter(
            models.Farm_species.id == species_id,
            models.Farm_species.farm_id == farm_id
        ).first()

        if not species:
            logger.warning(f"Farm species with ID {species_id} not found in farm ID {farm_id}.")
            raise HTTPException(status_code=404, detail="Farm species not found.")

        if species_data.name is not None:
            species.name = species_data.name
        if species_data.description is not None:
            species.description = species_data.description
        if species_data.price is not None:
            species.price = species_data.price
        if species_data.available_quantity is not None:
            species.available_quantity = species_data.available_quantity

        db.commit()
        db.refresh(species)

        logger.info(f"Farm species with ID {species_id} updated successfully by user ID {user_id}.")
        return species

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while updating farm species: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to update farm species due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while updating farm species with ID {species_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.delete("/api/v1/users/{user_id}/farms/{farm_id}/farm_species/{farm_species_id}", response_model=dict)
def delete_farm_species(user_id: int, farm_id: int, species_id: int, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} requested to delete farm species with ID {species_id} in farm ID {farm_id}.")

    try:
        species = db.query(models.Farm_species).filter(
            models.Farm_species.id == species_id,
            models.Farm_species.farm_id == farm_id
        ).first()

        if not species:
            logger.warning(f"Farm species with ID {species_id} not found in farm ID {farm_id}.")
            raise HTTPException(status_code=404, detail="Farm species not found.")

        db.delete(species)
        db.commit()

        logger.info(f"Farm species with ID {species_id} deleted successfully by user ID {user_id}.")
        return {"detail": "Farm species deleted successfully."}

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while deleting farm species with ID {species_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/api/v1/users/{user_id}/farms/{farm_id}/species/", response_model=schemas.Species)
def create_species(user_id: int, species_data: schemas.SpeciesCreate, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} requested to create a new species.")

    current_user = db.query(models.User).filter_by(id=user_id).first()
    if not current_user:
        logger.error("User not found.")
        raise HTTPException(status_code=404, detail="User not found.")

    category = db.query(models.Category).filter(models.Category.category == species_data.category_name).first()
    if not category:
        logger.error(f"Category with ID {species_data.category_name} does not exist.")
        try:
            new_category = models.Category(category=species_data.category_name)
            db.add(new_category)
            db.commit()
            db.refresh(new_category)
            logger.info(f"Category {species_data.category_name} was not found, so it was added to Category table.")
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Failed to insert category {species_data.category_name}: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed to insert category.")

    try:
        new_species = models.Species(
            category_name=species_data.category_name,
            common_name=species_data.common_name,
            scientific_name=species_data.scientific_name,
            description=species_data.description,
            genus=species_data.genus,
            family=species_data.family,
            optimal_temperature_min=species_data.optimal_temperature_min,
            optimal_temperature_max=species_data.optimal_temperature_max,
            optimal_humidity=species_data.optimal_humidity,
            optimal_ph=species_data.optimal_ph,
            water_requirement_per_litre=species_data.water_requirement_per_litre,
            nutritient_requirement_per_kg=species_data.nutritient_requirement_per_kg,
            lifespan=species_data.lifespan,
            native_region=species_data.native_region
        )

        db.add(new_species)
        db.commit()
        db.refresh(new_species)

        logger.info(f"Species created successfully by user ID {user_id}: {new_species.common_name}")
        return new_species

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while creating species: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to create species due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while creating species: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}/farms/{farm_id}/species/{species_id}", response_model=schemas.Species)
def read_species(user_id: int, species_id: int, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} requested to read species with ID {species_id}.")

    try:
        species = db.query(models.Species).filter(models.Species.id == species_id).first()

        if not species:
            logger.warning(f"Species with ID {species_id} not found.")
            raise HTTPException(status_code=404, detail="Species not found.")

        return species

    except Exception as e:
        logger.critical(f"Unexpected error while reading species with ID {species_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}/farms/{farm_id}/species/", response_model=list[schemas.Species])
def read_species_list(user_id: int, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} requested to read all species.")

    try:
        species_list = db.query(models.Species).all()
        logger.info(f"Successfully retrieved {len(species_list)} species.")
        return species_list

    except Exception as e:
        logger.critical(f"Unexpected error while reading all species: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.patch("/api/v1/users/{user_id}/farms/{farm_id}/species/{species_id}", response_model=schemas.Species)
def update_species(user_id: int, species_id: int, species_data: schemas.SpeciesUpdate, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} requested to update species with ID {species_id}.")

    try:
        species = db.query(models.Species).filter(models.Species.id == species_id).first()

        if not species:
            logger.warning(f"Species with ID {species_id} not found.")
            raise HTTPException(status_code=404, detail="Species not found.")

        if species_data.common_name is not None:
            species.common_name = species_data.common_name
        if species_data.scientific_name is not None:
            species.scientific_name = species_data.scientific_name
        if species_data.description is not None:
            species.description = species_data.description
        if species_data.genus is not None:
            species.genus = species_data.genus
        if species_data.family is not None:
            species.family = species_data.family
        if species_data.optimal_temperature_min is not None:
            species.optimal_temperature_min = species_data.optimal_temperature_min
        if species_data.optimal_temperature_max is not None:
            species.optimal_temperature_max = species_data.optimal_temperature_max
        if species_data.optimal_humidity is not None:
            species.optimal_humidity = species_data.optimal_humidity
        if species_data.optimal_ph is not None:
            species.optimal_ph = species_data.optimal_ph
        if species_data.water_requirement_per_litre is not None:
            species.water_requirement_per_litre = species_data.water_requirement_per_litre
        if species_data.nutritient_requirement_per_kg is not None:
            species.nutritient_requirement_per_kg = species_data.nutritient_requirement_per_kg
        if species_data.lifespan is not None:
            species.lifespan = species_data.lifespan
        if species_data.native_region is not None:
            species.native_region = species_data.native_region

        db.commit()
        db.refresh(species)

        logger.info(f"Species with ID {species_id} updated successfully by user ID {user_id}.")
        return species

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while updating species: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to update species due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while updating species with ID {species_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.delete("/api/v1/users/{user_id}/farms/{farm_id}/species/{species_id}", response_model=dict)
def delete_species(user_id: int, species_id: int, db: Session = Depends(get_db)):
    logger.info(f"User {user_id} requested to delete species with ID {species_id}.")

    try:
        species = db.query(models.Species).filter(models.Species.id == species_id).first()

        if not species:
            logger.warning(f"Species with ID {species_id} not found.")
            raise HTTPException(status_code=404, detail="Species not found.")

        db.delete(species)
        db.commit()

        logger.info(f"Species with ID {species_id} deleted successfully by user ID {user_id}.")
        return {"detail": "Species deleted successfully."}

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while deleting species with ID {species_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/api/v1/users/{user_id}/farms/{farm_id}/species/{species_id}/sub_species/", response_model=schemas.SubSpecies)
def create_sub_species(
    user_id: int, 
    species_id: int, 
    sub_species_data: schemas.SubSpeciesCreate, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to create a new sub-species under species ID {species_id}.")

    current_user = db.query(models.User).filter_by(id=user_id).first()
    if not current_user:
        logger.error("User not found.")
        raise HTTPException(status_code=404, detail="User not found.")

    species = db.query(models.Species).filter(models.Species.id == species_id).first()
    if not species:
        logger.error(f"Species with ID {species_id} not found.")
        raise HTTPException(status_code=404, detail="Species not found.")

    try:
        new_sub_species = models.Sub_species(
            species_id=species_id, 
            name=sub_species_data.name,
            common_name=sub_species_data.common_name,
            description=sub_species_data.description,
            growth_rate=sub_species_data.growth_rate,
            unique_traits=sub_species_data.unique_traits
        )

        db.add(new_sub_species)
        db.commit()
        db.refresh(new_sub_species)

        logger.info(f"Sub-species created successfully by user ID {user_id} under species ID {species_id}: {new_sub_species.name}")
        return new_sub_species

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while creating sub-species: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to create sub-species due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while creating sub-species: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}/farms/{farm_id}/species/{species_id}/sub_species/{sub_species_id}", response_model=schemas.SubSpecies)
def read_sub_species(
    user_id: int, 
    species_id: int, 
    sub_species_id: int, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to read sub-species with ID {sub_species_id} under species ID {species_id}.")

    try:
        sub_species = db.query(models.Sub_species).filter(
            models.Sub_species.id == sub_species_id,
            models.Sub_species.species_id == species_id  
        ).first()

        if not sub_species:
            logger.warning(f"Sub-species with ID {sub_species_id} not found under species ID {species_id}.")
            raise HTTPException(status_code=404, detail="Sub-species not found.")

        return sub_species

    except Exception as e:
        logger.critical(f"Unexpected error while reading sub-species with ID {sub_species_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}/farms/{farm_id}/species/{species_id}/sub_species/", response_model=list[schemas.SubSpecies])
def read_sub_species_list(
    user_id: int, 
    species_id: int, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to read all sub-species under species ID {species_id}.")

    try:
        sub_species_list = db.query(models.Sub_species).filter(
            models.Sub_species.species_id == species_id  # Filter sub-species by species ID
        ).all()
        logger.info(f"Successfully retrieved {len(sub_species_list)} sub-species under species ID {species_id}.")
        return sub_species_list

    except Exception as e:
        logger.critical(f"Unexpected error while reading all sub-species: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.patch("/api/v1/users/{user_id}/farms/{farm_id}/species/{species_id}/sub_species/{sub_species_id}", response_model=schemas.SubSpecies)
def update_sub_species(
    user_id: int, 
    species_id: int, 
    sub_species_id: int, 
    sub_species_data: schemas.SubSpeciesUpdate, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to update sub-species with ID {sub_species_id} under species ID {species_id}.")

    try:
        sub_species = db.query(models.Sub_species).filter(
            models.Sub_species.id == sub_species_id,
            models.Sub_species.species_id == species_id  
        ).first()

        if not sub_species:
            logger.warning(f"Sub-species with ID {sub_species_id} not found under species ID {species_id}.")
            raise HTTPException(status_code=404, detail="Sub-species not found.")

        if sub_species_data.name is not None:
            sub_species.name = sub_species_data.name
        if sub_species_data.common_name is not None:
            sub_species.common_name = sub_species_data.common_name
        if sub_species_data.description is not None:
            sub_species.description = sub_species_data.description
        if sub_species_data.growth_rate is not None:
            sub_species.growth_rate = sub_species_data.growth_rate
        if sub_species_data.unique_traits is not None:
            sub_species.unique_traits = sub_species_data.unique_traits

        db.commit()
        db.refresh(sub_species)

        logger.info(f"Sub-species with ID {sub_species_id} updated successfully by user ID {user_id}.")
        return sub_species

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while updating sub-species: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to update sub-species due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while updating sub-species with ID {sub_species_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.delete("/api/v1/users/{user_id}/farms/{farm_id}/species/{species_id}/sub_species/{sub_species_id}", response_model=dict)
def delete_sub_species(
    user_id: int, 
    species_id: int, 
    sub_species_id: int, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to delete sub-species with ID {sub_species_id} under species ID {species_id}.")

    try:
        sub_species = db.query(models.Sub_species).filter(
            models.Sub_species.id == sub_species_id,
            models.Sub_species.species_id == species_id  
        ).first()

        if not sub_species:
            logger.warning(f"Sub-species with ID {sub_species_id} not found under species ID {species_id}.")
            raise HTTPException(status_code=404, detail="Sub-species not found.")

        db.delete(sub_species)
        db.commit()

        logger.info(f"Sub-species with ID {sub_species_id} deleted successfully by user ID {user_id}.")
        return {"detail": "Sub-species deleted successfully."}

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while deleting sub-species with ID {sub_species_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/api/v1/users/{user_id}/orders/", response_model=schemas.Order)
def create_order(
    user_id: int, 
    order_data: schemas.OrderCreate, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to create a new order.")

    current_user = db.query(models.User).filter_by(id=user_id).first()
    if not current_user:
        logger.error("User not found.")
        raise HTTPException(status_code=404, detail="User not found.")

    farmer = db.query(models.User).filter(models.User.id == order_data.farmer_id).first()
    if not farmer:
        logger.error(f"Farmer with ID {order_data.farmer_id} not found.")
        raise HTTPException(status_code=404, detail="Farmer not found.")

    try:
        new_order = models.Order(
            farmer_id=order_data.farmer_id,
            name=order_data.name,
            description=order_data.description
        )

        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        logger.info(f"Order created successfully by user ID {user_id}: {new_order.name}")
        return new_order

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while creating order: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to create order due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while creating order: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}/orders/{order_id}", response_model=schemas.Order)
def read_order(
    user_id: int, 
    order_id: int, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to read order with ID {order_id}.")

    try:
        order = db.query(models.Order).filter(models.Order.id == order_id).first()

        if not order:
            logger.warning(f"Order with ID {order_id} not found.")
            raise HTTPException(status_code=404, detail="Order not found.")

        return order

    except Exception as e:
        logger.critical(f"Unexpected error while reading order with ID {order_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}/orders/", response_model=list[schemas.Order])
def read_orders_list(
    user_id: int, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to read all orders.")

    try:
        orders_list = db.query(models.Order).all()
        logger.info(f"Successfully retrieved {len(orders_list)} orders.")
        return orders_list

    except Exception as e:
        logger.critical(f"Unexpected error while reading all orders: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.patch("/api/v1/users/{user_id}/orders/{order_id}", response_model=schemas.Order)
def update_order(
    user_id: int, 
    order_id: int, 
    order_data: schemas.OrderUpdate, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to update order with ID {order_id}.")

    try:
        order = db.query(models.Order).filter(models.Order.id == order_id).first()

        if not order:
            logger.warning(f"Order with ID {order_id} not found.")
            raise HTTPException(status_code=404, detail="Order not found.")

        if order_data.name is not None:
            order.name = order_data.name
        if order_data.description is not None:
            order.description = order_data.description

        db.commit()
        db.refresh(order)

        logger.info(f"Order with ID {order_id} updated successfully by user ID {user_id}.")
        return order

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while updating order: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to update order due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while updating order with ID {order_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.delete("/api/v1/users/{user_id}/orders/{order_id}", response_model=dict)
def delete_order(
    user_id: int, 
    order_id: int, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to delete order with ID {order_id}.")

    try:
        order = db.query(models.Order).filter(models.Order.id == order_id).first()

        if not order:
            logger.warning(f"Order with ID {order_id} not found.")
            raise HTTPException(status_code=404, detail="Order not found.")

        db.delete(order)
        db.commit()

        logger.info(f"Order with ID {order_id} deleted successfully by user ID {user_id}.")
        return {"detail": "Order deleted successfully."}

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while deleting order with ID {order_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/api/v1/users/{user_id}/orders/{order_id}/order_items/", response_model=schemas.OrderItem)
def create_order_item(
    user_id: int, 
    order_id: int, 
    order_item_data: schemas.OrderItemCreate, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to create a new order item for order ID {order_id}.")

    current_user = db.query(models.User).filter_by(id=user_id).first()
    if not current_user:
        logger.error("User not found.")
        raise HTTPException(status_code=404, detail="User not found.")

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        logger.error(f"Order with ID {order_id} not found.")
        raise HTTPException(status_code=404, detail="Order not found.")

    farm_species = db.query(models.Farm_species).filter(models.Farm_species.id == order_item_data.farm_species_id).first()
    if not farm_species:
        logger.error(f"Farm species with ID {order_item_data.farm_species_id} not found.")
        raise HTTPException(status_code=404, detail="Farm species not found.")

    try:
        total_price = order_item_data.quantity * order_item_data.price

        new_order_item = models.Order_item(
            order_id=order_id,
            # farm_species_id=order_item_data.farm_species_id,
            quantity=order_item_data.quantity,
            price=order_item_data.price,
            total_price=total_price
        )

        db.add(new_order_item)
        db.commit()
        db.refresh(new_order_item)

        logger.info(f"Order item created successfully by user ID {user_id} for order ID {order_id}.")
        return new_order_item

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while creating order item: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to create order item due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while creating order item: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}/orders/{order_id}/order_items/{order_item_id}", response_model=schemas.OrderItem)
def read_order_item(
    user_id: int, 
    order_id: int, 
    order_item_id: int, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to read order item with ID {order_item_id} for order ID {order_id}.")

    try:
        order_item = db.query(models.Order_item).filter(
            models.Order_item.id == order_item_id,
            models.Order_item.order_id == order_id
        ).first()

        if not order_item:
            logger.warning(f"Order item with ID {order_item_id} not found for order ID {order_id}.")
            raise HTTPException(status_code=404, detail="Order item not found.")

        return order_item

    except Exception as e:
        logger.critical(f"Unexpected error while reading order item with ID {order_item_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}/orders/{order_id}/order_items/", response_model=list[schemas.OrderItem])
def read_order_items_list(
    user_id: int, 
    order_id: int, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to read all order items for order ID {order_id}.")

    try:
        order_items_list = db.query(models.Order_item).filter(
            models.Order_item.order_id == order_id
        ).all()
        logger.info(f"Successfully retrieved {len(order_items_list)} order items for order ID {order_id}.")
        return order_items_list

    except Exception as e:
        logger.critical(f"Unexpected error while reading all order items: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.patch("/api/v1/users/{user_id}/orders/{order_id}/order_items/{order_item_id}", response_model=schemas.OrderItem)
def update_order_item(
    user_id: int, 
    order_id: int, 
    order_item_id: int, 
    order_item_data: schemas.OrderItemUpdate, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to update order item with ID {order_item_id} for order ID {order_id}.")

    try:
        order_item = db.query(models.Order_item).filter(
            models.Order_item.id == order_item_id,
            models.Order_item.order_id == order_id
        ).first()

        if not order_item:
            logger.warning(f"Order item with ID {order_item_id} not found for order ID {order_id}.")
            raise HTTPException(status_code=404, detail="Order item not found.")

        if order_item_data.quantity is not None:
            order_item.quantity = order_item_data.quantity
        if order_item_data.price is not None:
            order_item.price = order_item_data.price

        if order_item_data.quantity is not None or order_item_data.price is not None:
            order_item.total_price = order_item.quantity * order_item.price

        db.commit()
        db.refresh(order_item)

        logger.info(f"Order item with ID {order_item_id} updated successfully by user ID {user_id}.")
        return order_item

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while updating order item: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to update order item due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while updating order item with ID {order_item_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.delete("/api/v1/users/{user_id}/orders/{order_id}/order_items/{order_item_id}", response_model=dict)
def delete_order_item(
    user_id: int, 
    order_id: int, 
    order_item_id: int, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to delete order item with ID {order_item_id} for order ID {order_id}.")

    try:
        order_item = db.query(models.Order_item).filter(
            models.Order_item.id == order_item_id,
            models.Order_item.order_id == order_id
        ).first()

        if not order_item:
            logger.warning(f"Order item with ID {order_item_id} not found for order ID {order_id}.")
            raise HTTPException(status_code=404, detail="Order item not found.")

        db.delete(order_item)
        db.commit()

        logger.info(f"Order item with ID {order_item_id} deleted successfully by user ID {user_id}.")
        return {"detail": "Order item deleted successfully."}

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while deleting order item with ID {order_item_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.post("/api/v1/users/{user_id}/orders/{order_id}/transactions/", response_model=schemas.Transaction)
def create_transaction(
    user_id: int, 
    order_id: int, 
    transaction_data: schemas.TransactionCreate, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to create a new transaction for order ID {order_id}.")

    current_user = db.query(models.User).filter_by(id=user_id).first()
    if not current_user:
        logger.error("User not found.")
        raise HTTPException(status_code=404, detail="User not found.")

    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.user_id == user_id
    ).first()
    if not order:
        logger.error(f"Order with ID {order_id} not found.")
        raise HTTPException(status_code=404, detail="Order not found.")

    farm = db.query(models.Farm).filter(models.Farm.id == transaction_data.farm_id).first()
    if not farm:
        logger.error(f"Farm with ID {transaction_data.farm_id} not found.")
        raise HTTPException(status_code=404, detail="Farm not found.")

    try:
        new_transaction = models.Transaction(
            buyer_id=user_id,
            order_id=order_id,
            # farm_id=transaction_data.farm_id,
            total_amount=transaction_data.total_amount,
            status=transaction_data.status,
            payment_method=transaction_data.payment_method
        )

        db.add(new_transaction)
        db.commit()
        db.refresh(new_transaction)

        logger.info(f"Transaction created successfully by user ID {user_id} for order ID {order_id}.")
        return new_transaction

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while creating transaction: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to create transaction due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while creating transaction: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}/orders/{order_id}/transactions/{transaction_id}", response_model=schemas.Transaction)
def read_transaction(
    user_id: int, 
    order_id: int, 
    transaction_id: int, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to read transaction with ID {transaction_id} for order ID {order_id}.")

    try:
        transaction = db.query(models.Transaction).filter(
            models.Transaction.id == transaction_id,
            models.Transaction.order_id == order_id
        ).first()

        if not transaction:
            logger.warning(f"Transaction with ID {transaction_id} not found for order ID {order_id}.")
            raise HTTPException(status_code=404, detail="Transaction not found.")

        return transaction

    except Exception as e:
        logger.critical(f"Unexpected error while reading transaction with ID {transaction_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/api/v1/users/{user_id}/orders/{order_id}/transactions/", response_model=list[schemas.Transaction])
def read_transactions_list(
    user_id: int, 
    order_id: int, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to read all transactions for order ID {order_id}.")

    try:
        transactions_list = db.query(models.Transaction).filter(
            models.Transaction.order_id == order_id
        ).all()
        logger.info(f"Successfully retrieved {len(transactions_list)} transactions for order ID {order_id}.")
        return transactions_list

    except Exception as e:
        logger.critical(f"Unexpected error while reading all transactions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.patch("/api/v1/users/{user_id}/orders/{order_id}/transactions/{transaction_id}", response_model=schemas.Transaction)
def update_transaction(
    user_id: int, 
    order_id: int, 
    transaction_id: int, 
    transaction_data: schemas.TransactionUpdate, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to update transaction with ID {transaction_id} for order ID {order_id}.")

    try:
        transaction = db.query(models.Transaction).filter(
            models.Transaction.id == transaction_id,
            models.Transaction.order_id == order_id
        ).first()

        if not transaction:
            logger.warning(f"Transaction with ID {transaction_id} not found for order ID {order_id}.")
            raise HTTPException(status_code=404, detail="Transaction not found.")

        if transaction_data.total_amount is not None:
            transaction.total_amount = transaction_data.total_amount
        if transaction_data.status is not None:
            transaction.status = transaction_data.status
        if transaction_data.payment_method is not None:
            transaction.payment_method = transaction_data.payment_method

        db.commit()
        db.refresh(transaction)

        logger.info(f"Transaction with ID {transaction_id} updated successfully by user ID {user_id}.")
        return transaction

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error while updating transaction: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to update transaction due to database constraint.")

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while updating transaction with ID {transaction_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.delete("/api/v1/users/{user_id}/orders/{order_id}/transactions/{transaction_id}", response_model=dict)
def delete_transaction(
    user_id: int, 
    order_id: int, 
    transaction_id: int, 
    db: Session = Depends(get_db)
):
    logger.info(f"User {user_id} requested to delete transaction with ID {transaction_id} for order ID {order_id}.")

    try:
        transaction = db.query(models.Transaction).filter(
            models.Transaction.id == transaction_id,
            models.Transaction.order_id == order_id
        ).first()

        if not transaction:
            logger.warning(f"Transaction with ID {transaction_id} not found for order ID {order_id}.")
            raise HTTPException(status_code=404, detail="Transaction not found.")

        db.delete(transaction)
        db.commit()

        logger.info(f"Transaction with ID {transaction_id} deleted successfully by user ID {user_id}.")
        return {"detail": "Transaction deleted successfully."}

    except Exception as e:
        db.rollback()
        logger.critical(f"Unexpected error while deleting transaction with ID {transaction_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")