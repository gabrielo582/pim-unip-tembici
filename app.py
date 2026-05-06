from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from typing import List, Optional
import math
from collections import defaultdict

app = FastAPI()

# SQLite fix para FastAPI
engine = create_engine(
    "sqlite:///tracker.db",
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ========================
# DATABASE MODEL
# ========================
class Location(Base):
    __tablename__ = "location_point"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    bike_id = Column(Integer, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    accuracy = Column(Float)
    altitude = Column(Float)
    altitude_accuracy = Column(Float)
    heading = Column(Float)
    speed = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class Bike(Base):
    __tablename__ = "bikes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)

class BikeComponent(Base):
    __tablename__ = "bike_components"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)

class BikeMaintenance(Base):
    __tablename__ = "bike_maintenance"

    id = Column(Integer, primary_key=True, index=True)
    bike_id = Column(Integer, ForeignKey("bikes.id"), nullable=False, index=True)
    bike_component_id = Column(Integer, ForeignKey("bike_components.id"), nullable=False, index=True)
    maintenance_type = Column(Integer)
    maintenance_cost = Column(Float)
    maintenance_start_date = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# ========================
# SCHEMA
# ========================
class LocationRequest(BaseModel):
    device_id: str
    bike_id: Optional[int] = None
    latitude: float
    longitude: float
    accuracy: float
    altitude: float
    altitude_accuracy: float
    heading: float
    speed: float

class BikeRequest(BaseModel):
    title: str

class BikeResponse(BikeRequest):
    id: int

    class Config:
        orm_mode = True

class BikeComponentRequest(BaseModel):
    title: str

class BikeComponentResponse(BikeComponentRequest):
    id: int

    class Config:
        orm_mode = True

class BikeMaintenanceRequest(BaseModel):
    bike_id: int
    bike_component_id: int
    maintenance_type: int
    maintenance_cost: float
    maintenance_start_date: Optional[datetime] = None

class BikeMaintenanceResponse(BikeMaintenanceRequest):
    id: int

    class Config:
        orm_mode = True

# ========================
# DEPENDENCY (boa prática)
# ========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========================
# ENDPOINTS
# ========================

@app.post("/location")
def receive_location(data: LocationRequest, db: Session = Depends(get_db)):
    loc = Location(
        device_id=data.device_id,
        bike_id=data.bike_id,
        latitude=data.latitude,
        longitude=data.longitude,
        accuracy=data.accuracy,
        altitude=data.altitude,
        altitude_accuracy=data.altitude_accuracy,
        heading=data.heading,
        speed=data.speed
    )

    db.add(loc)
    db.commit()
    db.refresh(loc)

    return {"status": "ok", "id": loc.id}


@app.get("/locations/{device_id}")
def get_locations(device_id: str, db: Session = Depends(get_db)):
    locations = db.query(Location).filter_by(device_id=device_id).all()

    return [
        {
            "lat": loc.latitude,
            "lng": loc.longitude,
            "speed": loc.speed,
            "created_at": loc.created_at
        }
        for loc in locations
    ]


@app.post("/bikes", response_model=BikeResponse)
def create_bike(data: BikeRequest, db: Session = Depends(get_db)):
    bike = Bike(title=data.title)
    db.add(bike)
    db.commit()
    db.refresh(bike)
    return bike


@app.get("/bikes", response_model=List[BikeResponse])
def list_bikes(db: Session = Depends(get_db)):
    return db.query(Bike).all()


@app.get("/bikes/{bike_id}", response_model=BikeResponse)
def get_bike(bike_id: int, db: Session = Depends(get_db)):
    bike = db.query(Bike).get(bike_id)
    if not bike:
        raise HTTPException(status_code=404, detail="Bike not found")
    return bike


@app.put("/bikes/{bike_id}", response_model=BikeResponse)
def update_bike(bike_id: int, data: BikeRequest, db: Session = Depends(get_db)):
    bike = db.query(Bike).get(bike_id)
    if not bike:
        raise HTTPException(status_code=404, detail="Bike not found")
    bike.title = data.title
    db.commit()
    db.refresh(bike)
    return bike


@app.delete("/bikes/{bike_id}")
def delete_bike(bike_id: int, db: Session = Depends(get_db)):
    bike = db.query(Bike).get(bike_id)
    if not bike:
        raise HTTPException(status_code=404, detail="Bike not found")
    db.delete(bike)
    db.commit()
    return {"status": "deleted"}


@app.post("/components", response_model=BikeComponentResponse)
def create_component(data: BikeComponentRequest, db: Session = Depends(get_db)):
    component = BikeComponent(title=data.title)
    db.add(component)
    db.commit()
    db.refresh(component)
    return component


@app.get("/components", response_model=List[BikeComponentResponse])
def list_components(db: Session = Depends(get_db)):
    return db.query(BikeComponent).all()


@app.get("/components/{component_id}", response_model=BikeComponentResponse)
def get_component(component_id: int, db: Session = Depends(get_db)):
    component = db.query(BikeComponent).get(component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    return component


@app.put("/components/{component_id}", response_model=BikeComponentResponse)
def update_component(component_id: int, data: BikeComponentRequest, db: Session = Depends(get_db)):
    component = db.query(BikeComponent).get(component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    component.title = data.title
    db.commit()
    db.refresh(component)
    return component


@app.delete("/components/{component_id}")
def delete_component(component_id: int, db: Session = Depends(get_db)):
    component = db.query(BikeComponent).get(component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    db.delete(component)
    db.commit()
    return {"status": "deleted"}


@app.post("/maintenances", response_model=BikeMaintenanceResponse)
def create_maintenance(data: BikeMaintenanceRequest, db: Session = Depends(get_db)):
    if not db.query(Bike).get(data.bike_id):
        raise HTTPException(status_code=404, detail="Bike not found")
    if not db.query(BikeComponent).get(data.bike_component_id):
        raise HTTPException(status_code=404, detail="Component not found")

    maintenance = BikeMaintenance(
        bike_id=data.bike_id,
        bike_component_id=data.bike_component_id,
        maintenance_type=data.maintenance_type,
        maintenance_cost=data.maintenance_cost,
        maintenance_start_date=data.maintenance_start_date or datetime.utcnow()
    )

    db.add(maintenance)
    db.commit()
    db.refresh(maintenance)
    return maintenance


@app.get("/maintenances", response_model=List[BikeMaintenanceResponse])
def list_maintenances(bike_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(BikeMaintenance)
    if bike_id is not None:
        query = query.filter_by(bike_id=bike_id)
    return query.all()


@app.get("/maintenances/{maintenance_id}", response_model=BikeMaintenanceResponse)
def get_maintenance(maintenance_id: int, db: Session = Depends(get_db)):
    maintenance = db.query(BikeMaintenance).get(maintenance_id)
    if not maintenance:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    return maintenance


@app.put("/maintenances/{maintenance_id}", response_model=BikeMaintenanceResponse)
def update_maintenance(maintenance_id: int, data: BikeMaintenanceRequest, db: Session = Depends(get_db)):
    maintenance = db.query(BikeMaintenance).get(maintenance_id)
    if not maintenance:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    if not db.query(Bike).get(data.bike_id):
        raise HTTPException(status_code=404, detail="Bike not found")
    if not db.query(BikeComponent).get(data.bike_component_id):
        raise HTTPException(status_code=404, detail="Component not found")

    maintenance.bike_id = data.bike_id
    maintenance.bike_component_id = data.bike_component_id
    maintenance.maintenance_type = data.maintenance_type
    maintenance.maintenance_cost = data.maintenance_cost
    maintenance.maintenance_start_date = data.maintenance_start_date or maintenance.maintenance_start_date
    db.commit()
    db.refresh(maintenance)
    return maintenance


@app.delete("/maintenances/{maintenance_id}")
def delete_maintenance(maintenance_id: int, db: Session = Depends(get_db)):
    maintenance = db.query(BikeMaintenance).get(maintenance_id)
    if not maintenance:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    db.delete(maintenance)
    db.commit()
    return {"status": "deleted"}


# ========================
# HAVERSINE
# ========================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # metros

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ========================
# REPORT
# ========================
@app.get("/device-report/{device_id}")
def get_report(device_id: str, db: Session = Depends(get_db)):
    locations = db.query(Location)\
        .filter_by(device_id=device_id)\
        .order_by(Location.created_at.asc())\
        .all()

    if not locations:
        return {"error": "no data"}

    daily = defaultdict(lambda: {
        "distance": 0,
        "time": 0,
        "alt_gain": 0,
        "effort": 0
    })

    total_distance = 0
    total_effort = 0

    for i in range(1, len(locations)):
        p1 = locations[i - 1]
        p2 = locations[i]

        # Distância
        dist = haversine(p1.latitude, p1.longitude, p2.latitude, p2.longitude)

        # Tempo (segundos)
        dt = (p2.created_at - p1.created_at).total_seconds()
        if dt <= 0:
            continue

        # Velocidade média (m/s)
        speed = dist / dt

        # Ganho de altitude (só subida)
        alt_diff = (p2.altitude or 0) - (p1.altitude or 0)
        alt_gain = max(0, alt_diff)

        # Esforço (modelo simples)
        effort = dist * (1 + alt_gain * 0.01) * (1 + speed * 0.05)

        day = p2.created_at.date().isoformat()

        daily[day]["distance"] += dist
        daily[day]["time"] += dt
        daily[day]["alt_gain"] += alt_gain
        daily[day]["effort"] += effort

        total_distance += dist
        total_effort += effort

    # Monta resposta
    history = []

    for day, data in sorted(daily.items()):
        avg_speed = data["distance"] / data["time"] if data["time"] > 0 else 0

        history.append({
            "date": day,
            "distance_m": round(data["distance"], 2),
            "avg_speed_m_s": round(avg_speed, 2),
            "altitude_gain_m": round(data["alt_gain"], 2),
            "effort": round(data["effort"], 2)
        })

    total_time = sum(d["time"] for d in daily.values())
    avg_speed_total = total_distance / total_time if total_time > 0 else 0

    return {
        "device_id": device_id,
        "summary": {
            "total_distance_m": round(total_distance, 2),
            "avg_speed_m_s": round(avg_speed_total, 2),
            "total_effort": round(total_effort, 2)
        },
        "daily_history": history
    }