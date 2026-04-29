# entities/health_pack.py
import pygame
from entities.item import HealthItem

class HealthPack(pygame.sprite.Sprite):
    def __init__(self, x, y, target_pos=None):
        super().__init__()
        self.image = pygame.Surface((16, 16))
        self.image.fill((255, 100, 100))
        self.rect = self.image.get_rect(center=(x, y))
        self.item = HealthItem()
        # 抛物线动画
        self.animating = target_pos is not None
        self.can_pickup = not self.animating
        if self.animating:
            self.start_pos = (x, y)
            self.target_pos = target_pos
            self.progress = 0.0
            self.duration = 0.3
        else:
            self.start_pos = None
            self.target_pos = None
            self.progress = 1.0

    def update(self, dt):
        if self.animating and self.progress < 1.0:
            self.progress += dt / self.duration
            if self.progress >= 1.0:
                self.progress = 1.0
                self.rect.center = self.target_pos
                self.animating = False
                self.can_pickup = True
            else:
                t = self.progress
                arc = 30 * 4 * t * (1 - t)
                x = self.start_pos[0] + (self.target_pos[0] - self.start_pos[0]) * t
                y = self.start_pos[1] + (self.target_pos[1] - self.start_pos[1]) * t - arc
                self.rect.center = (int(x), int(y))