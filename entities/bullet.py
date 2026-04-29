# entities/bullet.py
import pygame
import settings

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        super().__init__()
        self.image = pygame.Surface((8, 8))
        self.image.fill((255, 255, 0))   # 黄色
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = direction[0] * settings.BULLET_SPEED
        self.vy = direction[1] * settings.BULLET_SPEED

    def update(self, dt):
        self.rect.x += self.vx * dt
        self.rect.y += self.vy * dt
        # 超出屏幕一定距离则删除
        if (self.rect.x < -200 or self.rect.x > settings.WORLD_WIDTH + 200 or
            self.rect.y < -200 or self.rect.y > settings.WORLD_HEIGHT + 200):
            self.kill()