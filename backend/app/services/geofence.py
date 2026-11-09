import math

from fastapi import HTTPException

from app.config import settings


def office_distance_meters(latitude: float, longitude: float) -> float:
    radius = 6_371_000
    lat1, lat2 = math.radians(settings.office_latitude), math.radians(latitude)
    delta_lat = math.radians(latitude - settings.office_latitude)
    delta_lon = math.radians(longitude - settings.office_longitude)
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(min(1.0, value)))


def validate_gps_reading(latitude: float | None, longitude: float | None, accuracy_meters: float | None) -> float:
    if latitude is None or longitude is None or accuracy_meters is None:
        raise HTTPException(status_code=422, detail="Fresh GPS location is required for attendance")
    if not all(math.isfinite(value) for value in (latitude, longitude, accuracy_meters)):
        raise HTTPException(status_code=422, detail="GPS coordinates and accuracy must be finite numbers")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise HTTPException(status_code=422, detail="GPS coordinates are outside valid ranges")
    if accuracy_meters <= 0:
        raise HTTPException(status_code=422, detail="GPS accuracy must be positive")
    if accuracy_meters > settings.max_gps_accuracy_meters:
        raise HTTPException(status_code=422, detail=f"GPS accuracy must be {settings.max_gps_accuracy_meters:g} metres or better")
    distance = office_distance_meters(latitude, longitude)
    return distance


def validate_attendance_location(latitude: float | None, longitude: float | None, accuracy_meters: float | None) -> float:
    distance = validate_gps_reading(latitude, longitude, accuracy_meters)
    if distance > settings.office_geofence_radius_meters:
        raise HTTPException(status_code=403, detail=f"You are approximately {distance:.0f} metres from the office; attendance is allowed within {settings.office_geofence_radius_meters:g} metres")
    return distance
