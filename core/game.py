import pygame
import settings
from core.camera import Camera
from entities.player import Player

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        pygame.display.set_caption("Game Demo")
        self.clock = pygame.time.Clock()
        self.running = True

        # 创建玩家
        self.player = Player(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2)
        
        # 创建摄像机
        self.camera = Camera(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT,
                             settings.WORLD_WIDTH, settings.WORLD_HEIGHT)
        self.camera.follow(self.player)

        # 一个简单的精灵组，方便后续扩展
        self.all_sprites = pygame.sprite.Group()
        self.all_sprites.add(self.player)

    def run(self):
        while self.running:
            dt = self.clock.tick(settings.FPS) / 1000.0   # 转换为秒

            # 事件处理
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            # 更新
            self.player.update(dt)
            self.camera.update(self.player)   # 让摄像机跟随玩家

            # 绘制
            self.screen.fill((30, 30, 30))    # 深灰色背景
            self.draw_grid()                  # 绘制网格，体现摄像机移动

            # 手动绘制所有精灵（应用摄像机偏移）
            for sprite in self.all_sprites:
                screen_rect = self.camera.apply(sprite.rect)
                self.screen.blit(sprite.image, screen_rect)

            pygame.display.flip()

    def draw_grid(self):
        """根据摄像机偏移绘制网格线，模拟地图背景"""
        # 获取摄像机偏移
        offset_x, offset_y = self.camera.offset

        # 计算需要绘制的网格起始和结束范围
        start_x = int(offset_x // settings.TILE_SIZE) * settings.TILE_SIZE - offset_x
        start_y = int(offset_y // settings.TILE_SIZE) * settings.TILE_SIZE - offset_y
        end_x = settings.SCREEN_WIDTH
        end_y = settings.SCREEN_HEIGHT

        # 绘制垂直线
        x = start_x
        while x <= end_x:
            pygame.draw.line(self.screen, (80, 80, 80), (x, 0), (x, settings.SCREEN_HEIGHT))
            x += settings.TILE_SIZE

        # 绘制水平线
        y = start_y
        while y <= end_y:
            pygame.draw.line(self.screen, (80, 80, 80), (0, y), (settings.SCREEN_WIDTH, y))
            y += settings.TILE_SIZE