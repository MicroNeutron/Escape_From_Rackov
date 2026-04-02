# entities/player.py
import pygame
import settings

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # 创建不同方向的简单图像（实际后期会用动画）
        self.image_right = pygame.Surface((32, 32))
        self.image_right.fill((0, 255, 0))
        self.image_left = pygame.Surface((32, 32))
        self.image_left.fill((0, 200, 0))
        self.image = self.image_right
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = 0
        self.vy = 0
        self.direction = "right"   # "left" 或 "right"

    def update(self, dt):
        # 获取按键
        keys = pygame.key.get_pressed()
        self.vx = 0
        self.vy = 0

        if keys[pygame.K_a]:
            self.vx = -settings.PLAYER_SPEED
            self.direction = "left"
        if keys[pygame.K_d]:
            self.vx = settings.PLAYER_SPEED
            self.direction = "right"
        if keys[pygame.K_w]:
            self.vy = -settings.PLAYER_SPEED
        if keys[pygame.K_s]:
            self.vy = settings.PLAYER_SPEED
    
        # 移动
        self.rect.x += self.vx * dt
        self.rect.y += self.vy * dt

        # 边界限制（防止超出世界）
        self.rect.x = max(0, min(self.rect.x, settings.WORLD_WIDTH - self.rect.width))
        self.rect.y = max(0, min(self.rect.y, settings.WORLD_HEIGHT - self.rect.height))

        # 根据方向切换图像
        self.image = self.image_right if self.direction == "right" else self.image_left