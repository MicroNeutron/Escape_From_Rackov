# core/game.py
import pygame
import settings
from core.camera import Camera
from entities.player import Player
from entities.enemy import Enemy, collide_hitbox
from entities.bullet import Bullet
from entities.coin import Coin
from entities.ammo_pack import AmmoPack
from entities.health_pack import HealthPack
from entities.item import HealthItem
import math
import random
import json
import os

# 存档文件路径（基于项目根目录）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_FILE_PATH = os.path.join(_PROJECT_ROOT, "save_data.json")

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        pygame.display.set_caption("Escape From Rackov")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "PLAYING"
        self.zone = "safe"
        self.switch_cooldown = 0.0

        self.player = Player(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2)
        self.camera = Camera(settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT,
                             settings.WORLD_WIDTH, settings.WORLD_HEIGHT)
        self.camera.follow(self.player)

        self.all_sprites = pygame.sprite.Group()
        self.all_sprites.add(self.player)
        self.enemies = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.coins = pygame.sprite.Group()
        self.ammo_packs = pygame.sprite.Group()
        self.health_packs = pygame.sprite.Group()

        self.door_rect = pygame.Rect(settings.DOOR_X, settings.DOOR_Y,
                                     settings.DOOR_WIDTH, settings.DOOR_HEIGHT)

        self.item_spawn_times = {}
        self.floating_texts = []
        self.slot_rects = []
        self.drop_rects = []
        self.gold_before_death = 0
        self.gold_loss = 0
        self.last_full_inventory_msg_time = 0

        # HUD 消息系统（底部中央）
        self.hud_messages = []

        # 左下角拾取提示，每个元素为 [text, icon_color, lifetime]
        self.pickup_messages = []

        # UI 状态
        self.inventory_open = False
        self.selected_slot = None

        # 银行系统
        self.bank_rect = pygame.Rect(settings.BANK_X, settings.BANK_Y,
                                     settings.BANK_WIDTH, settings.BANK_HEIGHT)
        self.bank_ui_open = False
        self.bank_ui_buttons = []
        self.bank_cooldown = 0.0  # 银行退出冷却（5秒）
        self.bank_page = "home"   # 银行页面: "home", "balance", "deposit", "withdraw"
        self.bank_input = ""      # 银行输入框内容
        self.bank_input_active = False  # 输入框是否激活
        self.bank_message = ""    # 银行操作结果消息
        self.bank_message_timer = 0.0  # 消息显示计时

        # 加载存档
        self.load_save_data()
        self.init_zone()

        self.font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 36)
        self.ammo_spawn_timer = 0
        self.health_spawn_timer = 0
        self.ammo_spawn_interval = 5.0
        self.health_spawn_interval = 10.0

    # ---------- 存档系统 ----------
    def save_game_data(self):
        inv_data = []
        for slot in self.player.inventory:
            if slot:
                inv_data.append({"name": slot.name, "stack": slot.stack})
            else:
                inv_data.append(None)
        data = {
            "gold": self.gold,
            "ammo": self.player.ammo,
            "inventory": inv_data,
            "bank_gold": self.player.bank_gold
        }
        try:
            with open(SAVE_FILE_PATH, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"保存失败: {e}")

    def load_save_data(self):
        if not os.path.exists(SAVE_FILE_PATH):
            self.gold = 0
            self.player.gold = 0
            return
        try:
            with open(SAVE_FILE_PATH, "r") as f:
                data = json.load(f)
            self.gold = data.get("gold", 0)
            self.player.gold = self.gold
            self.player.ammo = data.get("ammo", settings.PLAYER_MAX_AMMO)
            if self.player.ammo > self.player.max_ammo:
                self.player.ammo = self.player.max_ammo
            self.player.bank_gold = data.get("bank_gold", 0)
            inv_data = data.get("inventory", [None] * self.player.max_inventory_slots)
            self.player.inventory = [None] * self.player.max_inventory_slots
            for i, item_data in enumerate(inv_data):
                if item_data and i < len(self.player.inventory):
                    name = item_data["name"]
                    stack = item_data["stack"]
                    if name == "health":
                        item = HealthItem()
                        item.stack = stack
                        self.player.inventory[i] = item
        except Exception as e:
            print(f"加载失败: {e}")
            self.gold = 0
            self.player.gold = 0

    # ---------- UI 消息 ----------
    def add_hud_message(self, text, duration=2.0):
        self.hud_messages.append([text, duration])

    def add_pickup_message(self, item_type, value, duration=2.0):
        if item_type == "health":
            text = f"+{value}"
            icon_color = (255, 100, 100)
        elif item_type == "ammo":
            text = f"+{value}"
            icon_color = (0, 100, 255)
        else:  # gold
            text = f"+{value}"
            icon_color = (255, 215, 0)
        self.pickup_messages.append([text, icon_color, duration])

    # ---------- 区域管理 ----------
    def init_zone(self):
        for e in self.enemies:
            e.kill()
        for b in self.bullets:
            b.kill()
        for c in self.coins:
            c.kill()
        for a in self.ammo_packs:
            a.kill()
        for h in self.health_packs:
            h.kill()
        self.item_spawn_times.clear()
        self.floating_texts.clear()
        if self.zone == "warzone":
            for _ in range(settings.MIN_ENEMIES):
                self.spawn_enemy()
            self.ammo_spawn_timer = 0
            self.health_spawn_timer = 0

    def switch_zone(self):
        if self.switch_cooldown > 0:
            return
        if self.zone == "safe":
            self.zone = "warzone"
        else:
            self.zone = "safe"
        self.init_zone()
        self.player.rect.centerx = settings.DOOR_X + settings.DOOR_WIDTH // 2
        self.player.rect.bottom = settings.DOOR_Y + settings.DOOR_HEIGHT + 10
        self.camera.update(self.player)
        self.switch_cooldown = settings.ZONE_SWITCH_COOLDOWN
        self.inventory_open = False

    # ---------- 生成敌人/物品 ----------
    def spawn_enemy(self):
        while True:
            x = random.randint(100, settings.WORLD_WIDTH - 100)
            y = random.randint(100, settings.WORLD_HEIGHT - 100)
            dist_to_player = math.hypot(x - self.player.rect.centerx, y - self.player.rect.centery)
            if dist_to_player > 100:
                break
        enemy = Enemy(x, y)
        self.enemies.add(enemy)
        self.all_sprites.add(enemy)

    def spawn_ammo_pack(self):
        if self.zone != "warzone":
            return
        while True:
            x = random.randint(50, settings.WORLD_WIDTH - 50)
            y = random.randint(50, settings.WORLD_HEIGHT - 50)
            dist_to_player = math.hypot(x - self.player.rect.centerx, y - self.player.rect.centery)
            if dist_to_player > 150:
                break
        ammo = AmmoPack(x, y, settings.AMMO_PACK_VALUE)
        self.ammo_packs.add(ammo)
        self.all_sprites.add(ammo)
        self.record_item_spawn(ammo)

    def spawn_health_pack(self):
        if self.zone != "warzone":
            return
        while True:
            x = random.randint(50, settings.WORLD_WIDTH - 50)
            y = random.randint(50, settings.WORLD_HEIGHT - 50)
            dist_to_player = math.hypot(x - self.player.rect.centerx, y - self.player.rect.centery)
            if dist_to_player > 150:
                break
        health = HealthPack(x, y)
        self.health_packs.add(health)
        self.all_sprites.add(health)
        self.record_item_spawn(health)

    def record_item_spawn(self, item):
        self.item_spawn_times[item] = pygame.time.get_ticks()

    def check_item_lifespan(self):
        current_time = pygame.time.get_ticks()
        for item in list(self.item_spawn_times.keys()):
            spawn_time = self.item_spawn_times[item]
            if current_time - spawn_time > settings.ITEM_LIFESPAN * 1000:
                if item in self.item_spawn_times:
                    del self.item_spawn_times[item]
                item.kill()

    # ---------- 游戏重置 ----------
    def reset_game(self):
        self.gold = 0
        self.player.gold = 0
        self.player.ammo = 10
        if self.player.ammo > self.player.max_ammo:
            self.player.ammo = self.player.max_ammo
        self.player.inventory = [None] * self.player.max_inventory_slots
        self.zone = "safe"
        self.init_zone()
        self.player.rect.center = (settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2)
        self.player.hp = settings.PLAYER_MAX_HP
        self.player.invincible_time = 0.0
        self.floating_texts.clear()
        self.switch_cooldown = 0.0
        self.state = "PLAYING"
        self.save_game_data()

    # ---------- 浮动文字 ----------
    def add_floating_text(self, text, x, y, color=(255,255,0)):
        self.floating_texts.append({
            "text": text,
            "x": x,
            "y": y,
            "life": 1.0,
            "color": color
        })

    # ---------- 主循环 ----------
    def run(self):
        while self.running:
            dt = self.clock.tick(settings.FPS) / 1000.0

            if self.switch_cooldown > 0:
                self.switch_cooldown -= dt
                if self.switch_cooldown < 0:
                    self.switch_cooldown = 0

            if self.bank_cooldown > 0:
                self.bank_cooldown -= dt
                if self.bank_cooldown < 0:
                    self.bank_cooldown = 0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_game_data()
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.bank_ui_open:
                        self.handle_bank_click(event.pos)
                    elif self.inventory_open:
                        self.handle_inventory_click(event.pos)
                    elif self.state == "PLAYING" and self.zone == "warzone" and self.player.can_shoot():
                        self.shoot()
                elif event.type == pygame.KEYDOWN:
                    if self.state == "PLAYING":
                        # 银行输入框激活时，处理数字输入
                        if self.bank_ui_open and self.bank_input_active:
                            if event.key == pygame.K_BACKSPACE:
                                self.bank_input = self.bank_input[:-1]
                            elif event.key == pygame.K_RETURN:
                                self._confirm_bank_input()
                            elif event.key == pygame.K_ESCAPE:
                                self.bank_input_active = False
                            elif event.unicode.isdigit():
                                self.bank_input += event.unicode
                        elif self.bank_ui_open:
                            if event.key == pygame.K_ESCAPE:
                                if self.bank_page == "home":
                                    self._close_bank_ui()
                                else:
                                    self.bank_page = "home"
                                    self.bank_message = ""
                            elif event.key == pygame.K_e:
                                self._close_bank_ui()
                        else:
                            if event.key == pygame.K_e:
                                self.inventory_open = not self.inventory_open
                            elif event.key == pygame.K_r:
                                if self.player.use_health_item():
                                    screen_pos = self.camera.apply_offset((self.player.rect.centerx, self.player.rect.top - 20))
                                    self.add_floating_text("+1", screen_pos[0], screen_pos[1], (255, 100, 100))
                                    self.save_game_data()
                            elif event.key == pygame.K_ESCAPE:
                                if self.inventory_open:
                                    self.inventory_open = False
                    if self.state == "DEAD" and event.key == pygame.K_SPACE:
                        self.reset_game()

            if self.state == "PLAYING":
                # 银行UI打开时禁止玩家移动
                if not self.bank_ui_open:
                    self.player.update(dt)

                if self.zone == "warzone":
                    for enemy in self.enemies:
                        enemy.update(dt, self.player.rect.center)
                    for bullet in self.bullets:
                        bullet.update(dt)
                    for coin in self.coins:
                        coin.update(dt)
                    for ammo in self.ammo_packs:
                        ammo.update(dt)
                    for health in self.health_packs:
                        health.update(dt)

                    # 子弹 vs 敌人
                    for bullet in self.bullets:
                        hit_enemies = pygame.sprite.spritecollide(bullet, self.enemies, False, collide_hitbox)
                        for enemy in hit_enemies:
                            if enemy.take_damage(1):
                                gold, ammo_val, health_val = enemy.drop_loot()
                                offset_range = 20
                                if gold > 0:
                                    start_x = enemy.rect.centerx
                                    start_y = enemy.rect.centery
                                    end_x = start_x + random.randint(-offset_range, offset_range)
                                    end_y = start_y + random.randint(-offset_range, offset_range)
                                    end_x = max(0, min(end_x, settings.WORLD_WIDTH))
                                    end_y = max(0, min(end_y, settings.WORLD_HEIGHT))
                                    coin = Coin(start_x, start_y, gold, target_pos=(end_x, end_y))
                                    self.coins.add(coin)
                                    self.all_sprites.add(coin)
                                    self.record_item_spawn(coin)
                                if ammo_val is not None:
                                    start_x = enemy.rect.centerx
                                    start_y = enemy.rect.centery
                                    end_x = start_x + random.randint(-offset_range, offset_range)
                                    end_y = start_y + random.randint(-offset_range, offset_range)
                                    end_x = max(0, min(end_x, settings.WORLD_WIDTH))
                                    end_y = max(0, min(end_y, settings.WORLD_HEIGHT))
                                    ammo_pack = AmmoPack(start_x, start_y, ammo_val, target_pos=(end_x, end_y))
                                    self.ammo_packs.add(ammo_pack)
                                    self.all_sprites.add(ammo_pack)
                                    self.record_item_spawn(ammo_pack)
                                if health_val is not None:
                                    start_x = enemy.rect.centerx
                                    start_y = enemy.rect.centery
                                    end_x = start_x + random.randint(-offset_range, offset_range)
                                    end_y = start_y + random.randint(-offset_range, offset_range)
                                    end_x = max(0, min(end_x, settings.WORLD_WIDTH))
                                    end_y = max(0, min(end_y, settings.WORLD_HEIGHT))
                                    health_pack = HealthPack(start_x, start_y, target_pos=(end_x, end_y))
                                    self.health_packs.add(health_pack)
                                    self.all_sprites.add(health_pack)
                                    self.record_item_spawn(health_pack)
                                enemy.kill()
                                # 击杀后：补回被杀的1个 + 额外增加1个 = 净增1个敌人
                                self.spawn_enemy()
                                self.spawn_enemy()
                            bullet.kill()

                    # 自然刷新
                    self.ammo_spawn_timer += dt
                    if self.ammo_spawn_timer >= self.ammo_spawn_interval:
                        self.ammo_spawn_timer = 0
                        if len(self.ammo_packs) < 5:
                            self.spawn_ammo_pack()
                    self.health_spawn_timer += dt
                    if self.health_spawn_timer >= self.health_spawn_interval:
                        self.health_spawn_timer = 0
                        if len(self.health_packs) < 3:
                            self.spawn_health_pack()

                    self.check_item_lifespan()

                # 拾取逻辑（安全区和战区都执行）
                # 金币
                collected_coins = pygame.sprite.spritecollide(self.player, self.coins, False)
                for coin in collected_coins:
                    if not coin.can_pickup:
                        continue
                    self.gold += coin.value
                    self.player.gold = self.gold
                    self.add_pickup_message("gold", coin.value)
                    screen_pos = self.camera.apply_offset((self.player.rect.centerx, self.player.rect.top - 20))
                    self.add_floating_text(f"+{coin.value}", screen_pos[0], screen_pos[1], (255, 215, 0))
                    if coin in self.item_spawn_times:
                        del self.item_spawn_times[coin]
                    coin.kill()
                    self.save_game_data()

                # 弹药包
                collected_ammo = pygame.sprite.spritecollide(self.player, self.ammo_packs, False)
                for ammo in collected_ammo:
                    if not ammo.can_pickup:
                        continue
                    self.player.ammo = min(self.player.ammo + ammo.ammo_value, self.player.max_ammo)
                    self.add_pickup_message("ammo", ammo.ammo_value)
                    screen_pos = self.camera.apply_offset((self.player.rect.centerx, self.player.rect.top - 20))
                    self.add_floating_text(f"+{ammo.ammo_value}", screen_pos[0], screen_pos[1], (0, 255, 255))
                    if ammo in self.item_spawn_times:
                        del self.item_spawn_times[ammo]
                    ammo.kill()
                    self.save_game_data()

                # 血包
                collected_health = pygame.sprite.spritecollide(self.player, self.health_packs, False)
                for health in collected_health:
                    if not health.can_pickup:
                        continue
                    item = HealthItem()
                    if self.player.add_item_to_inventory(item):
                        self.add_pickup_message("health", 1)
                        if health in self.item_spawn_times:
                            del self.item_spawn_times[health]
                        health.kill()
                        self.save_game_data()
                    else:
                        # 物品栏满，保留在地上，显示提示
                        self.add_hud_message("Inventory full!", 1.5)

                # 玩家碰撞敌人
                hit_enemies = pygame.sprite.spritecollide(self.player, self.enemies, False, collide_hitbox)
                if hit_enemies:
                    if self.player.take_damage(1):
                        self.gold_before_death = self.gold
                        self.gold_loss = self.gold
                        self.state = "DEAD"

                self.camera.update(self.player)

                if self.player.rect.colliderect(self.door_rect) and self.switch_cooldown == 0:
                    self.switch_zone()

                # 触碰银行摊位自动打开银行UI
                if (self.zone == "safe"
                    and not self.bank_ui_open
                    and self.bank_cooldown == 0
                    and self.player.rect.colliderect(self.bank_rect)):
                    self.bank_ui_open = True
                    self.bank_page = "home"
                    self.bank_input = ""
                    self.bank_input_active = False
                    self.bank_message = ""
                    self.bank_message_timer = 0.0
                    self.inventory_open = False

                # 更新浮动文字
                for text in self.floating_texts[:]:
                    text["life"] -= dt
                    if text["life"] <= 0:
                        self.floating_texts.remove(text)

                # 更新 HUD 消息
                for msg in self.hud_messages[:]:
                    msg[1] -= dt
                    if msg[1] <= 0:
                        self.hud_messages.remove(msg)

                # 更新左下角拾取提示
                for msg in self.pickup_messages[:]:
                    msg[2] -= dt
                    if msg[2] <= 0:
                        self.pickup_messages.remove(msg)

                # 更新银行消息计时
                if self.bank_message_timer > 0:
                    self.bank_message_timer -= dt
                    if self.bank_message_timer <= 0:
                        self.bank_message = ""
                        self.bank_message_timer = 0

            # 绘制
            self.draw_background()
            self.draw_door()

            for sprite in self.all_sprites:
                screen_rect = self.camera.apply(sprite.rect)
                self.screen.blit(sprite.image, screen_rect)
            for bullet in self.bullets:
                screen_rect = self.camera.apply(bullet.rect)
                self.screen.blit(bullet.image, screen_rect)
            for coin in self.coins:
                screen_rect = self.camera.apply(coin.rect)
                self.screen.blit(coin.image, screen_rect)
            for ammo in self.ammo_packs:
                screen_rect = self.camera.apply(ammo.rect)
                self.screen.blit(ammo.image, screen_rect)
            for health in self.health_packs:
                screen_rect = self.camera.apply(health.rect)
                self.screen.blit(health.image, screen_rect)

            for enemy in self.enemies:
                enemy.draw_health(self.screen, self.camera.offset)

            self.draw_ui()
            for text in self.floating_texts:
                txt_surf = self.small_font.render(text["text"], True, text["color"])
                self.screen.blit(txt_surf, (text["x"], text["y"]))

            if self.inventory_open:
                self.draw_inventory()
            if self.bank_ui_open:
                self.draw_bank_ui()

            if self.state == "DEAD":
                self.draw_death_screen()

            pygame.display.flip()

    def shoot(self):
        if not self.player.shoot():
            return
        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_mouse = (mouse_x + self.camera.offset.x, mouse_y + self.camera.offset.y)
        dx = world_mouse[0] - self.player.rect.centerx
        dy = world_mouse[1] - self.player.rect.centery
        length = math.hypot(dx, dy)
        if length > 0:
            dx /= length
            dy /= length
        bullet = Bullet(self.player.rect.centerx, self.player.rect.centery, (dx, dy))
        self.bullets.add(bullet)

    # ---------- 绘制函数 ----------
    def draw_background(self):
        if self.zone == "safe":
            self.screen.fill((50, 50, 150))
            offset_x, offset_y = self.camera.offset
            start_x = int(offset_x // settings.TILE_SIZE) * settings.TILE_SIZE - offset_x
            start_y = int(offset_y // settings.TILE_SIZE) * settings.TILE_SIZE - offset_y
            end_x = settings.SCREEN_WIDTH
            end_y = settings.SCREEN_HEIGHT
            x = start_x
            while x <= end_x:
                pygame.draw.line(self.screen, (100, 100, 200), (x, 0), (x, settings.SCREEN_HEIGHT))
                x += settings.TILE_SIZE
            y = start_y
            while y <= end_y:
                pygame.draw.line(self.screen, (100, 100, 200), (0, y), (settings.SCREEN_WIDTH, y))
                y += settings.TILE_SIZE

            # ====== 新增：绘制银行摊位 ======
            bank_screen_rect = self.camera.apply(self.bank_rect)
            # 木色背景
            pygame.draw.rect(self.screen, (160, 120, 80), bank_screen_rect)
            # 黑色边框
            pygame.draw.rect(self.screen, (0, 0, 0), bank_screen_rect, 2)
            # 钱袋符号 "$"
            font = pygame.font.Font(None, 36)
            money_sign = font.render("$", True, (255, 215, 0))
            sign_rect = money_sign.get_rect(center=bank_screen_rect.center)
            self.screen.blit(money_sign, sign_rect)

        else:  # warzone
            self.screen.fill((30, 30, 30))
            offset_x, offset_y = self.camera.offset
            start_x = int(offset_x // settings.TILE_SIZE) * settings.TILE_SIZE - offset_x
            start_y = int(offset_y // settings.TILE_SIZE) * settings.TILE_SIZE - offset_y
            end_x = settings.SCREEN_WIDTH
            end_y = settings.SCREEN_HEIGHT
            x = start_x
            while x <= end_x:
                pygame.draw.line(self.screen, (50, 50, 50), (x, 0), (x, settings.SCREEN_HEIGHT))
                x += settings.TILE_SIZE
            y = start_y
            while y <= end_y:
                pygame.draw.line(self.screen, (50, 50, 50), (0, y), (settings.SCREEN_WIDTH, y))
                y += settings.TILE_SIZE

    def draw_door(self):
        screen_rect = self.camera.apply(self.door_rect)
        pygame.draw.rect(self.screen, (139, 69, 19), screen_rect)
        pygame.draw.rect(self.screen, (100, 50, 10), screen_rect, 3)

    def draw_ui(self):
        # 血条
        bar_width = 200
        bar_height = 20
        bg_rect = pygame.Rect(10, 10, bar_width, bar_height)
        pygame.draw.rect(self.screen, (100, 100, 100), bg_rect)
        hp_percent = self.player.hp / self.player.max_hp
        fill_width = bar_width * hp_percent
        fill_rect = pygame.Rect(10, 10, fill_width, bar_height)
        pygame.draw.rect(self.screen, (255, 0, 0), fill_rect)

        # 图标和数值
        icon_size = 24
        y_offset = 50
        # HP
        hp_icon = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.circle(hp_icon, (255, 0, 0), (icon_size//2, icon_size//2), icon_size//2)
        self.screen.blit(hp_icon, (10, y_offset))
        hp_text = self.small_font.render(f"{self.player.hp}/{self.player.max_hp}", True, (255, 255, 255))
        self.screen.blit(hp_text, (10 + icon_size + 5, y_offset + 4))

        y_offset += 35
        ammo_icon = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.rect(ammo_icon, (255, 255, 0), (4, 8, 16, 8))
        pygame.draw.circle(ammo_icon, (255, 255, 0), (20, 12), 4)
        self.screen.blit(ammo_icon, (10, y_offset))
        ammo_text = self.small_font.render(f"{self.player.ammo}/{self.player.max_ammo}", True, (200, 200, 200))
        self.screen.blit(ammo_text, (10 + icon_size + 5, y_offset + 4))

        y_offset += 35
        gold_icon = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.circle(gold_icon, (255, 215, 0), (icon_size//2, icon_size//2), icon_size//2)
        pygame.draw.circle(gold_icon, (0, 0, 0, 0), (icon_size//2, icon_size//2), icon_size//2 - 2, 1)
        self.screen.blit(gold_icon, (10, y_offset))
        gold_text = self.small_font.render(f"{self.gold}", True, (255, 215, 0))
        self.screen.blit(gold_text, (10 + icon_size + 5, y_offset + 4))

        y_offset += 35
        health_icon = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
        pygame.draw.rect(health_icon, (255, 100, 100), (icon_size//2 - 4, icon_size//2 - 2, 8, 4))
        pygame.draw.rect(health_icon, (255, 100, 100), (icon_size//2 - 2, icon_size//2 - 4, 4, 8))
        self.screen.blit(health_icon, (10, y_offset))
        health_count = self.player.get_health_item_count()
        health_text = self.small_font.render(f"{health_count}", True, (255, 100, 100))
        self.screen.blit(health_text, (10 + icon_size + 5, y_offset + 4))

        y_offset += 35
        zone_text = self.small_font.render(f"ZONE: {self.zone.upper()}", True, (255, 255, 255))
        self.screen.blit(zone_text, (10, y_offset))

        # 底部提示
        if self.state == "PLAYING" and self.zone == "warzone":
            tip = self.small_font.render("Left Click to Shoot | E: Inventory | R: Use Health", True, (200, 200, 200))
            self.screen.blit(tip, (10, settings.SCREEN_HEIGHT - 40))
        elif self.zone == "safe":
            tip = self.small_font.render("Safe Zone - No Combat | E: Inventory | ESC: Close", True, (200, 200, 200))
            self.screen.blit(tip, (10, settings.SCREEN_HEIGHT - 40))

        enemy_count = self.small_font.render(f"Enemies: {len(self.enemies)}", True, (200, 200, 200))
        self.screen.blit(enemy_count, (10, settings.SCREEN_HEIGHT - 70))

        # 固定位置 HUD 消息（底部中央）
        if self.hud_messages:
            latest_msg = self.hud_messages[-1][0]
            msg_surface = self.small_font.render(latest_msg, True, (255, 255, 255))
            bg_rect = msg_surface.get_rect()
            bg_rect.width += 20
            bg_rect.height += 10
            bg_rect.centerx = settings.SCREEN_WIDTH // 2
            bg_rect.bottom = settings.SCREEN_HEIGHT - 20
            s = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            self.screen.blit(s, bg_rect.topleft)
            text_x = bg_rect.centerx - msg_surface.get_width() // 2
            text_y = bg_rect.centery - msg_surface.get_height() // 2
            self.screen.blit(msg_surface, (text_x, text_y))

        # 左下角拾取提示（最新一条）
        if self.pickup_messages:
            latest = self.pickup_messages[-1]
            text, icon_color, _ = latest
            icon_size = 24
            icon_surf = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
            pygame.draw.rect(icon_surf, icon_color, (0, 0, icon_size, icon_size))
            pygame.draw.rect(icon_surf, (255, 255, 255), (0, 0, icon_size, icon_size), 2)
            text_surf = self.small_font.render(text, True, (255, 255, 255))
            total_width = icon_size + 10 + text_surf.get_width() + 20
            total_height = max(icon_size, text_surf.get_height()) + 10
            bg_rect = pygame.Rect(10, settings.SCREEN_HEIGHT - 70, total_width, total_height)
            s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            self.screen.blit(s, bg_rect.topleft)
            icon_x = bg_rect.x + 10
            icon_y = bg_rect.centery - icon_size // 2
            self.screen.blit(icon_surf, (icon_x, icon_y))
            text_x = icon_x + icon_size + 10
            text_y = bg_rect.centery - text_surf.get_height() // 2
            self.screen.blit(text_surf, (text_x, text_y))

    def draw_inventory(self):
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        slot_size = 64
        margin = 20
        total_width = len(self.player.inventory) * slot_size + (len(self.player.inventory)-1) * margin
        start_x = (settings.SCREEN_WIDTH - total_width) // 2
        start_y = settings.SCREEN_HEIGHT // 2 - slot_size // 2

        self.slot_rects = []
        self.drop_rects = []
        for i, item in enumerate(self.player.inventory):
            x = start_x + i * (slot_size + margin)
            y = start_y
            rect = pygame.Rect(x, y, slot_size, slot_size)
            self.slot_rects.append(rect)

            pygame.draw.rect(self.screen, (100, 100, 100), rect)
            pygame.draw.rect(self.screen, (200, 200, 200), rect, 3)

            if item:
                self.screen.blit(item.icon, (x + 16, y + 16))
                count_text = self.small_font.render(str(item.stack), True, (255, 255, 255))
                self.screen.blit(count_text, (x + slot_size - 20, y + slot_size - 20))
                # 只有在战区才绘制丢弃按钮
                if self.zone == "warzone":
                    drop_rect = pygame.Rect(x + slot_size - 20, y + 5, 15, 15)
                    pygame.draw.rect(self.screen, (200, 0, 0), drop_rect)
                    drop_text = self.small_font.render("X", True, (255, 255, 255))
                    self.screen.blit(drop_text, (x + slot_size - 18, y + 3))
                    self.drop_rects.append((drop_rect, i))

        tip_text = self.small_font.render("Click on item to use (health) | Click X to drop", True, (255, 255, 255))
        tip_rect = tip_text.get_rect(center=(settings.SCREEN_WIDTH//2, start_y + slot_size + 30))
        self.screen.blit(tip_text, tip_rect)

    def handle_inventory_click(self, pos):
        # 丢弃按钮
        for drop_rect, idx in self.drop_rects:
            if drop_rect.collidepoint(pos):
                slot_item = self.player.inventory[idx]
                if slot_item and self.player.remove_item_from_inventory(idx, 1):
                    offset_x = random.randint(60, 120) * random.choice([-1, 1])
                    offset_y = random.randint(60, 120) * random.choice([-1, 1])
                    drop_x = self.player.rect.centerx + offset_x
                    drop_y = self.player.rect.centery + offset_y
                    drop_x = max(0, min(drop_x, settings.WORLD_WIDTH))
                    drop_y = max(0, min(drop_y, settings.WORLD_HEIGHT))
                    if slot_item.name == "health":
                        health_pack = HealthPack(self.player.rect.centerx, self.player.rect.centery, target_pos=(drop_x, drop_y))
                        self.health_packs.add(health_pack)
                        self.all_sprites.add(health_pack)
                        self.record_item_spawn(health_pack)
                    self.save_game_data()
                return
        # 使用物品
        for i, rect in enumerate(self.slot_rects):
            if rect.collidepoint(pos):
                item = self.player.inventory[i]
                if item and item.name == "health":
                    if self.player.use_health_item_at_index(i):
                        screen_pos = self.camera.apply_offset((self.player.rect.centerx, self.player.rect.top - 20))
                        self.add_floating_text("+1", screen_pos[0], screen_pos[1], (255, 100, 100))
                        self.save_game_data()
                break

    def _close_bank_ui(self):
        """关闭银行UI并设置冷却"""
        self.bank_ui_open = False
        self.bank_cooldown = settings.ZONE_SWITCH_COOLDOWN
        self.bank_page = "home"
        self.bank_input = ""
        self.bank_input_active = False
        self.bank_message = ""
        self.bank_message_timer = 0.0

    def _confirm_bank_input(self):
        """确认银行输入框的值，执行存款或取款"""
        if not self.bank_input:
            return
        amount = int(self.bank_input)
        if amount <= 0:
            self.bank_message = "Invalid amount"
            self.bank_message_timer = 2.0
            self.bank_input = ""
            return

        if self.bank_page == "deposit":
            if amount > self.player.gold:
                self.bank_message = "Insufficient gold"
                self.bank_message_timer = 2.0
            else:
                self.player.deposit_gold(amount)
                self.gold = self.player.gold
                self.save_game_data()
                self.bank_message = f"Deposited {amount} gold"
                self.bank_message_timer = 2.0
        elif self.bank_page == "withdraw":
            if amount > self.player.bank_gold:
                self.bank_message = "Insufficient bank balance"
                self.bank_message_timer = 2.0
            else:
                self.player.withdraw_gold(amount)
                self.gold = self.player.gold
                self.save_game_data()
                self.bank_message = f"Withdrew {amount} gold"
                self.bank_message_timer = 2.0

        self.bank_input = ""
        self.bank_input_active = False

    def draw_bank_ui(self):
        # 半透明背景
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        cx = settings.SCREEN_WIDTH // 2

        # 标题
        title_text = self.font.render("Bank", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(cx, 120))
        self.screen.blit(title_text, title_rect)

        # 随身金币显示
        pocket_text = self.small_font.render(f"Pocket: {self.player.gold}", True, (255, 215, 0))
        pocket_rect = pocket_text.get_rect(center=(cx, 170))
        self.screen.blit(pocket_text, pocket_rect)

        self.bank_ui_buttons = []

        if self.bank_page == "home":
            # 三个功能按钮
            btn_w, btn_h = 200, 50
            btn_x = cx - btn_w // 2

            # Balance 按钮
            balance_btn = pygame.Rect(btn_x, 250, btn_w, btn_h)
            pygame.draw.rect(self.screen, (60, 60, 140), balance_btn)
            pygame.draw.rect(self.screen, (255, 255, 255), balance_btn, 2)
            balance_text = self.small_font.render("Balance", True, (255, 255, 255))
            bt_rect = balance_text.get_rect(center=balance_btn.center)
            self.screen.blit(balance_text, bt_rect)

            # Deposit 按钮
            deposit_btn = pygame.Rect(btn_x, 320, btn_w, btn_h)
            pygame.draw.rect(self.screen, (0, 100, 0), deposit_btn)
            pygame.draw.rect(self.screen, (255, 255, 255), deposit_btn, 2)
            deposit_text = self.small_font.render("Deposit", True, (255, 255, 255))
            dt_rect = deposit_text.get_rect(center=deposit_btn.center)
            self.screen.blit(deposit_text, dt_rect)

            # Withdrawal 按钮
            withdraw_btn = pygame.Rect(btn_x, 390, btn_w, btn_h)
            pygame.draw.rect(self.screen, (140, 60, 0), withdraw_btn)
            pygame.draw.rect(self.screen, (255, 255, 255), withdraw_btn, 2)
            withdraw_text = self.small_font.render("Withdrawal", True, (255, 255, 255))
            wt_rect = withdraw_text.get_rect(center=withdraw_btn.center)
            self.screen.blit(withdraw_text, wt_rect)

            self.bank_ui_buttons = [
                ("balance", balance_btn),
                ("deposit", deposit_btn),
                ("withdraw", withdraw_btn),
            ]

            # 提示
            tip = self.small_font.render("ESC: Close", True, (180, 180, 180))
            tip_rect = tip.get_rect(center=(cx, 470))
            self.screen.blit(tip, tip_rect)

        elif self.bank_page == "balance":
            # 余额显示
            balance_label = self.font.render(f"{self.player.bank_gold}", True, (150, 150, 255))
            bl_rect = balance_label.get_rect(center=(cx, 280))
            self.screen.blit(balance_label, bl_rect)

            unit_text = self.small_font.render("gold in bank", True, (180, 180, 180))
            ut_rect = unit_text.get_rect(center=(cx, 330))
            self.screen.blit(unit_text, ut_rect)

            # 返回按钮
            back_btn = pygame.Rect(cx - 80, 400, 160, 45)
            pygame.draw.rect(self.screen, (80, 80, 80), back_btn)
            pygame.draw.rect(self.screen, (255, 255, 255), back_btn, 2)
            back_text = self.small_font.render("Back", True, (255, 255, 255))
            bkt_rect = back_text.get_rect(center=back_btn.center)
            self.screen.blit(back_text, bkt_rect)
            self.bank_ui_buttons = [("back", back_btn)]

        elif self.bank_page in ("deposit", "withdraw"):
            page_title = "Deposit" if self.bank_page == "deposit" else "Withdrawal"
            page_color = (0, 180, 0) if self.bank_page == "deposit" else (180, 80, 0)

            pt = self.font.render(page_title, True, page_color)
            pt_rect = pt.get_rect(center=(cx, 230))
            self.screen.blit(pt, pt_rect)

            # 输入框
            input_w, input_h = 240, 45
            input_rect = pygame.Rect(cx - input_w // 2, 290, input_w, input_h)
            border_color = (255, 255, 100) if self.bank_input_active else (180, 180, 180)
            pygame.draw.rect(self.screen, (40, 40, 40), input_rect)
            pygame.draw.rect(self.screen, border_color, input_rect, 2)

            # 输入框文字
            display_text = self.bank_input if self.bank_input else "0"
            if self.bank_input_active and pygame.time.get_ticks() % 1000 < 500:
                display_text += "|"
            input_surf = self.small_font.render(display_text, True, (255, 255, 255))
            is_rect = input_surf.get_rect(midleft=(input_rect.x + 10, input_rect.centery))
            self.screen.blit(input_surf, is_rect)

            # 点击输入框激活
            self.bank_ui_buttons = [("input_field", input_rect)]

            # 确定按钮
            confirm_btn = pygame.Rect(cx - 80, 355, 160, 40)
            pygame.draw.rect(self.screen, page_color, confirm_btn)
            pygame.draw.rect(self.screen, (255, 255, 255), confirm_btn, 2)
            confirm_text = self.small_font.render("Confirm", True, (255, 255, 255))
            ct_rect = confirm_text.get_rect(center=confirm_btn.center)
            self.screen.blit(confirm_text, ct_rect)
            self.bank_ui_buttons.append(("confirm", confirm_btn))

            # 存款页专属：Deposit All 按钮
            if self.bank_page == "deposit":
                deposit_all_btn = pygame.Rect(cx - 100, 405, 200, 40)
                pygame.draw.rect(self.screen, (0, 60, 0), deposit_all_btn)
                pygame.draw.rect(self.screen, (255, 255, 255), deposit_all_btn, 2)
                deposit_all_text = self.small_font.render("Deposit All", True, (255, 255, 255))
                da_rect = deposit_all_text.get_rect(center=deposit_all_btn.center)
                self.screen.blit(deposit_all_text, da_rect)
                self.bank_ui_buttons.append(("deposit_all", deposit_all_btn))

            # 返回按钮
            back_y = 455 if self.bank_page == "deposit" else 405
            back_btn = pygame.Rect(cx - 80, back_y, 160, 40)
            pygame.draw.rect(self.screen, (80, 80, 80), back_btn)
            pygame.draw.rect(self.screen, (255, 255, 255), back_btn, 2)
            back_text = self.small_font.render("Back", True, (255, 255, 255))
            bkt_rect = back_text.get_rect(center=back_btn.center)
            self.screen.blit(back_text, bkt_rect)
            self.bank_ui_buttons.append(("back", back_btn))

            # 操作结果消息
            if self.bank_message:
                msg_color = (100, 255, 100) if "Deposited" in self.bank_message or "Withdrew" in self.bank_message else (255, 100, 100)
                msg_surf = self.small_font.render(self.bank_message, True, msg_color)
                msg_y = back_y + 55
                msg_rect = msg_surf.get_rect(center=(cx, msg_y))
                self.screen.blit(msg_surf, msg_rect)

            # 提示
            tip = self.small_font.render("Type amount, Enter to confirm", True, (180, 180, 180))
            tip_y = back_y + 95
            tip_rect = tip.get_rect(center=(cx, tip_y))
            self.screen.blit(tip, tip_rect)

    def handle_bank_click(self, pos):
        for action, rect in self.bank_ui_buttons:
            if rect.collidepoint(pos):
                if action == "balance":
                    self.bank_page = "balance"
                elif action == "deposit":
                    self.bank_page = "deposit"
                    self.bank_input = ""
                    self.bank_input_active = True
                    self.bank_message = ""
                elif action == "withdraw":
                    self.bank_page = "withdraw"
                    self.bank_input = ""
                    self.bank_input_active = True
                    self.bank_message = ""
                elif action == "back":
                    self.bank_page = "home"
                    self.bank_input = ""
                    self.bank_input_active = False
                    self.bank_message = ""
                elif action == "input_field":
                    self.bank_input_active = True
                elif action == "confirm":
                    self._confirm_bank_input()
                elif action == "deposit_all":
                    if self.player.gold > 0:
                        amount = self.player.gold
                        self.player.deposit_gold(amount)
                        self.gold = self.player.gold
                        self.save_game_data()
                        self.bank_message = f"Deposited {amount} gold"
                        self.bank_message_timer = 2.0
                    else:
                        self.bank_message = "No gold to deposit"
                        self.bank_message_timer = 2.0
                break

    def draw_death_screen(self):
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        death_text = self.font.render("YOU DIED", True, (255, 0, 0))
        text_rect = death_text.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 - 80))
        self.screen.blit(death_text, text_rect)

        loss_text = self.small_font.render(f"You lost {self.gold_loss} gold", True, (255, 215, 0))
        loss_rect = loss_text.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 - 30))
        self.screen.blit(loss_text, loss_rect)

        restart_text = self.small_font.render("Press SPACE to restart", True, (255, 255, 255))
        restart_rect = restart_text.get_rect(center=(settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 + 20))
        self.screen.blit(restart_text, restart_rect)