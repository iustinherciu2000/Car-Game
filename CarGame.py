import pygame
import time
import math
from utils import scale_image, blit_rotate_center, blit_text_center
pygame.font.init()

TURF = scale_image(pygame.image.load('imgs/grass.jpg'), 2.5)  # background grass image
RACE_TRACK = scale_image(pygame.image.load('imgs/track.png'), 0.9)  # main race track image

TRACK_EDGE = scale_image(pygame.image.load('imgs/track-border.png'), 0.9)  # track boundary image
TRACK_EDGE_MASK = pygame.mask.from_surface(TRACK_EDGE)  # mask for precise edge collisions

FINISH_LINE = pygame.image.load('imgs/finish.png')  # finish line image
FINISH_LINE_MASK = pygame.mask.from_surface(FINISH_LINE)  # mask for finish line collision
FINISH_POS = (130, 250)  # where to place the finish line

PLAYER_CAR_IMAGE = scale_image(pygame.image.load('imgs/red-car.png'), 0.55)  # player car sprite
AI_CAR_IMAGE = scale_image(pygame.image.load('imgs/green-car.png'), 0.55)  # AI car sprite

SCREEN_WIDTH, SCREEN_HEIGHT = (RACE_TRACK.get_width(), RACE_TRACK.get_height())  # window size based on track image
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))  # create the game window

pygame.display.set_caption('Racing Game!')
UI_FONT = pygame.font.SysFont('comicsans', 44)  # font used for on-screen text

FRAME_RATE = 60  # target FPS
WAYPOINTS = [(175, 119), (110, 70), (56, 133), (70, 481), (318, 731), (404, 680), (418, 521), (507, 475), (600, 551), (613, 715), (736, 713), (734, 399), (611, 357), (409, 343), (433, 257), (697, 258), (738, 123), (581, 71), (303, 78), (275, 377), (176, 388), (178, 260)]

# Tracks stage/level state and timers
class GameInfo:
    LEVELS = 10

    def __init__(self, stage=1):
        self.stage = stage
        self.in_progress = False
        self.stage_start_time = 0

    # Adjust AI per level or progress state
    def advance_level(self):
        self.stage += 1
        self.in_progress = False

    # Reset car or game state to defaults
    def reset_state(self):
        self.stage = 1
        self.in_progress = False
        self.stage_start_time = 0

    def is_game_finished(self):
        return self.stage > self.LEVELS

    def start_stage(self):
        self.in_progress = True
        self.stage_start_time = time.time()

    def get_stage_time(self):
        if not self.in_progress:
            return 0
        return round(time.time() - self.stage_start_time)

# Base car class: position, rotation, movement, collisions
class AbstractCar:
    def __init__(self, max_speed, turn_speed):
        self.sprite = self.IMAGE
        self.max_speed = max_speed
        self.speed = 0
        self.turn_speed = turn_speed
        self.heading = 0
        self.x_pos, self.y_pos = self.START_POSITION
        self.acceleration = 0.1

    # Rotate the car left/right based on turn_speed
    def rotate(self, left=False, right=False):
        if left:
            self.heading += self.turn_speed
        elif right:
            self.heading -= self.turn_speed

    # Draw the car sprite at its current position/heading
    def render(self, screen):
        blit_rotate_center(screen, self.sprite, (self.x_pos, self.y_pos), self.heading)

    # Increase speed in the current heading
    def accelerate_forward(self):
        self.speed = min(self.speed + self.acceleration, self.max_speed)
        self.update_motion()

    # Move in reverse (negative speed)
    def accelerate_backward(self):
        self.speed = max(self.speed - self.acceleration, -self.max_speed / 2)
        self.update_motion()

    # Update position based on speed and heading
    def update_motion(self):
        radians = math.radians(self.heading)
        vert = math.cos(radians) * self.speed
        horiz = math.sin(radians) * self.speed
        self.y_pos -= vert
        self.x_pos -= horiz

    # Pixel-perfect collision check using masks
    def collides_with(self, mask, x_pos=0, y_pos=0):
        car_mask = pygame.mask.from_surface(self.sprite)
        screen_offset = (int(self.x_pos - x_pos), int(self.y_pos - y_pos))
        poi = mask.overlap(car_mask, screen_offset)
        return poi

    # Reset car or game state to defaults
    def reset_state(self):
        self.x_pos, self.y_pos = self.START_POSITION
        self.heading = 0
        self.speed = 0

# Player-controlled car behavior
class PlayerCar(AbstractCar):
    IMAGE = PLAYER_CAR_IMAGE
    START_POSITION = (180, 200)

    # Slow down gradually when no input is given
    def apply_friction(self):
        self.speed = max(self.speed - self.acceleration / 2, 0)
        self.update_motion()

    # Small bounce-back when hitting the edge
    def bounce(self):
        self.speed = -self.speed
        self.update_motion()

# Simple AI car that follows waypoints
class ComputerCar(AbstractCar):
    IMAGE = AI_CAR_IMAGE
    START_POSITION = (150, 200)

    def __init__(self, max_speed, turn_speed, waypoints=[]):
        super().__init__(max_speed, turn_speed)
        self.waypoints = waypoints
        self.waypoint_index = 0
        self.speed = max_speed

    # Debug: draw AI waypoint dots
    def draw_points(self, screen):
        for point in self.waypoints:
            pygame.render.circle(screen, (255, 0, 0), point, 5)

    # Draw the car sprite at its current position/heading
    def render(self, screen):
        super().render(screen)

    # Turn AI car toward the next waypoint
    def compute_angle(self):
        target_x_pos, target_y_pos = self.waypoints[self.waypoint_index]
        dx = target_x_pos - self.x_pos
        dy = target_y_pos - self.y_pos

        if dy == 0:
            desired_angle_rad = math.pi / 2
        else:
            desired_angle_rad = math.atan(dx / dy)
        
        if target_y_pos > self.y_pos:
            desired_angle_rad += math.pi
        angle_delta = self.heading - math.degrees(desired_angle_rad)
        
        if angle_delta >= 180:
            angle_delta -= 360
        
        if angle_delta > 0:
            self.heading -= min(self.turn_speed, abs(angle_delta))
        else:
            self.heading += min(self.turn_speed, abs(angle_delta))

    # Advance to the next waypoint when close enough
    def advance_waypoint(self):
        target_idx = self.waypoints[self.waypoint_index]
        rect = pygame.Rect(self.x_pos, self.y_pos, self.sprite.get_width(), self.sprite.get_height())
        
        if rect.collidepoint(*target_idx):
            self.waypoint_index += 1

    # Update position based on speed and heading
    def update_motion(self):
        if self.waypoint_index >= len(self.waypoints):
            return
        
        self.compute_angle()
        self.advance_waypoint()
        super().update_motion()

    # Adjust AI per level or progress state
    def advance_level(self, stage):
        self.reset_state()
        self.speed = self.max_speed + (stage - 1) * 0.2
        self.waypoint_index = 0

# Draw the scene: background, track, cars, and HUD
def draw(screen, images, player, opponent, race_state):
    for sprite, pos in images:
        screen.blit(sprite, pos)
    
    # HUD: level
    stage_text = UI_FONT.render(f'Level {race_state.stage}', 1, (255, 255, 255))
    screen.blit(stage_text, (10, SCREEN_HEIGHT - stage_text.get_height() - 70))
    
    # HUD: timer
    timer_text = UI_FONT.render(f'Time: {race_state.get_stage_time()}s', 1, (255, 255, 255))
    screen.blit(timer_text, (10, SCREEN_HEIGHT - timer_text.get_height() - 40))
    
    # HUD: speed
    speed_text = UI_FONT.render(f'Vel: {round(player.speed, 1)}px/s', 1, (255, 255, 255))
    screen.blit(speed_text, (10, SCREEN_HEIGHT - speed_text.get_height() - 10))
    player.render(screen)
    opponent.render(screen)
    pygame.display.update()

# Handle keyboard input for the player car
def move_player(player):
    keys = pygame.key.get_pressed()
    moved = False

    if keys[pygame.K_a]:
        player.rotate(left=True)
    
    if keys[pygame.K_d]:
        player.rotate(right=True)
    
    if keys[pygame.K_w]:
        moved = True
        player.accelerate_forward()
    
    if keys[pygame.K_s]:
        moved = True
        player.accelerate_backward()
    
    if not moved:
        player.apply_friction()

# Handle collisions with track edges and finish line
def handle_collision(player, opponent, race_state):
    if player.collides_with(TRACK_EDGE_MASK) != None:
        player.bounce()
    computer_finish_poi_collide = opponent.collides_with(FINISH_LINE_MASK, *FINISH_POS)
    if computer_finish_poi_collide != None:
        blit_text_center(SCREEN, UI_FONT, 'You lost!')
        pygame.display.update()
        pygame.time.wait(5000)
        race_state.reset_state()
        player.reset_state()
        opponent.reset_state()
    
    player_finish_poi_collide = player.collides_with(FINISH_LINE_MASK, *FINISH_POS)
    if player_finish_poi_collide != None:
        if player_finish_poi_collide[1] == 0:
            player.bounce()
        else:
            race_state.advance_level()
            player.reset_state()
            opponent.advance_level(race_state.stage)
run = True

# Clock to cap the frame rate
game_clock = pygame.time.Clock()

# Static images to blit each frame (draw order)
images = [(TURF, (0, 0)), (RACE_TRACK, (0, 0)), (FINISH_LINE, FINISH_POS), (TRACK_EDGE, (0, 0))]
player = PlayerCar(4, 4)
opponent = ComputerCar(2, 4, WAYPOINTS)
race_state = GameInfo()

# Main game loop
while run:

    # Cap the FPS
    game_clock.tick(FRAME_RATE)
    draw(SCREEN, images, player, opponent, race_state)

    # Waiting screen until the level starts
    while not race_state.in_progress:
        blit_text_center(SCREEN, UI_FONT, f'Press any key to start level {race_state.stage}!')
        pygame.display.update()
        
        # Handle user input and quit events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                break
            
            if event.type == pygame.KEYDOWN:
                race_state.start_stage()
    
    # Handle user input and quit events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
            break
    
    move_player(player)
    opponent.update_motion()
    handle_collision(player, opponent, race_state)
    
    if race_state.is_game_finished():
        blit_text_center(SCREEN, UI_FONT, 'You won the game!')
        pygame.time.wait(5000)
        race_state.reset_state()
        player.reset_state()
        opponent.reset_state()


pygame.quit()