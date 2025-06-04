from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import os
import asyncio
import json
import uuid
from datetime import datetime, timedelta
import random
import math
from geopy.distance import geodesic
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Traffic Management API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'traffic_management')

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Pydantic Models
class TrafficLight(BaseModel):
    id: str
    intersection_id: str
    direction: str  # north, south, east, west
    status: str  # red, yellow, green
    remaining_time: int
    priority_override: bool = False

class Intersection(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    traffic_lights: List[TrafficLight]
    emergency_priority: bool = False
    traffic_flow_rate: float = 0.0
    last_updated: datetime

class EmergencyVehicle(BaseModel):
    id: str
    type: str  # ambulance, fire_truck, police
    latitude: float
    longitude: float
    destination_lat: float
    destination_lon: float
    speed: float
    route: List[str]  # intersection IDs in route
    priority_level: int
    active: bool = True
    estimated_arrival: Optional[datetime] = None

class TrafficIncident(BaseModel):
    id: str
    type: str
    latitude: float
    longitude: float
    severity: int
    description: str
    emergency_vehicles: List[str]
    created_at: datetime
    resolved_at: Optional[datetime] = None

class PriorityRequest(BaseModel):
    vehicle_id: str
    intersection_id: str
    priority_level: int
    duration: int  # seconds

# Traffic Management Engine
class TrafficManager:
    def __init__(self):
        self.intersections: Dict[str, Intersection] = {}
        self.emergency_vehicles: Dict[str, EmergencyVehicle] = {}
        self.priority_queue: List[PriorityRequest] = []
        
    def calculate_priority_score(self, vehicle: EmergencyVehicle, intersection: Intersection) -> float:
        """Calculate priority score based on distance, vehicle type, and urgency"""
        distance = geodesic(
            (vehicle.latitude, vehicle.longitude),
            (intersection.latitude, intersection.longitude)
        ).kilometers
        
        # Priority multipliers
        type_multiplier = {
            'ambulance': 1.0,
            'fire_truck': 1.2,
            'police': 0.8
        }
        
        # Closer vehicles get higher priority, adjusted by type
        base_score = (1 / max(distance, 0.1)) * type_multiplier.get(vehicle.type, 1.0)
        priority_score = base_score * vehicle.priority_level
        
        return priority_score
    
    def optimize_traffic_flow(self, intersection_id: str):
        """Optimize traffic light timing based on current conditions"""
        if intersection_id not in self.intersections:
            return
            
        intersection = self.intersections[intersection_id]
        
        # Check for emergency vehicles in vicinity
        nearby_emergency = self.get_nearby_emergency_vehicles(intersection, radius=2.0)
        
        if nearby_emergency:
            # Emergency priority mode
            self.activate_emergency_mode(intersection_id, nearby_emergency[0])
        else:
            # Normal traffic optimization
            self.normal_traffic_optimization(intersection_id)
    
    def get_nearby_emergency_vehicles(self, intersection: Intersection, radius: float) -> List[EmergencyVehicle]:
        """Find emergency vehicles within radius (km) of intersection"""
        nearby = []
        for vehicle in self.emergency_vehicles.values():
            if not vehicle.active:
                continue
                
            distance = geodesic(
                (intersection.latitude, intersection.longitude),
                (vehicle.latitude, vehicle.longitude)
            ).kilometers
            
            if distance <= radius:
                nearby.append(vehicle)
        
        # Sort by priority score
        nearby.sort(key=lambda v: self.calculate_priority_score(v, intersection), reverse=True)
        return nearby
    
    def activate_emergency_mode(self, intersection_id: str, vehicle: EmergencyVehicle):
        """Activate emergency priority for intersection"""
        intersection = self.intersections[intersection_id]
        intersection.emergency_priority = True
        
        # Determine vehicle's approach direction and give green light
        approach_direction = self.get_approach_direction(vehicle, intersection)
        
        for light in intersection.traffic_lights:
            if light.direction == approach_direction:
                light.status = "green"
                light.remaining_time = 30  # Extended green time
                light.priority_override = True
            else:
                light.status = "red"
                light.remaining_time = 30
                light.priority_override = True
    
    def get_approach_direction(self, vehicle: EmergencyVehicle, intersection: Intersection) -> str:
        """Determine which direction the vehicle is approaching from"""
        # Simple logic based on relative position
        lat_diff = vehicle.latitude - intersection.latitude
        lon_diff = vehicle.longitude - intersection.longitude
        
        if abs(lat_diff) > abs(lon_diff):
            return "south" if lat_diff > 0 else "north"
        else:
            return "west" if lon_diff > 0 else "east"
    
    def normal_traffic_optimization(self, intersection_id: str):
        """Normal traffic flow optimization when no emergencies"""
        intersection = self.intersections[intersection_id]
        intersection.emergency_priority = False
        
        # Reset any priority overrides
        for light in intersection.traffic_lights:
            light.priority_override = False

traffic_manager = TrafficManager()

# Initialize sample data
async def initialize_sample_data():
    """Initialize the system with sample intersections and emergency vehicles"""
    
    # Sample intersections (major intersections in a city grid)
    sample_intersections = [
        {
            "id": "int_001",
            "name": "Main St & 1st Ave",
            "latitude": 40.7589,
            "longitude": -73.9851,
            "traffic_lights": [
                {"id": "tl_001_n", "intersection_id": "int_001", "direction": "north", "status": "green", "remaining_time": 25},
                {"id": "tl_001_s", "intersection_id": "int_001", "direction": "south", "status": "green", "remaining_time": 25},
                {"id": "tl_001_e", "intersection_id": "int_001", "direction": "east", "status": "red", "remaining_time": 25},
                {"id": "tl_001_w", "intersection_id": "int_001", "direction": "west", "status": "red", "remaining_time": 25}
            ],
            "emergency_priority": False,
            "traffic_flow_rate": 0.8,
            "last_updated": datetime.utcnow()
        },
        {
            "id": "int_002", 
            "name": "Main St & 2nd Ave",
            "latitude": 40.7595,
            "longitude": -73.9845,
            "traffic_lights": [
                {"id": "tl_002_n", "intersection_id": "int_002", "direction": "north", "status": "red", "remaining_time": 15},
                {"id": "tl_002_s", "intersection_id": "int_002", "direction": "south", "status": "red", "remaining_time": 15},
                {"id": "tl_002_e", "intersection_id": "int_002", "direction": "east", "status": "green", "remaining_time": 15},
                {"id": "tl_002_w", "intersection_id": "int_002", "direction": "west", "status": "green", "remaining_time": 15}
            ],
            "emergency_priority": False,
            "traffic_flow_rate": 0.6,
            "last_updated": datetime.utcnow()
        },
        {
            "id": "int_003",
            "name": "Broadway & 1st Ave", 
            "latitude": 40.7583,
            "longitude": -73.9857,
            "traffic_lights": [
                {"id": "tl_003_n", "intersection_id": "int_003", "direction": "north", "status": "yellow", "remaining_time": 3},
                {"id": "tl_003_s", "intersection_id": "int_003", "direction": "south", "status": "yellow", "remaining_time": 3},
                {"id": "tl_003_e", "intersection_id": "int_003", "direction": "east", "status": "red", "remaining_time": 28},
                {"id": "tl_003_w", "intersection_id": "int_003", "direction": "west", "status": "red", "remaining_time": 28}
            ],
            "emergency_priority": False,
            "traffic_flow_rate": 0.9,
            "last_updated": datetime.utcnow()
        },
        {
            "id": "int_004",
            "name": "Broadway & 2nd Ave",
            "latitude": 40.7589,
            "longitude": -73.9863,
            "traffic_lights": [
                {"id": "tl_004_n", "intersection_id": "int_004", "direction": "north", "status": "green", "remaining_time": 20},
                {"id": "tl_004_s", "intersection_id": "int_004", "direction": "south", "status": "green", "remaining_time": 20},
                {"id": "tl_004_e", "intersection_id": "int_004", "direction": "east", "status": "red", "remaining_time": 20},
                {"id": "tl_004_w", "intersection_id": "int_004", "direction": "west", "status": "red", "remaining_time": 20}
            ],
            "emergency_priority": False,
            "traffic_flow_rate": 0.7,
            "last_updated": datetime.utcnow()
        }
    ]
    
    # Load intersections into traffic manager
    for int_data in sample_intersections:
        intersection = Intersection(**int_data)
        traffic_manager.intersections[intersection.id] = intersection
    
    # Sample emergency vehicle
    emergency_vehicle = EmergencyVehicle(
        id="emv_001",
        type="ambulance",
        latitude=40.7575,
        longitude=-73.9840,
        destination_lat=40.7600,
        destination_lon=-73.9870,
        speed=45.0,
        route=["int_001", "int_002"],
        priority_level=9,
        active=True,
        estimated_arrival=datetime.utcnow() + timedelta(minutes=5)
    )
    
    traffic_manager.emergency_vehicles[emergency_vehicle.id] = emergency_vehicle

# API Endpoints
@app.on_event("startup")
async def startup_event():
    await initialize_sample_data()
    asyncio.create_task(traffic_simulation_loop())
    logger.info("Smart Traffic Management System started")

@app.get("/")
async def root():
    return {"message": "Smart Traffic Management System API", "version": "1.0.0"}

@app.get("/api/intersections")
async def get_intersections():
    """Get all intersections with current status"""
    return list(traffic_manager.intersections.values())

@app.get("/api/intersections/{intersection_id}")
async def get_intersection(intersection_id: str):
    """Get specific intersection details"""
    if intersection_id not in traffic_manager.intersections:
        raise HTTPException(status_code=404, detail="Intersection not found")
    return traffic_manager.intersections[intersection_id]

@app.get("/api/emergency-vehicles")
async def get_emergency_vehicles():
    """Get all active emergency vehicles"""
    return [v for v in traffic_manager.emergency_vehicles.values() if v.active]

@app.post("/api/emergency-vehicles")
async def create_emergency_vehicle(vehicle: EmergencyVehicle):
    """Create new emergency vehicle dispatch"""
    vehicle.id = str(uuid.uuid4())
    vehicle.active = True
    traffic_manager.emergency_vehicles[vehicle.id] = vehicle
    
    # Broadcast update
    await manager.broadcast(json.dumps({
        "type": "emergency_vehicle_created",
        "data": vehicle.dict()
    }))
    
    return vehicle

@app.post("/api/priority-override/{intersection_id}")
async def priority_override(intersection_id: str, priority_request: PriorityRequest):
    """Manual priority override for traffic controller"""
    if intersection_id not in traffic_manager.intersections:
        raise HTTPException(status_code=404, detail="Intersection not found")
    
    # Apply priority override
    intersection = traffic_manager.intersections[intersection_id]
    intersection.emergency_priority = True
    
    # Find vehicle and apply emergency mode
    if priority_request.vehicle_id in traffic_manager.emergency_vehicles:
        vehicle = traffic_manager.emergency_vehicles[priority_request.vehicle_id]
        traffic_manager.activate_emergency_mode(intersection_id, vehicle)
    
    await manager.broadcast(json.dumps({
        "type": "priority_override",
        "intersection_id": intersection_id,
        "data": intersection.dict()
    }))
    
    return {"status": "Priority override activated", "intersection_id": intersection_id}

@app.get("/api/traffic-status")
async def get_traffic_status():
    """Get overall traffic network status"""
    total_intersections = len(traffic_manager.intersections)
    emergency_active = len([v for v in traffic_manager.emergency_vehicles.values() if v.active])
    priority_intersections = len([i for i in traffic_manager.intersections.values() if i.emergency_priority])
    
    avg_flow_rate = sum([i.traffic_flow_rate for i in traffic_manager.intersections.values()]) / total_intersections
    
    return {
        "total_intersections": total_intersections,
        "emergency_vehicles_active": emergency_active,
        "priority_intersections": priority_intersections,
        "average_flow_rate": round(avg_flow_rate, 2),
        "system_status": "operational"
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now - can add specific handling later
            await manager.send_personal_message(f"Message received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background simulation task
async def traffic_simulation_loop():
    """Background task to simulate traffic light changes and vehicle movement"""
    while True:
        try:
            # Update traffic lights
            for intersection in traffic_manager.intersections.values():
                for light in intersection.traffic_lights:
                    if light.remaining_time > 0:
                        light.remaining_time -= 1
                    else:
                        # Change light status
                        if light.status == "green":
                            light.status = "yellow"
                            light.remaining_time = 3
                        elif light.status == "yellow":
                            light.status = "red"
                            light.remaining_time = 25
                        elif light.status == "red":
                            light.status = "green"
                            light.remaining_time = 25
                
                intersection.last_updated = datetime.utcnow()
                
                # Run traffic optimization
                traffic_manager.optimize_traffic_flow(intersection.id)
            
            # Update emergency vehicle positions
            for vehicle in traffic_manager.emergency_vehicles.values():
                if vehicle.active:
                    # Simple movement simulation
                    direction_lat = (vehicle.destination_lat - vehicle.latitude)
                    direction_lon = (vehicle.destination_lon - vehicle.longitude)
                    distance = math.sqrt(direction_lat**2 + direction_lon**2)
                    
                    if distance > 0.001:  # Still moving
                        # Move vehicle towards destination
                        speed_factor = 0.0001  # Adjust for realistic movement
                        vehicle.latitude += (direction_lat / distance) * speed_factor
                        vehicle.longitude += (direction_lon / distance) * speed_factor
                    else:
                        # Arrived at destination
                        vehicle.active = False
            
            # Broadcast updates
            await manager.broadcast(json.dumps({
                "type": "traffic_update",
                "timestamp": datetime.utcnow().isoformat(),
                "intersections": [i.dict() for i in traffic_manager.intersections.values()],
                "emergency_vehicles": [v.dict() for v in traffic_manager.emergency_vehicles.values() if v.active]
            }))
            
            await asyncio.sleep(1)  # Update every second
            
        except Exception as e:
            logger.error(f"Error in traffic simulation: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)