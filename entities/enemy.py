# entities/enemy.py
import pygame
import settings
import math
import random

def collide_hitbox(sprite_a, sprite_b):
    a_rect = sprite_a.hitbox if hasattr(sprite_a, 'hitbox') else sprite_a.rect
    b_rect = sprite_b.hitbox if hasattr(sprite_b, 'hitbox') else sprite_b.rect
    return a_rect.colliderect(b_rect)

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((32, 32))
        self.image.fill((255, 0, 0))
        self.rect = self.image.get_rect(center=(x, y))
        hitbox_size = settings.TILE_SIZE // 2
        self.hitbox = pygame.Rect(0, 0, hitbox_size, hitbox_size)
        self.hitbox.center = self.rect.center
        self.speed = settings.ENEMY_SPEED
        self.max_hp = settings.ENEMY_HP
        self.hp = self.max_hp
        # 掉落参数
        self.gold_drop_min = settings.ENEMY_GOLD_DROP_MIN
        self.gold_drop_max = settings.ENEMY_GOLD_DROP_MAX
        self.ammo_drop_chance = settings.ENEMY_AMMO_DROP_CHANCE
        self.health_drop_chance = settings.ENEMY_HEALTH_DROP_CHANCE

    def take_damage(self, amount):
        self.hp -= amount
        return self.hp <= 0

    def drop_loot(self):
        """返回 (金币数量, 弹药包值, 血包值)"""
        gold = random.randint(self.gold_drop_min, self.gold_drop_max)
        ammo_value = None
        health_value = None
        if random.random() < self.ammo_drop_chance:
            ammo_value = settings.AMMO_PACK_VALUE
        if random.random() < self.health_drop_chance:
            health_value = settings.HEALTH_PACK_VALUE
        return gold, ammo_value, health_value

    def update(self, dt, player_pos):
        dx = player_pos[0] - self.rect.centerx
        dy = player_pos[1] - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0:
            dx /= dist
            dy /= dist
        self.rect.x += dx * self.speed * dt
        self.rect.y += dy * self.speed * dt
        self.hitbox.center = self.rect.center

    def draw_health(self, screen, camera_offset):
        if self.hp <= 0 or self.hp == self.max_hp:
            return
        font = pygame.font.Font(None, 20)
        text = font.render(str(self.hp), True, (255, 255, 255))
        screen_x = self.rect.centerx - camera_offset[0] - text.get_width() // 2
        screen_y = self.rect.top - camera_offset[1] - 15
        screen.blit(text, (screen_x, screen_y))