import os
os.environ['SDL_VIDEODRIVER'] = 'windib'
import pygame
pygame.init()
screen = pygame.display.set_mode((400,300))
clock = pygame.time.Clock()
running = True
while running:
    dt = clock.tick(60)/1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            print(f"Key down: {event.key} ({pygame.key.name(event.key)})")
    # 或者轮询状态
    keys = pygame.key.get_pressed()
    for k in [pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
        if keys[k]:
            print(f"{pygame.key.name(k)} pressed")
    screen.fill((0,0,0))
    pygame.display.flip()
pygame.quit()