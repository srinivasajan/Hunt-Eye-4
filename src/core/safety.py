class SafetyLayer:
    """Runtime safety gate for movement commands."""

    def __init__(self, max_velocity=5.0, max_altitude=30.0, geofence_radius=100.0):
        self.MAX_VELOCITY = float(max_velocity)
        self.MAX_ALTITUDE = float(max_altitude)
        self.GEOFENCE_RADIUS = float(geofence_radius)

    def check_velocity(self, vx, vy, vz):
        vx = max(-self.MAX_VELOCITY, min(self.MAX_VELOCITY, float(vx)))
        vy = max(-self.MAX_VELOCITY, min(self.MAX_VELOCITY, float(vy)))
        vz = max(-self.MAX_VELOCITY, min(self.MAX_VELOCITY, float(vz)))
        return vx, vy, vz

    def check_altitude(self, current_altitude):
        return float(current_altitude) <= self.MAX_ALTITUDE

    def check_geofence(self, distance_from_home):
        return float(distance_from_home) <= self.GEOFENCE_RADIUS

    def check_emergency(self, system_mode):
        return str(system_mode).upper() != "EMERGENCY"

    def is_safe(self, vx, vy, vz, altitude, distance, system_mode):
        _, _, _, safe, _ = self.enforce_command(
            vx, vy, vz, altitude, distance, system_mode
        )
        return safe

    def enforce_command(self, vx, vy, vz, altitude, distance, system_mode):
        if not self.check_altitude(altitude):
            return 0.0, 0.0, 0.0, False, "ALTITUDE_LIMIT"
        if not self.check_geofence(distance):
            return 0.0, 0.0, 0.0, False, "GEOFENCE_LIMIT"
        if not self.check_emergency(system_mode):
            return 0.0, 0.0, 0.0, False, "EMERGENCY"

        vx, vy, vz = self.check_velocity(vx, vy, vz)
        return vx, vy, vz, True, "OK"


if __name__ == "__main__":
    safety = SafetyLayer()
    print("=== Safety Layer Tests ===")
    print(safety.enforce_command(1.0, 1.0, 0.5, 15.0, 50.0, "TRACKING"))
    print(safety.enforce_command(10.0, 10.0, 10.0, 15.0, 50.0, "TRACKING"))
    print(safety.enforce_command(1.0, 1.0, 0.5, 35.0, 50.0, "TRACKING"))
