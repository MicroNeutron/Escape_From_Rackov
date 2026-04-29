# entities/item.py
import pygame

class Item:
    def __init__(self, name, icon_color, max_stack=5):
        self.name = name
        self.icon = pygame.Surface((32, 32))
        self.icon.fill(icon_color)
        self.max_stack = max_stack
        self.stack = 1   # 当前堆叠数量

    def can_stack_with(self, other):
        return self.name == other.name and self.stack < self.max_stack

    def add_one(self):
        if self.stack < self.max_stack:
            self.stack += 1
            return True
        return False

    def remove_one(self):
        if self.stack > 0:
            self.stack -= 1
            return True
        return False

class HealthItem(Item):
    def __init__(self):
        super().__init__("health", (255, 100, 100), max_stack=5)

class AmmoItem(Item):   # 预留，暂不使用
    def __init__(self):
        super().__init__("ammo", (0, 100, 255), max_stack=5)