import pygame
import sys
import random
import os
import glob  # Moved glob import here

print("Current working directory:", os.getcwd())

# ----- Global Settings -----
WIDTH, HEIGHT = 900, 600
MENU_HEIGHT = 100
ROWS, COLS = 5, 9
CELL_WIDTH = WIDTH // COLS
CELL_HEIGHT = (HEIGHT - MENU_HEIGHT) // ROWS

# Colors
GRID_COLOR = (200, 200, 200)
MENU_BG = (100, 100, 100, 150)  # RGBA for transparency

# Global game over flag
game_over = False

# ----- Pygame Initialization -----
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("PvZ with Pygame")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 20)

# ----- Sprite Groups -----
all_sprites = pygame.sprite.Group()
plant_group = pygame.sprite.Group()
zombie_group = pygame.sprite.Group()
projectile_group = pygame.sprite.Group()

grid_occupancy = {}

# ----- Classes -----
class Plant(pygame.sprite.Sprite):
    def __init__(self, row, col, plant_type):
        super().__init__(plant_group, all_sprites)
        self.row = row
        self.col = col
        self.type = plant_type
        
        # Load animation frames
        self.frames = self.load_animation_frames()
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.center = (col * CELL_WIDTH + CELL_WIDTH//2, 
                           MENU_HEIGHT + row * CELL_HEIGHT + CELL_HEIGHT//2)
        self.animation_speed = 100
        self.last_frame_time = pygame.time.get_ticks()

        # Plant stats
        if plant_type == "pea_shooter":
            self.health = 100
            self.shoot_interval = 1000
            self.last_shot = pygame.time.get_ticks()
        elif plant_type == "sunflower":
            self.health = 80
        elif plant_type == "wall_nut":
            self.health = 300
        elif plant_type == "cherry_bomb":
            self.health = 1
            self.explode()
        elif plant_type == "snow_pea":
            self.health = 100
            self.shoot_interval = 1200
            self.last_shot = pygame.time.get_ticks()

    def load_animation_frames(self):
        frames = []
        folder = f"Assets/plant asset/{self.type}" 
        file_list = sorted(glob.glob(os.path.join(folder, f"{self.type}_*.png")))

        if not file_list:
            # If no animation frames, use the icon as fallback
            icon_path = f"Assets/plant_icons/{self.type}_icon.png"
            if os.path.exists(icon_path):
                fallback_image = pygame.image.load(icon_path).convert_alpha()
                fallback_image = pygame.transform.scale(fallback_image, (CELL_WIDTH-10, CELL_HEIGHT-10))
                return [fallback_image]
            else:
                # If even the icon is missing, use a colored rectangle
                fallback_image = pygame.Surface((CELL_WIDTH-10, CELL_HEIGHT-10))
                fallback_image.fill((255, 0, 255))  # Magenta color
                return [fallback_image]
                    
        for file in file_list:
            try:
                frame = pygame.image.load(file).convert_alpha()
                frame = pygame.transform.scale(frame, (CELL_WIDTH-10, CELL_HEIGHT-10))
                frames.append(frame)
            except pygame.error:
                print(f"Error loading frame: {file}")  
        return frames if frames else [pygame.Surface((CELL_WIDTH-10, CELL_HEIGHT-10))]

    def update(self):
        self.animate()
        if self.type in ["pea_shooter", "snow_pea"]:
            now = pygame.time.get_ticks()
            if now - self.last_shot >= self.shoot_interval:
                if any(zombie.row == self.row and zombie.rect.x > self.rect.x 
                      for zombie in zombie_group):
                    Projectile(self.row, self.rect.centerx, self.type)
                    self.last_shot = now

    def animate(self):
        now = pygame.time.get_ticks()
        if now - self.last_frame_time > self.animation_speed:
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.image = self.frames[self.frame_index]
            self.last_frame_time = now

    def explode(self):
        for zombie in zombie_group:
            if zombie.row == self.row and abs(zombie.rect.centerx - self.rect.centerx) < CELL_WIDTH*2:
                zombie.health -= 100
        self.kill()

class Zombie(pygame.sprite.Sprite):
    def __init__(self, row, zombie_type):
        super().__init__(zombie_group, all_sprites)
        self.row = row
        self.type = zombie_type

        # Stats
        stats = {
            "regular": {"health": 200, "speed": 50},
            "conehead": {"health": 250, "speed": 50},
            "buckethead": {"health": 300, "speed": 50},
            "flag": {"health": 180, "speed": 100},
        }
        self.health = stats[zombie_type]["health"]
        self.speed = stats[zombie_type]["speed"]
        
        # Load image
        self.image = pygame.image.load(
            f"Assets/zombies/{zombie_type}.png"
        ).convert_alpha()
        self.image = pygame.transform.scale(self.image, (CELL_WIDTH-10, CELL_HEIGHT-10))
        self.rect = self.image.get_rect()
        self.rect.center = (WIDTH + CELL_WIDTH//2, 
                           MENU_HEIGHT + row * CELL_HEIGHT + CELL_HEIGHT//2)
        self.attack_timer = pygame.time.get_ticks()

    def update(self):
        dt = clock.get_time() / 1000
        collided = pygame.sprite.spritecollide(self, plant_group, False)
        if collided:
            if pygame.time.get_ticks() - self.attack_timer >= 500:
                collided[0].health -= 20
                self.attack_timer = pygame.time.get_ticks()
        else:
            self.rect.x -= int(self.speed * dt)
        
        # Game-over check: if zombie passes x=100, trigger game over.
        if self.rect.right < 100:
            global game_over
            game_over = True
            self.kill()
            return
        
        if self.rect.right < 0 or self.health <= 0:
            self.kill()

class Projectile(pygame.sprite.Sprite):
    def __init__(self, row, x, plant_type):
        super().__init__(projectile_group, all_sprites)
        self.row = row
        self.plant_type = plant_type
        
        # Load image based on plant type
        self.image = pygame.image.load(
            f"Assets/projectiles/{plant_type}_projectile.png"
        ).convert_alpha()
        self.image = pygame.transform.scale(self.image, (20, 20))
        self.rect = self.image.get_rect(center=(x, MENU_HEIGHT + row * CELL_HEIGHT + CELL_HEIGHT // 2))
        
        # Projectile stats
        self.damage = 20 if plant_type == "pea_shooter" else 15
        self.speed = -200  # Move left

    def update(self):
        self.rect.x += self.speed * clock.get_time() / 1000
        if self.rect.right < 0:
            self.kill()
        hits = pygame.sprite.spritecollide(self, zombie_group, False)
        if hits:
            hits[0].health -= self.damage
            self.kill()

# ----- Helper Functions -----
def spawn_zombie():
    Zombie(random.randint(0, ROWS - 1), random.choice(
        ["regular", "conehead", "buckethead", "flag"]
    ))

def draw_grid():
    for row in range(ROWS):
        for col in range(COLS):
            rect = pygame.Rect(col * CELL_WIDTH, MENU_HEIGHT + row * CELL_HEIGHT, CELL_WIDTH, CELL_HEIGHT)
            pygame.draw.rect(screen, GRID_COLOR, rect, 1)

def draw_menu(selected_plant):
    # Semi-transparent overlay
    menu_surface = pygame.Surface((WIDTH, MENU_HEIGHT), pygame.SRCALPHA)
    menu_surface.fill(MENU_BG)
    screen.blit(menu_surface, (0, 0))
    
    # Text
    text = font.render("1:Pea 2:Sun 3:Wall 4:Cherry 5:Snow", True, (255, 255, 255))
    screen.blit(text, (10, 10))
    sel_text = font.render(f"Selected: {selected_plant.replace('_', ' ').title()}", True, (255, 255, 255))
    screen.blit(sel_text, (10, 40))
    
    # Plant icons
    for i, plant_type in enumerate(["pea_shooter", "sunflower", "wall_nut", "cherry_bomb", "snow_pea"]):
        try:
            icon = pygame.image.load(f"Assets/plant_icons/{plant_type}_icon.png")
            icon = pygame.transform.scale(icon, (40, 40))
            screen.blit(icon, (200 + i * 100, 20))
        except:
            pass

# ----- Main Game Loop -----
def main():
    # Setup
    base_path = os.path.dirname(os.path.abspath(__file__))
    background_path = os.path.join(base_path, "Assets", "backgrounds", "background.jpg")

# Construct the full path to the background image
    background_path = os.path.join(background_path)
    try:
        
        background = pygame.transform.scale(background, (WIDTH, HEIGHT))
    except Exception as e:
        print("Error loading background:", e)
        sys.exit()

    
    selected_plant = "pea_shooter"
    pygame.time.set_timer(pygame.USEREVENT + 1, 3000)  # Zombie spawn timer

    running = True
    while running:
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                keys = {
                    pygame.K_1: "pea_shooter",
                    pygame.K_2: "sunflower",
                    pygame.K_3: "wall_nut",
                    pygame.K_4: "cherry_bomb",
                    pygame.K_5: "snow_pea"
                }
                if event.key in keys:
                    selected_plant = keys[event.key]
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                if my > MENU_HEIGHT:
                    col = mx // CELL_WIDTH
                    row = (my - MENU_HEIGHT) // CELL_HEIGHT
                    if (row, col) not in grid_occupancy:
                        grid_occupancy[(row, col)] = Plant(row, col, selected_plant)
            if event.type == pygame.USEREVENT + 1:
                spawn_zombie()

        # Update
        all_sprites.update()

        # Draw
        screen.blit(background, (0, 0))
        draw_grid()
        draw_menu(selected_plant)
        all_sprites.draw(screen)
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
