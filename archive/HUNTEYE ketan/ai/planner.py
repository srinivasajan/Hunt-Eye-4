# Dev 3 - A* Path Planner
# Drone ko obstacles avoid karte hue raasta dhundhta hai

import numpy as np

class AStarPlanner:
    def __init__(self):
        # Cost map - Dev 2 banayega, abhi hum fake banate hain test ke liye
        # 0 = open air, 100 = obstacle
        self.cost_map = np.zeros((20, 20))
        
        # Kuch obstacles add karo test ke liye
        self.cost_map[5:8, 5:8] = 100    # building 1
        self.cost_map[12:15, 10:14] = 100 # building 2
        self.cost_map[3:6, 14:17] = 100   # building 3
    
    def heuristic(self, a, b):
        # Distance calculate karo - seedha line mein
        return np.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2)
    
    def find_path(self, start, goal):
        # A* algorithm - sabse safe raasta dhundho
        open_set = {start}
        came_from = {}
        
        g_score = {start: 0}
        f_score = {start: self.heuristic(start, goal)}
        
        # 8 directions mein move kar sakta hai
        directions = [
            (-1,0), (1,0), (0,-1), (0,1),   # upar, neeche, left, right
            (-1,-1), (-1,1), (1,-1), (1,1)   # diagonals
        ]
        
        while open_set:
            # Sabse kam cost wala node lo
            current = min(open_set, key=lambda x: f_score.get(x, float('inf')))
            
            # Goal pe pahunch gaye?
            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                path.reverse()
                return path
            
            open_set.remove(current)
            
            # 8 directions check karo
            for dx, dy in directions:
                neighbor = (current[0]+dx, current[1]+dy)
                
                # Map ke bahar hai?
                if not (0 <= neighbor[0] < 20 and 0 <= neighbor[1] < 20):
                    continue
                
                # Obstacle hai?
                if self.cost_map[neighbor[0], neighbor[1]] >= 90:
                    continue
                
                # Diagonal cost zyada hoti hai
                if dx != 0 and dy != 0:
                    move_cost = 1.414
                else:
                    move_cost = 1.0
                
                tentative_g = g_score[current] + move_cost
                
                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self.heuristic(neighbor, goal)
                    open_set.add(neighbor)
        
        return None  # Raasta nahi mila


# TEST
if __name__ == "__main__":
    print("=== A* Path Planner Test ===")
    
    planner = AStarPlanner()
    
    # Start aur Goal set karo
    start = (0, 0)   # drone yahan hai
    goal = (19, 19)  # target yahan hai
    
    print(f"\nStart: {start}")
    print(f"Goal: {goal}")
    print(f"\nRaasta dhundh raha hai...")
    
    path = planner.find_path(start, goal)
    
    if path:
        print(f"\nRaasta mila! {len(path)} steps mein pahunchega")
        print(f"\nPehle 5 steps:")
        for i, step in enumerate(path[:5]):
            print(f"  Step {i+1}: {step}")
        print(f"\nAakhri 5 steps:")
        for i, step in enumerate(path[-5:]):
            print(f"  Step {len(path)-4+i}: {step}")
    else:
        print("Raasta nahi mila!")
    
    # Map print karo
    print("\nCost Map (X=obstacle, .=open, S=start, G=goal):")
    for i in range(20):
        row = ""
        for j in range(20):
            if (i,j) == start:
                row += "S "
            elif (i,j) == goal:
                row += "G "
            elif (i,j) in path:
                row += "* "
            elif planner.cost_map[i,j] >= 90:
                row += "X "
            else:
                row += ". "
        print(row)