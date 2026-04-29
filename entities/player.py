# entities/player.py
import pygame
import settings
from entities.item import HealthItem

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image_right = pygame.Surface((32, 32))
        self.image_right.fill((0, 255, 0))
        self.image_left = pygame.Surface((32, 32))
        self.image_left.fill((0, 200, 0))
        self.image = self.image_right
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = 0
        self.vy = 0
        self.direction = "right"
        self.hp = settings.PLAYER_MAX_HP
        self.max_hp = settings.PLAYER_MAX_HP
        self.ammo = settings.PLAYER_MAX_AMMO
        self.max_ammo = settings.PLAYER_MAX_AMMO
        self.invincible_time = 0.0
        self.invincible_duration = 0.5
        self.gold = 0  # 随身金币
        self.bank_gold = 0   # 银行存款

        # 物品栏：初始4格，每格可以是 None 或 Item 对象
        self.inventory = [None] * 4
        self.max_inventory_slots = 4

    def add_item_to_inventory(self, item):
        """尝试将物品添加到物品栏，成功返回True，否则False"""
        for i, slot in enumerate(self.inventory):
            if slot and slot.name == item.name and slot.stack < slot.max_stack:
                slot.stack += 1
                return True
        for i, slot in enumerate(self.inventory):
            if slot is None:
                self.inventory[i] = item
                return True
        return False

    def remove_item_from_inventory(self, index, count=1):
        if index < 0 or index >= len(self.inventory):
            return False
        slot = self.inventory[index]
        if slot is None:
            return False
        if slot.stack >= count:
            slot.stack -= count
            if slot.stack <= 0:
                self.inventory[index] = None
            return True
        return False

    def use_health_item(self):
        for i, slot in enumerate(self.inventory):
            if slot and slot.name == "health":
                if self.hp < self.max_hp:
                    self.hp = min(self.hp + 1, self.max_hp)
                    self.remove_item_from_inventory(i, 1)
                    return True
                else:
                    return False
        return False

    def get_health_item_count(self):
        total = 0
        for slot in self.inventory:
            if slot and slot.name == "health":
                total += slot.stack
        return total

    def use_health_item_at_index(self, index):
        """使用指定索引的血包（假设该格子是血包）"""
        if index < 0 or index >= len(self.inventory):
            return False
        slot = self.inventory[index]
        if slot and slot.name == "health":
            if self.hp < self.max_hp:
                self.hp = min(self.hp + 1, self.max_hp)
                self.remove_item_from_inventory(index, 1)
                return True
        return False

    def take_damage(self, amount):
        if self.invincible_time > 0:
            return False
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            return True
        self.invincible_time = self.invincible_duration
        return False

    def heal(self, amount):
        self.hp = min(self.hp + amount, self.max_hp)

    def can_shoot(self):
        return self.ammo > 0

    def shoot(self):
        if self.can_shoot():
            self.ammo -= 1
            return True
        return False

    def update(self, dt):
        if self.invincible_time > 0:
            self.invincible_time -= dt

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

        self.rect.x += self.vx * dt
        self.rect.y += self.vy * dt
        self.rect.x = max(0, min(self.rect.x, settings.WORLD_WIDTH - self.rect.width))
        self.rect.y = max(0, min(self.rect.y, settings.WORLD_HEIGHT - self.rect.height))

        self.image = self.image_right if self.direction == "right" else self.image_left

    def deposit_gold(self, amount):
        """将随身金币存入银行，amount 不能超过当前 gold"""
        if amount <= self.gold:
            self.gold -= amount
            self.bank_gold += amount
            return True
        return False

    def withdraw_gold(self, amount):
        """从银行取款，amount 不能超过 bank_gold"""
        if amount <= self.bank_gold:
            self.bank_gold -= amount
            self.gold += amount
            return True
        return False