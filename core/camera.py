# core/camera.py
import pygame

class Camera:
    def __init__(self, screen_width, screen_height, world_width, world_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.world_width = world_width
        self.world_height = world_height
        self.offset = pygame.math.Vector2(0, 0)
        self.target = None

    def follow(self, target):
        """设置跟随的目标（通常是玩家）"""
        self.target = target

    def update(self, target=None):
        """更新摄像机位置，使其跟随目标并限制在世界范围内"""
        if target is None:
            target = self.target
        if target is None:
            return

        # 理想偏移量 = 目标位置 - 屏幕中心
        ideal_x = target.rect.centerx - self.screen_width // 2
        ideal_y = target.rect.centery - self.screen_height // 2

        # 边界限制：防止摄像机超出世界范围
        self.offset.x = max(0, min(ideal_x, self.world_width - self.screen_width))
        self.offset.y = max(0, min(ideal_y, self.world_height - self.screen_height))

    def apply(self, rect):
        """将世界坐标矩形转换为屏幕坐标矩形"""
        return rect.move(-self.offset.x, -self.offset.y)

    def apply_offset(self, pos):
        """将世界坐标点转换为屏幕坐标点"""
        return (pos[0] - self.offset.x, pos[1] - self.offset.y)