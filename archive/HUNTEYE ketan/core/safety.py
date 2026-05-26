# Dev 3 - Safety Layer
# Har MAVLink command se pehle yeh check hota hai

class SafetyLayer:
    def __init__(self):
        # Yeh limits hain - inhe cross nahi karna
        self.MAX_VELOCITY = 5.0    # m/s
        self.MAX_ALTITUDE = 30.0   # meters
        self.GEOFENCE_RADIUS = 100.0  # meters
        
    def check_velocity(self, vx, vy, vz):
        # Speed zyada hai toh cap karo
        vx = max(-self.MAX_VELOCITY, min(self.MAX_VELOCITY, vx))
        vy = max(-self.MAX_VELOCITY, min(self.MAX_VELOCITY, vy))
        vz = max(-self.MAX_VELOCITY, min(self.MAX_VELOCITY, vz))
        return vx, vy, vz
    
    def check_altitude(self, current_altitude):
        # Drone zyada ucha gaya toh emergency
        if current_altitude > self.MAX_ALTITUDE:
            print("DANGER! Altitude limit cross ho gayi - Land karo!")
            return False
        return True
    
    def check_geofence(self, distance_from_home):
        # Drone zyada door gaya toh emergency
        if distance_from_home > self.GEOFENCE_RADIUS:
            print("DANGER! Geofence cross ho gayi - Wapas aao!")
            return False
        return True
    
    def check_emergency(self, system_mode):
        # Koi bhi emergency set kare toh land karo
        if system_mode == "emergency":
            print("EMERGENCY! Drone land kar raha hai!")
            return False
        return True
    
    def is_safe(self, vx, vy, vz, altitude, distance, system_mode):
        # Sab checks ek saath
        if not self.check_altitude(altitude):
            return False
        if not self.check_geofence(distance):
            return False
        if not self.check_emergency(system_mode):
            return False
        # Velocity cap karo
        vx, vy, vz = self.check_velocity(vx, vy, vz)
        print(f"SAFE ✓ → vx={vx}, vy={vy}, vz={vz}")
        return True


# TEST
if __name__ == "__main__":
    safety = SafetyLayer()
    
    print("=== Safety Layer Tests ===")
    
    # Test 1 - Sab safe hai
    print("\nTest 1 - Normal flight:")
    safety.is_safe(1.0, 1.0, 0.5, 15.0, 50.0, "hunting")
    
    # Test 2 - Altitude zyada hai
    print("\nTest 2 - Altitude zyada:")
    safety.is_safe(1.0, 1.0, 0.5, 35.0, 50.0, "hunting")
    
    # Test 3 - Geofence cross hua
    print("\nTest 3 - Geofence cross:")
    safety.is_safe(1.0, 1.0, 0.5, 15.0, 110.0, "hunting")
    
    # Test 4 - Emergency
    print("\nTest 4 - Emergency:")
    safety.is_safe(1.0, 1.0, 0.5, 15.0, 50.0, "emergency")
    
    # Test 5 - Speed zyada hai
    print("\nTest 5 - Speed cap:")
    safety.is_safe(10.0, 10.0, 10.0, 15.0, 50.0, "hunting")