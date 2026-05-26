# Dev 3 - MAVLink Interface + PID Controller
# Yeh file drone ko move karti hai

class PIDController:
    def __init__(self):
        # Yeh 3 numbers tune karne padte hain
        self.Kp = 0.002    # Main correction strength
        self.Ki = 0.0001   # Drift hatata hai
        self.Kd = 0.001    # Overshoot rokta hai
        
        self.integral_x = 0
        self.integral_y = 0
        self.prev_error_x = 0
        self.prev_error_y = 0
    
    def calculate(self, target_cx, target_cy, frame_cx=640, frame_cy=360):
        # Target kitna door hai center se
        error_x = target_cx - frame_cx
        error_y = target_cy - frame_cy
        
        # PID calculation
        self.integral_x += error_x
        self.integral_y += error_y
        
        vx = (self.Kp * error_x + 
              self.Ki * self.integral_x + 
              self.Kd * (error_x - self.prev_error_x))
        
        vy = (self.Kp * error_y + 
              self.Ki * self.integral_y + 
              self.Kd * (error_y - self.prev_error_y))
        
        # Speed cap - max 2 m/s
        vx = max(-2.0, min(2.0, vx))
        vy = max(-2.0, min(2.0, vy))
        
        self.prev_error_x = error_x
        self.prev_error_y = error_y
        
        return vx, vy


# TEST - Yeh chalao dekho kaam karta hai ya nahi
if __name__ == "__main__":
    pid = PIDController()
    
    # Target daayein hai (800, 360), center hai (640, 360)
    vx, vy = pid.calculate(800, 360)
    print(f"Target daayein hai → Drone daayein jayega: vx={vx:.4f}")
    
    # Target neeche hai (640, 500)
    vx, vy = pid.calculate(640, 500)
    print(f"Target neeche hai → Drone neeche jayega: vy={vy:.4f}")
    
    # Target center mein hai (640, 360)
    vx, vy = pid.calculate(640, 360)
    print(f"Target center mein hai → Drone ruke: vx={vx:.4f}, vy={vy:.4f}")