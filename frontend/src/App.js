import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import { AlertTriangle, Activity, MapPin, Clock, Zap, Users, BarChart3, Settings, Car, Truck, Shield } from 'lucide-react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [intersections, setIntersections] = useState([]);
  const [emergencyVehicles, setEmergencyVehicles] = useState([]);
  const [trafficStatus, setTrafficStatus] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  const [selectedIntersection, setSelectedIntersection] = useState(null);
  const [priorityMode, setPriorityMode] = useState(false);

  useEffect(() => {
    fetchInitialData();
    setupWebSocket();
  }, []);

  const fetchInitialData = async () => {
    try {
      const [intersectionsRes, vehiclesRes, statusRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/intersections`),
        fetch(`${BACKEND_URL}/api/emergency-vehicles`),
        fetch(`${BACKEND_URL}/api/traffic-status`)
      ]);

      setIntersections(await intersectionsRes.json());
      setEmergencyVehicles(await vehiclesRes.json());
      setTrafficStatus(await statusRes.json());
    } catch (error) {
      console.error('Error fetching initial data:', error);
    }
  };

  const setupWebSocket = () => {
    const ws = new WebSocket(`${BACKEND_URL.replace('http', 'ws')}/ws`);
    
    ws.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'traffic_update') {
          setIntersections(data.intersections);
          setEmergencyVehicles(data.emergency_vehicles);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  };

  const handlePriorityOverride = async (intersectionId, vehicleId) => {
    try {
      await fetch(`${BACKEND_URL}/api/priority-override/${intersectionId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          vehicle_id: vehicleId,
          intersection_id: intersectionId,
          priority_level: 9,
          duration: 60
        }),
      });
    } catch (error) {
      console.error('Error setting priority override:', error);
    }
  };

  const createEmergencyVehicle = async () => {
    const vehicle = {
      type: 'ambulance',
      latitude: 40.7575 + (Math.random() - 0.5) * 0.01,
      longitude: -73.9840 + (Math.random() - 0.5) * 0.01,
      destination_lat: 40.7600 + (Math.random() - 0.5) * 0.01,
      destination_lon: -73.9870 + (Math.random() - 0.5) * 0.01,
      speed: 45.0,
      route: ['int_001', 'int_002'],
      priority_level: 9
    };

    try {
      await fetch(`${BACKEND_URL}/api/emergency-vehicles`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(vehicle),
      });
    } catch (error) {
      console.error('Error creating emergency vehicle:', error);
    }
  };

  const getVehicleIcon = (type) => {
    switch (type) {
      case 'ambulance': return <Car className="w-4 h-4" />;
      case 'fire_truck': return <Truck className="w-4 h-4" />;
      case 'police': return <Shield className="w-4 h-4" />;
      default: return <Car className="w-4 h-4" />;
    }
  };

  const getTrafficLightColor = (status) => {
    switch (status) {
      case 'green': return 'bg-green-500';
      case 'yellow': return 'bg-yellow-500';
      case 'red': return 'bg-red-500';
      default: return 'bg-gray-400';
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Activity className="w-8 h-8 text-blue-400" />
            <h1 className="text-2xl font-bold">Smart Traffic Management</h1>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
              <span className="text-sm text-gray-400">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <button
              onClick={createEmergencyVehicle}
              className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg flex items-center space-x-2"
            >
              <AlertTriangle className="w-4 h-4" />
              <span>Dispatch Emergency</span>
            </button>
            <button
              onClick={() => setPriorityMode(!priorityMode)}
              className={`px-4 py-2 rounded-lg flex items-center space-x-2 ${
                priorityMode ? 'bg-orange-600 hover:bg-orange-700' : 'bg-gray-600 hover:bg-gray-700'
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Priority Mode</span>
            </button>
          </div>
        </div>
      </header>

      <div className="flex h-screen">
        {/* Main Traffic Grid */}
        <div className="flex-1 p-6">
          <div className="bg-gray-800 rounded-lg p-6 h-full">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Traffic Network Status</h2>
              <div className="flex items-center space-x-4 text-sm">
                <div className="flex items-center space-x-2">
                  <BarChart3 className="w-4 h-4 text-blue-400" />
                  <span>Flow Rate: {trafficStatus.average_flow_rate || 0}%</span>
                </div>
                <div className="flex items-center space-x-2">
                  <MapPin className="w-4 h-4 text-green-400" />
                  <span>{trafficStatus.total_intersections || 0} Intersections</span>
                </div>
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                  <span>{trafficStatus.emergency_vehicles_active || 0} Emergency Vehicles</span>
                </div>
              </div>
            </div>

            {/* Traffic Grid Visualization */}
            <div className="grid grid-cols-2 gap-8 h-full">
              {intersections.map((intersection) => (
                <div
                  key={intersection.id}
                  className={`bg-gray-700 rounded-lg p-4 border-2 cursor-pointer transition-all ${
                    intersection.emergency_priority
                      ? 'border-red-500 bg-red-900/30'
                      : selectedIntersection?.id === intersection.id
                      ? 'border-blue-500'
                      : 'border-gray-600 hover:border-gray-500'
                  }`}
                  onClick={() => setSelectedIntersection(intersection)}
                >
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold">{intersection.name}</h3>
                    {intersection.emergency_priority && (
                      <div className="flex items-center space-x-1 text-red-400">
                        <Zap className="w-4 h-4" />
                        <span className="text-xs">PRIORITY</span>
                      </div>
                    )}
                  </div>

                  {/* Traffic Light Grid */}
                  <div className="relative">
                    <div className="grid grid-cols-3 gap-2 h-32">
                      {/* North */}
                      <div className="col-start-2 flex flex-col items-center justify-start">
                        {intersection.traffic_lights
                          .filter(light => light.direction === 'north')
                          .map(light => (
                            <div key={light.id} className="flex flex-col items-center">
                              <div className={`w-3 h-3 rounded-full ${getTrafficLightColor(light.status)} mb-1`}></div>
                              <span className="text-xs text-gray-400">{light.remaining_time}s</span>
                            </div>
                          ))}
                      </div>

                      {/* West */}
                      <div className="col-start-1 row-start-2 flex items-center justify-start">
                        {intersection.traffic_lights
                          .filter(light => light.direction === 'west')
                          .map(light => (
                            <div key={light.id} className="flex items-center">
                              <div className={`w-3 h-3 rounded-full ${getTrafficLightColor(light.status)} mr-1`}></div>
                              <span className="text-xs text-gray-400">{light.remaining_time}s</span>
                            </div>
                          ))}
                      </div>

                      {/* Center intersection */}
                      <div className="col-start-2 row-start-2 flex items-center justify-center">
                        <div className="w-8 h-8 bg-gray-600 rounded border-2 border-yellow-400"></div>
                      </div>

                      {/* East */}
                      <div className="col-start-3 row-start-2 flex items-center justify-end">
                        {intersection.traffic_lights
                          .filter(light => light.direction === 'east')
                          .map(light => (
                            <div key={light.id} className="flex items-center">
                              <span className="text-xs text-gray-400 mr-1">{light.remaining_time}s</span>
                              <div className={`w-3 h-3 rounded-full ${getTrafficLightColor(light.status)}`}></div>
                            </div>
                          ))}
                      </div>

                      {/* South */}
                      <div className="col-start-2 row-start-3 flex flex-col items-center justify-end">
                        {intersection.traffic_lights
                          .filter(light => light.direction === 'south')
                          .map(light => (
                            <div key={light.id} className="flex flex-col items-center">
                              <span className="text-xs text-gray-400 mb-1">{light.remaining_time}s</span>
                              <div className={`w-3 h-3 rounded-full ${getTrafficLightColor(light.status)}`}></div>
                            </div>
                          ))}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between text-sm text-gray-400">
                    <span>Flow: {(intersection.traffic_flow_rate * 100).toFixed(0)}%</span>
                    {priorityMode && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          const nearbyVehicle = emergencyVehicles[0];
                          if (nearbyVehicle) {
                            handlePriorityOverride(intersection.id, nearbyVehicle.id);
                          }
                        }}
                        className="bg-orange-600 hover:bg-orange-700 px-2 py-1 rounded text-xs"
                      >
                        Override
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Emergency Vehicles Panel */}
        <div className="w-80 bg-gray-800 border-l border-gray-700 p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <span>Emergency Vehicles</span>
          </h2>

          <div className="space-y-4">
            {emergencyVehicles.map((vehicle) => (
              <div
                key={vehicle.id}
                className="bg-gray-700 rounded-lg p-4 border border-gray-600"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <div className="text-red-400">
                      {getVehicleIcon(vehicle.type)}
                    </div>
                    <span className="font-medium capitalize">{vehicle.type}</span>
                  </div>
                  <div className="flex items-center space-x-1 text-orange-400">
                    <Zap className="w-3 h-3" />
                    <span className="text-xs">P{vehicle.priority_level}</span>
                  </div>
                </div>

                <div className="space-y-2 text-sm text-gray-400">
                  <div className="flex items-center space-x-2">
                    <MapPin className="w-3 h-3" />
                    <span>
                      {vehicle.latitude.toFixed(4)}, {vehicle.longitude.toFixed(4)}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Clock className="w-3 h-3" />
                    <span>Speed: {vehicle.speed} mph</span>
                  </div>
                  <div className="text-xs">
                    Route: {vehicle.route.join(' → ')}
                  </div>
                </div>

                <div className="mt-3 flex space-x-2">
                  <button
                    onClick={() => {
                      const nearbyIntersection = intersections[0];
                      if (nearbyIntersection) {
                        handlePriorityOverride(nearbyIntersection.id, vehicle.id);
                      }
                    }}
                    className="flex-1 bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-xs"
                  >
                    Priority Clear
                  </button>
                  <button className="flex-1 bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-xs">
                    Track Route
                  </button>
                </div>
              </div>
            ))}

            {emergencyVehicles.length === 0 && (
              <div className="text-center text-gray-500 py-8">
                <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No active emergency vehicles</p>
              </div>
            )}
          </div>

          {/* System Status */}
          <div className="mt-8 bg-gray-700 rounded-lg p-4">
            <h3 className="font-semibold mb-3 flex items-center space-x-2">
              <Activity className="w-4 h-4 text-green-400" />
              <span>System Status</span>
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Total Intersections:</span>
                <span>{trafficStatus.total_intersections || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Priority Active:</span>
                <span className="text-orange-400">{trafficStatus.priority_intersections || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Emergency Vehicles:</span>
                <span className="text-red-400">{trafficStatus.emergency_vehicles_active || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">System Status:</span>
                <span className="text-green-400 capitalize">{trafficStatus.system_status || 'offline'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;