from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, create_engine, Column, Integer, Float, String, DateTime, ForeignKey, inspect, text, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from typing import List, Optional
import math
from collections import defaultdict

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    title = Column(String, index=True, unique=True)

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
    life_effort = Column(Float, default=0.0)

Base.metadata.create_all(engine)

# Adiciona coluna de vida útil de esforço caso o banco já exista sem essa coluna.
inspector = inspect(engine)
if "bike_maintenance" in inspector.get_table_names():
    columns = [col["name"] for col in inspector.get_columns("bike_maintenance")]
    if "life_effort" not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE bike_maintenance ADD COLUMN life_effort FLOAT DEFAULT 0.0"))

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
        from_attributes = True

class BikeComponentRequest(BaseModel):
    title: str

class BikeComponentResponse(BikeComponentRequest):
    id: int

    class Config:
        from_attributes = True

class BikeComponentReadResponse(BikeComponentResponse):
    average_component_life_effort: float = 0.0

class BikeMaintenanceRequest(BaseModel):
    bike_id: int
    bike_component_id: int
    maintenance_type: int
    maintenance_cost: float
    maintenance_start_date: Optional[datetime] = None

class BikeMaintenanceResponse(BikeMaintenanceRequest):
    id: int
    life_effort: float = 0.0

    class Config:
        from_attributes = True

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
    lastLocation = db.query(Location).filter_by(device_id=data.device_id).order_by(Location.id.desc()).first()
    if lastLocation:
        dist = haversine(lastLocation.latitude, lastLocation.longitude, data.latitude, data.longitude)
        if dist < 5:  # filtro simples para evitar pontos muito próximos
            return {"status": "ignored", "reason": "too close to last point"}

    bike_id = data.bike_id
    if bike_id is None and lastLocation is not None:
        bike_id = lastLocation.bike_id

    loc = Location(
        device_id=data.device_id,
        bike_id=bike_id,
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


@app.get("/components", response_model=List[BikeComponentReadResponse])
def list_components(db: Session = Depends(get_db)):
    components = db.query(BikeComponent).all()
    averages = get_component_life_effort_averages(db)

    return [
        {
            "id": component.id,
            "title": component.title,
            "average_component_life_effort": round(averages.get(component.id, 0.0), 2)
        }
        for component in components
    ]


@app.get("/components/{component_id}", response_model=BikeComponentReadResponse)
def get_component(component_id: int, db: Session = Depends(get_db)):
    component = db.query(BikeComponent).get(component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    return {
        "id": component.id,
        "title": component.title,
        "average_component_life_effort": round(get_average_component_life_effort(component.id, db), 2)
    }


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

    maintenance_start_date = data.maintenance_start_date or datetime.utcnow()
    life_effort = calculate_maintenance_life_effort(
        data.bike_id,
        data.bike_component_id,
        maintenance_start_date,
        db
    )

    maintenance = BikeMaintenance(
        bike_id=data.bike_id,
        bike_component_id=data.bike_component_id,
        maintenance_type=data.maintenance_type,
        maintenance_cost=data.maintenance_cost,
        maintenance_start_date=maintenance_start_date,
        life_effort=life_effort
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
    maintenance.life_effort = calculate_maintenance_life_effort(
        data.bike_id,
        data.bike_component_id,
        maintenance.maintenance_start_date,
        db,
        exclude_maintenance_id=maintenance_id
    )
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


def segment_trips(locations, min_time_gap_seconds=60):
    """
    Segmenta uma lista de localizações em viagens separadas.
    Se o intervalo entre dois pontos for > min_time_gap_seconds, considera como viagens diferentes.
    Retorna uma lista de listas, onde cada sublista é uma viagem contínua.
    """
    if not locations:
        return []
    
    trips = []
    current_trip = [locations[0]]
    
    for i in range(1, len(locations)):
        prev_location = locations[i - 1]
        curr_location = locations[i]
        
        time_gap = (curr_location.created_at - prev_location.created_at).total_seconds()
        
        if time_gap > min_time_gap_seconds:
            # Nova viagem
            trips.append(current_trip)
            current_trip = [curr_location]
        else:
            # Continua a viagem
            current_trip.append(curr_location)
    
    # Adiciona a última viagem
    if current_trip:
        trips.append(current_trip)
    
    return trips

@app.get("/devices")
def get_devices(db: Session = Depends(get_db)):
    stmt = select(Location.device_id).distinct()
    return db.execute(stmt).scalars().all()


def compute_effort_between(bike: int, since: Optional[datetime], until: Optional[datetime], db: Session):
    query = db.query(Location).filter_by(bike_id=bike)
    if since is not None:
        query = query.filter(Location.created_at >= since)
    if until is not None:
        query = query.filter(Location.created_at <= until)
    locations = query.order_by(Location.created_at.asc()).all()

    total_effort = 0.0
    trips = segment_trips(locations, min_time_gap_seconds=60)
    
    # Calcula esforço para cada viagem separadamente
    for trip in trips:
        for i in range(1, len(trip)):
            p1 = trip[i - 1]
            p2 = trip[i]

            dist = haversine(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
            dt = (p2.created_at - p1.created_at).total_seconds()
            if dt <= 0:
                continue

            speed = dist / dt
            alt_diff = (p2.altitude or 0) - (p1.altitude or 0)
            alt_gain = max(0, alt_diff)
            effort = dist * (1 + alt_gain * 0.01) * (1 + speed * 0.05)
            total_effort += effort

    return total_effort


def get_average_component_life_effort(component_id: int, db: Session):
    """
    Calcula a MÉDIA de vida útil de um componente considerando TODAS as bicicletas.
    Busca todas as manutenções desse componente em todas as bikes e retorna a média do life_effort.
    """
    average_life_effort = (
        db.query(func.avg(BikeMaintenance.life_effort))
        .filter(BikeMaintenance.bike_component_id == component_id)
        .scalar()
    )

    return average_life_effort or 0.0


def get_component_life_effort_averages(db: Session):
    averages = (
        db.query(
            BikeMaintenance.bike_component_id,
            func.avg(BikeMaintenance.life_effort).label("average_life_effort")
        )
        .group_by(BikeMaintenance.bike_component_id)
        .all()
    )

    return {
        component_id: average_life_effort or 0.0
        for component_id, average_life_effort in averages
    }


def calculate_maintenance_life_effort(
    bike_id: int,
    component_id: int,
    maintenance_date: datetime,
    db: Session,
    exclude_maintenance_id: Optional[int] = None
):
    """
    Calcula o esforço acumulado da bike para esse componente
    desde a última manutenção até a data da manutenção atual.
    """
    query = db.query(BikeMaintenance).filter(
        BikeMaintenance.bike_id == bike_id,
        BikeMaintenance.bike_component_id == component_id,
        BikeMaintenance.maintenance_start_date < maintenance_date
    )

    if exclude_maintenance_id is not None:
        query = query.filter(BikeMaintenance.id != exclude_maintenance_id)

    last_maintenance = (
        query
        .order_by(BikeMaintenance.maintenance_start_date.desc(), BikeMaintenance.id.desc())
        .first()
    )
    since_date = last_maintenance.maintenance_start_date if last_maintenance else None

    return compute_effort_between(bike_id, since_date, maintenance_date, db)


def get_alert_for_usage(used_effort: float, life_effort: float):
    if life_effort <= 0:
        return {
            "status": "unknown",
            "alert": "Sem configuração",
            "message": "A vida útil estimada do componente não foi configurada.",
            "usage_percent": None
        }

    usage_percent = round((used_effort / life_effort) * 100, 2)
    if usage_percent < 70:
        alert = "Verde"
        status = "observation"
        message = "Componente com menos de 70% da vida útil utilizada."
    elif usage_percent <= 90:
        alert = "Amarelo"
        status = "attention"
        message = "Componente entre 70% e 90% da vida útil. Agende inspeção em breve."
    else:
        alert = "Vermelho"
        status = "critical"
        message = "Componente com mais de 90% da vida útil. Ordem de serviço imediata recomendada."

    return {
        "status": status,
        "alert": alert,
        "message": message,
        "usage_percent": min(100.0, usage_percent)
    }


@app.get("/predictive-report/{bike_id}")
def get_predictive_report(bike_id: int, db: Session = Depends(get_db)):
    bike = db.query(Bike).get(bike_id)
    if not bike:
        raise HTTPException(status_code=404, detail="Bike not found")

    components = db.query(BikeComponent).all()
    if not components:
        return {
            "bike_id": bike_id,
            "components": [],
            "message": "Nenhum componente cadastrado para análise preditiva."
        }

    report = []
    for component in components:
        last_maintenance = (
            db.query(BikeMaintenance)
            .filter_by(bike_id=bike_id, bike_component_id=component.id)
            .order_by(BikeMaintenance.maintenance_start_date.desc())
            .first()
        )

        since_date = last_maintenance.maintenance_start_date if last_maintenance else None
        used_effort = compute_effort_between(bike_id, since_date, None, db)
        # Usa a MÉDIA de vida útil do componente entre TODAS as bikes
        average_life_effort = get_average_component_life_effort(component.id, db)
        alert_data = get_alert_for_usage(used_effort, average_life_effort)

        report.append({
            "component_id": component.id,
            "component_title": component.title,
            "last_maintenance_date": last_maintenance.maintenance_start_date if last_maintenance else None,
            "average_component_life_effort": round(average_life_effort, 2),
            "effort_since_last_maintenance": round(used_effort, 2),
            "alert": alert_data["alert"],
            "status": alert_data["status"],
            "usage_percent": alert_data["usage_percent"],
            "message": alert_data["message"]
        })

    return {
        "bike_id": bike_id,
        "components": report
    }


# ========================
# REPORT
# ========================
@app.get("/bike-report/{bike}")
def get_report(bike: int, db: Session = Depends(get_db)):
    locations = db.query(Location)\
        .filter_by(bike_id=bike)\
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
    
    # Segmenta as localizações em viagens separadas
    trips = segment_trips(locations, min_time_gap_seconds=60)

    for trip in trips:
        for i in range(1, len(trip)):
            p1 = trip[i - 1]
            p2 = trip[i]

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
        "bike_id": bike,
        "summary": {
            "total_distance_m": round(total_distance, 2),
            "avg_speed_m_s": round(avg_speed_total, 2),
            "total_effort": round(total_effort, 2)
        },
        "daily_history": history
    }
