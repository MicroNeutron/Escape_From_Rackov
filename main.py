# main.py
import os
os.environ['SDL_VIDEODRIVER'] = 'windib'

import pygame
from core.game import Game

def main():
    pygame.init()
    game = Game()
    game.run()
    pygame.quit()

if __name__ == "__main__":
    main()