class Obstacle:
    
    def __init__(self, x, y, width, height, speed, direction, color, obstacle_type, solid=False, deadly=False):
        
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.speed = speed
        self.direction = direction
        self.color = color
        self.obstacle_type = obstacle_type
        self.solid = solid
        self.deadly = deadly

    def update(self):
        self.x += self.speed * self.direction