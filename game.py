import sys
import math
from collections import deque
from enum import Enum
from dataclasses import dataclass

import pygame

# ─────────────────────────────────────────────────────────────────────────────
# Layout constants
# ─────────────────────────────────────────────────────────────────────────────
WIN_W, WIN_H    = 1100, 700
PANEL_W         = 550
TILE_SIZE       = 110
GRID_COLS = GRID_ROWS = 3
GRID_PX         = TILE_SIZE * GRID_COLS       # 330
GRID_X          = (PANEL_W - GRID_PX) // 2   # 110
GRID_Y          = 160                          # grid top-y in left panel

# Animation tuning
MOVE_SPEED      = TILE_SIZE / 0.32   # px / s  →  full tile in 0.32 s
PAUSE_DURATION  = 0.18               # s  for non-move action pause

CURSOR_BLINK_MS = 530
GROWTH_TURNS    = 3

# ─────────────────────────────────────────────────────────────────────────────
# Cozy warm pixel-art palette
# ─────────────────────────────────────────────────────────────────────────────

# Environment
C_SKY           = (148, 193, 228)
C_GRASS         = ( 88, 132,  68)
C_GRASS_DK      = ( 70, 108,  52)
C_GRASS_LT      = (108, 155,  82)

# Soil / tiles
C_SOIL          = ( 96,  66,  42)
C_SOIL_LT       = (118,  86,  58)
C_SOIL_DK       = ( 68,  46,  26)
C_TILE_BDR      = ( 55,  38,  20)
C_FARM_BORDER   = (130, 100,  60)

# Plants
C_STEM          = ( 76, 136,  46)
C_STEM_LT       = ( 98, 162,  60)
C_LEAF          = ( 92, 156,  54)
C_LEAF_DK       = ( 65, 120,  36)
C_WHEAT         = (200, 168,  54)
C_WHEAT_LT      = (224, 196,  80)
C_SEED          = (140, 105,  64)
C_SEED_DK       = (108,  78,  44)

# Obstacle / stone
C_STONE         = ( 86,  80,  72)
C_STONE_DK      = ( 62,  56,  50)
C_STONE_LT      = (110, 103,  94)

# Robot
C_BOT_BODY      = (210, 158,  70)
C_BOT_DARK      = (158, 112,  44)
C_BOT_FACE      = (238, 214, 152)
C_BOT_EYE       = ( 44,  28,  12)
C_BOT_LED       = (255, 116,  50)

# Right panel wood
C_WOOD_BG       = ( 42,  28,  16)
C_WOOD_PLANK    = ( 50,  34,  20)
C_WOOD_GRAIN    = ( 34,  22,  10)
C_WOOD_LT       = ( 66,  48,  28)
C_DIVIDER       = ( 52,  36,  18)

# Editor (parchment)
C_PARCHMENT     = (220, 202, 168)
C_PARCH_DK      = (204, 184, 148)
C_PARCH_LINE    = (208, 190, 155)
C_INK           = ( 50,  33,  15)
C_CURSOR_AMB    = (175, 108,  36)
C_EDITOR_BDR    = ( 90,  64,  36)

# Console
C_CON_BG        = ( 24,  15,   8)
C_CON_WHT       = (200, 182, 148)
C_CON_RED       = (215,  86,  66)
C_CON_GRN       = (110, 192,  80)
C_CON_YLW       = (216, 186,  70)
C_CON_GRY       = (140, 124, 100)

# Run button
C_BTN_WOOD      = (112,  72,  34)
C_BTN_LT        = (145, 100,  54)
C_BTN_DK        = ( 70,  40,  16)
C_BTN_DIS       = ( 66,  46,  26)
C_BTN_TXT       = (244, 222, 170)
C_BTN_DIS_TXT   = ( 92,  70,  46)

# UI labels
C_GOLD          = (222, 185,  74)
C_WARM_WHT      = (238, 222, 194)
C_WARM_GRY      = (152, 136, 108)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def tile_center(r: int, c: int) -> tuple:
    return (GRID_X + c * TILE_SIZE + TILE_SIZE // 2,
            GRID_Y + r * TILE_SIZE + TILE_SIZE // 2)

# ─────────────────────────────────────────────────────────────────────────────
# Enums & data classes  (game logic — unchanged)
# ─────────────────────────────────────────────────────────────────────────────
class TileState(Enum):
    EMPTY    = "empty"
    PLANTED  = "planted"
    READY    = "ready"
    OBSTACLE = "obstacle"

class Direction(Enum):
    RIGHT = (0,  1)
    DOWN  = (1,  0)
    LEFT  = (0, -1)
    UP    = (-1, 0)

DIR_ORDER = [Direction.RIGHT, Direction.DOWN, Direction.LEFT, Direction.UP]

@dataclass
class Tile:
    state: TileState = TileState.EMPTY
    growth_turns: int = 0

# ─────────────────────────────────────────────────────────────────────────────
# Grid  (game logic — unchanged)
# ─────────────────────────────────────────────────────────────────────────────
class Grid:
    def __init__(self):
        self.cells = [[Tile() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]

    def get(self, r, c) -> Tile:
        return self.cells[r][c]

    def tick(self):
        for row in self.cells:
            for tile in row:
                if tile.state == TileState.PLANTED:
                    tile.growth_turns -= 1
                    if tile.growth_turns <= 0:
                        tile.state = TileState.READY

# ─────────────────────────────────────────────────────────────────────────────
# Robot  (pixel position added for smooth animation)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Robot:
    row: int = 0
    col: int = 0
    direction: Direction = Direction.RIGHT
    # visual pixel position (updated every frame)
    px: float = 0.0
    py: float = 0.0
    target_px: float = 0.0
    target_py: float = 0.0

    def init_pos(self):
        cx, cy = tile_center(self.row, self.col)
        self.px = self.target_px = float(cx)
        self.py = self.target_py = float(cy)

    def set_target(self, r: int, c: int):
        cx, cy = tile_center(r, c)
        self.target_px = float(cx)
        self.target_py = float(cy)

# ─────────────────────────────────────────────────────────────────────────────
# GameState  (animation state machine replaces old last_tick approach)
# ─────────────────────────────────────────────────────────────────────────────
class GameState:
    def __init__(self):
        self.grid  = Grid()
        self.robot = Robot()
        self.robot.init_pos()
        self.points = 0
        self.action_queue: deque = deque()
        # execution state
        self.running     = False   # True while draining queue
        self.animating   = False   # True during a command's animation window
        self.anim_is_move = False  # True if current animation is a robot move
        self.anim_timer  = 0.0    # seconds elapsed in current pause
        self.console_msgs: list = []

    def log(self, msg, color=C_CON_WHT):
        self.console_msgs.append((msg, color))
        if len(self.console_msgs) > 60:
            self.console_msgs.pop(0)

    def _start_move(self):
        self.animating    = True
        self.anim_is_move = True

    def _start_pause(self):
        self.animating    = True
        self.anim_is_move = False
        self.anim_timer   = 0.0

    def dispatch(self, action: str):
        robot = self.robot
        grid  = self.grid
        r, c  = robot.row, robot.col
        dr, dc = robot.direction.value

        if action == 'move':
            nr, nc = r + dr, c + dc
            if not (0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS):
                self.log("move(): hit boundary — can't move there.", C_CON_RED)
                self._start_pause()
            elif grid.get(nr, nc).state == TileState.OBSTACLE:
                self.log("move(): obstacle in the way.", C_CON_RED)
                self._start_pause()
            else:
                robot.row, robot.col = nr, nc
                robot.set_target(nr, nc)
                self._start_move()
            grid.tick()

        elif action == 'turn_left':
            idx = DIR_ORDER.index(robot.direction)
            robot.direction = DIR_ORDER[(idx - 1) % 4]
            grid.tick()
            self._start_pause()

        elif action == 'turn_right':
            idx = DIR_ORDER.index(robot.direction)
            robot.direction = DIR_ORDER[(idx + 1) % 4]
            grid.tick()
            self._start_pause()

        elif action == 'plant':
            tile = grid.get(r, c)
            if tile.state == TileState.EMPTY:
                tile.state = TileState.PLANTED
                tile.growth_turns = GROWTH_TURNS
                self.log(f"Planted at ({r},{c}). Grows in {GROWTH_TURNS} turns.", C_CON_YLW)
            else:
                self.log(f"plant(): tile ({r},{c}) is not empty soil.", C_CON_RED)
            grid.tick()
            self._start_pause()

        elif action == 'harvest':
            tile = grid.get(r, c)
            if tile.state == TileState.READY:
                tile.state = TileState.EMPTY
                tile.growth_turns = 0
                self.points += 10
                self.log(f"Harvested at ({r},{c})! +10 pts  (total: {self.points})", C_CON_GRN)
            else:
                self.log(f"harvest(): tile ({r},{c}) not ready to harvest.", C_CON_RED)
            grid.tick()
            self._start_pause()

        elif action == 'wait':
            grid.tick()
            self._start_pause()

# ─────────────────────────────────────────────────────────────────────────────
# Sandbox executor  (game logic — unchanged)
# ─────────────────────────────────────────────────────────────────────────────
def build_sandbox(queue: deque) -> dict:
    def move():       queue.append('move')
    def turn_left():  queue.append('turn_left')
    def turn_right(): queue.append('turn_right')
    def plant():      queue.append('plant')
    def harvest():    queue.append('harvest')
    def wait():       queue.append('wait')
    return {
        'move': move, 'turn_left': turn_left, 'turn_right': turn_right,
        'plant': plant, 'harvest': harvest, 'wait': wait,
        '__builtins__': {},
    }

def run_player_code(code: str, state: GameState):
    state.action_queue.clear()
    state.animating = False
    sandbox = build_sandbox(state.action_queue)
    try:
        exec(compile(code, '<editor>', 'exec'), sandbox)
    except SyntaxError as e:
        state.log(f"SyntaxError: {e.msg} (line {e.lineno})", C_CON_RED)
        state.action_queue.clear()
        return
    except Exception as e:
        state.log(f"Error: {e}", C_CON_RED)
        state.action_queue.clear()
        return
    if state.action_queue:
        state.running = True
        state.log(f"Running {len(state.action_queue)} command(s)…", C_CON_GRY)
    else:
        state.log("No commands queued.", C_CON_GRY)

# ─────────────────────────────────────────────────────────────────────────────
# Editor Component
# ─────────────────────────────────────────────────────────────────────────────
class EditorComponent:
    def __init__(self, rect: pygame.Rect, font: pygame.font.Font):
        self.rect   = rect
        self.font   = font
        self.lines  = [""]
        self.cursor_line = 0
        self.cursor_col  = 0
        self.scroll_offset = 0
        self.focused = True

    @property
    def text(self):
        return "\n".join(self.lines)

    def _clamp_cursor(self):
        self.cursor_line = max(0, min(self.cursor_line, len(self.lines) - 1))
        self.cursor_col  = max(0, min(self.cursor_col, len(self.lines[self.cursor_line])))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        key  = event.key
        mod  = event.mod
        ctrl = mod & pygame.KMOD_CTRL

        if ctrl and key == pygame.K_a:
            self.cursor_col = 0; return
        if ctrl and key == pygame.K_e:
            self.cursor_col = len(self.lines[self.cursor_line]); return

        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            line = self.lines[self.cursor_line]
            self.lines[self.cursor_line] = line[:self.cursor_col]
            self.lines.insert(self.cursor_line + 1, line[self.cursor_col:])
            self.cursor_line += 1
            self.cursor_col = 0

        elif key == pygame.K_BACKSPACE:
            if self.cursor_col > 0:
                line = self.lines[self.cursor_line]
                self.lines[self.cursor_line] = line[:self.cursor_col-1] + line[self.cursor_col:]
                self.cursor_col -= 1
            elif self.cursor_line > 0:
                prev = self.lines[self.cursor_line - 1]
                self.cursor_col = len(prev)
                self.lines[self.cursor_line - 1] = prev + self.lines[self.cursor_line]
                self.lines.pop(self.cursor_line)
                self.cursor_line -= 1

        elif key == pygame.K_DELETE:
            line = self.lines[self.cursor_line]
            if self.cursor_col < len(line):
                self.lines[self.cursor_line] = line[:self.cursor_col] + line[self.cursor_col+1:]
            elif self.cursor_line < len(self.lines) - 1:
                self.lines[self.cursor_line] += self.lines.pop(self.cursor_line + 1)

        elif key == pygame.K_LEFT:
            if self.cursor_col > 0:
                self.cursor_col -= 1
            elif self.cursor_line > 0:
                self.cursor_line -= 1
                self.cursor_col = len(self.lines[self.cursor_line])

        elif key == pygame.K_RIGHT:
            if self.cursor_col < len(self.lines[self.cursor_line]):
                self.cursor_col += 1
            elif self.cursor_line < len(self.lines) - 1:
                self.cursor_line += 1
                self.cursor_col = 0

        elif key == pygame.K_UP:
            if self.cursor_line > 0:
                self.cursor_line -= 1
                self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_line]))

        elif key == pygame.K_DOWN:
            if self.cursor_line < len(self.lines) - 1:
                self.cursor_line += 1
                self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_line]))

        elif key == pygame.K_HOME:
            self.cursor_col = 0

        elif key == pygame.K_END:
            self.cursor_col = len(self.lines[self.cursor_line])

        elif event.unicode and event.unicode.isprintable():
            line = self.lines[self.cursor_line]
            self.lines[self.cursor_line] = (line[:self.cursor_col]
                                            + event.unicode
                                            + line[self.cursor_col:])
            self.cursor_col += 1

        self._clamp_cursor()
        line_h = self.font.get_linesize()
        vis    = (self.rect.height - 12) // line_h
        if self.cursor_line < self.scroll_offset:
            self.scroll_offset = self.cursor_line
        elif self.cursor_line >= self.scroll_offset + vis:
            self.scroll_offset = self.cursor_line - vis + 1

    def draw(self, surf: pygame.Surface):
        # Parchment background
        pygame.draw.rect(surf, C_PARCHMENT, self.rect)
        # Faint lined-paper lines
        line_h = self.font.get_linesize()
        pad = 8
        vis_lines = (self.rect.height - pad * 2) // line_h
        for i in range(vis_lines + 1):
            ly = self.rect.y + pad + i * line_h + line_h - 2
            if ly < self.rect.bottom - 2:
                pygame.draw.line(surf, C_PARCH_LINE,
                                 (self.rect.x + 4, ly), (self.rect.right - 4, ly), 1)
        # Slightly darker left margin strip
        pygame.draw.rect(surf, C_PARCH_DK,
                         (self.rect.x, self.rect.y, 28, self.rect.height))
        pygame.draw.line(surf, C_EDITOR_BDR,
                         (self.rect.x + 28, self.rect.y),
                         (self.rect.x + 28, self.rect.bottom), 1)

        # Text
        for i in range(vis_lines):
            li = i + self.scroll_offset
            if li >= len(self.lines):
                break
            # Line number in margin
            num_surf = self.font.render(str(li + 1), True, C_WARM_GRY)
            surf.blit(num_surf, (self.rect.x + 4, self.rect.y + pad + i * line_h))
            # Code text
            txt_surf = self.font.render(self.lines[li], True, C_INK)
            surf.blit(txt_surf, (self.rect.x + 34, self.rect.y + pad + i * line_h))

        # Cursor
        show_cursor = (pygame.time.get_ticks() // CURSOR_BLINK_MS) % 2 == 0
        if self.focused and show_cursor:
            vis_li = self.cursor_line - self.scroll_offset
            if 0 <= vis_li < vis_lines:
                partial = self.lines[self.cursor_line][:self.cursor_col]
                cx = self.rect.x + 34 + self.font.size(partial)[0]
                cy = self.rect.y + pad + vis_li * line_h
                pygame.draw.line(surf, C_CURSOR_AMB, (cx, cy), (cx, cy + line_h - 2), 2)

        # Border (outer frame — wood color)
        pygame.draw.rect(surf, C_EDITOR_BDR, self.rect, 2)

# ─────────────────────────────────────────────────────────────────────────────
# Console Component
# ─────────────────────────────────────────────────────────────────────────────
class ConsoleComponent:
    def __init__(self, rect: pygame.Rect, font: pygame.font.Font):
        self.rect = rect
        self.font = font

    def draw(self, surf: pygame.Surface, msgs: list):
        pygame.draw.rect(surf, C_CON_BG, self.rect)
        pygame.draw.rect(surf, C_EDITOR_BDR, self.rect, 2)
        line_h = self.font.get_linesize()
        pad    = 7
        vis    = (self.rect.height - pad * 2) // line_h
        start  = max(0, len(msgs) - vis)
        for i, (text, color) in enumerate(msgs[start:]):
            ts = self.font.render(text, True, color)
            surf.blit(ts, (self.rect.x + pad, self.rect.y + pad + i * line_h))

# ─────────────────────────────────────────────────────────────────────────────
# Renderer  (full pixel-art visual overhaul)
# ─────────────────────────────────────────────────────────────────────────────
class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen     = screen
        self.font_mono  = pygame.font.SysFont("monospace", 14)
        self.font_ui    = pygame.font.SysFont("sans", 15, bold=True)
        self.font_big   = pygame.font.SysFont("sans", 24, bold=True)
        self.font_label = pygame.font.SysFont("monospace", 13)
        # Precompute soil dot patterns (deterministic per tile)
        self._soil_dots = {
            (r, c): self._gen_dots(r, c)
            for r in range(GRID_ROWS) for c in range(GRID_COLS)
        }

    @staticmethod
    def _gen_dots(r, c):
        dots = []
        h = r * 0x6B + c * 0xA3 + 0xFF
        for _ in range(9):
            h = (h * 0x41C6 + 0x3039) & 0xFFFF
            dx = 7 + h % 88
            h = (h * 0x41C6 + 0x3039) & 0xFFFF
            dy = 7 + h % 88
            h = (h * 0x41C6 + 0x3039) & 0xFFFF
            col = C_SOIL_LT if h % 3 != 0 else C_SOIL_DK
            dots.append((dx, dy, col))
        return dots

    # ── tile sprites ─────────────────────────────────────────────────────────

    def _draw_soil_base(self, px, py, r, c):
        s = self.screen
        inner = pygame.Rect(px + 3, py + 3, TILE_SIZE - 6, TILE_SIZE - 6)
        pygame.draw.rect(s, C_SOIL, inner)
        for dx, dy, col in self._soil_dots[(r, c)]:
            pygame.draw.rect(s, col, (px + dx, py + dy, 3, 3))

    def _draw_sprout(self, px, py):
        s  = self.screen
        cx = px + TILE_SIZE // 2
        # stem
        pygame.draw.rect(s, C_STEM,    (cx - 1, py + 48, 2, 38))
        pygame.draw.rect(s, C_STEM_LT, (cx,     py + 50, 1, 34))
        # left leaf
        pygame.draw.rect(s, C_LEAF,    (cx - 11, py + 56, 10, 5))
        pygame.draw.rect(s, C_LEAF_DK, (cx - 11, py + 60, 10, 2))
        # right leaf
        pygame.draw.rect(s, C_LEAF,    (cx + 1,  py + 64, 10, 5))
        pygame.draw.rect(s, C_LEAF_DK, (cx + 1,  py + 68, 10, 2))

    def _draw_crop(self, px, py):
        s  = self.screen
        cx = px + TILE_SIZE // 2
        # tall stem
        pygame.draw.rect(s, C_STEM,    (cx - 1, py + 30, 2, 58))
        pygame.draw.rect(s, C_STEM_LT, (cx,     py + 32, 1, 54))
        # alternating leaves
        for i, (side, row_y) in enumerate([(-12, 50), (2, 60), (-12, 70)]):
            pygame.draw.rect(s, C_LEAF if i % 2 == 0 else C_LEAF_DK,
                             (cx + side, py + row_y, 11, 5))
            pygame.draw.rect(s, C_LEAF_DK if i % 2 == 0 else C_LEAF,
                             (cx + side, py + row_y + 4, 11, 2))
        # wheat head (3 stalks)
        for ox in (-4, 0, 4):
            pygame.draw.rect(s, C_WHEAT,    (cx + ox - 1, py + 30, 3, 9))
            pygame.draw.rect(s, C_WHEAT_LT, (cx + ox,     py + 30, 2, 4))

    def _draw_growth_pips(self, px, py, tile: Tile):
        turns_done = GROWTH_TURNS - tile.growth_turns
        for i in range(3):
            col = C_STEM if i < turns_done else C_SOIL_DK
            pygame.draw.rect(self.screen, col,
                             (px + 8 + i * 9, py + TILE_SIZE - 14, 6, 6))

    def _draw_obstacle(self, px, py, r, c):
        s = self.screen
        inner = pygame.Rect(px + 3, py + 3, TILE_SIZE - 6, TILE_SIZE - 6)
        pygame.draw.rect(s, C_STONE, inner)
        seed = r * 23 + c * 41 + 7
        for i in range(4):
            sx = px + 12 + ((seed * (i + 1) * 17) % 70)
            sy = py + 12 + ((seed * (i + 1) * 11) % 70)
            sw = 14 + ((seed * i * 7) % 18)
            sh = 10 + ((seed * i * 5) % 14)
            pygame.draw.rect(s, C_STONE_DK, (sx, sy, sw, sh))
            pygame.draw.rect(s, C_STONE_LT, (sx, sy, sw, 2))
            pygame.draw.rect(s, C_STONE_LT, (sx, sy, 2, sh))

    def draw_tile(self, tile: Tile, px, py, r, c):
        s = self.screen
        if tile.state == TileState.OBSTACLE:
            self._draw_obstacle(px, py, r, c)
        else:
            self._draw_soil_base(px, py, r, c)
            if tile.state == TileState.PLANTED:
                self._draw_sprout(px, py)
                self._draw_growth_pips(px, py, tile)
            elif tile.state == TileState.READY:
                self._draw_crop(px, py)
        # tile border
        pygame.draw.rect(s, C_TILE_BDR,
                         (px + 3, py + 3, TILE_SIZE - 6, TILE_SIZE - 6), 2)

    # ── robot ────────────────────────────────────────────────────────────────

    def draw_robot(self, robot: Robot, anim_is_move: bool):
        s  = self.screen
        # bounce: bob up slightly at mid-move
        cy_off = 0
        if anim_is_move:
            dist  = math.hypot(robot.target_px - robot.px,
                               robot.target_py - robot.py)
            prog  = max(0.0, 1.0 - dist / TILE_SIZE)
            cy_off = int(-math.sin(prog * math.pi) * 5)

        cx = int(robot.px)
        cy = int(robot.py) + cy_off

        # shadow
        pygame.draw.rect(s, C_BOT_DARK,
                         (cx - 13, cy - 13 + 4, 26, 26), border_radius=3)
        # body
        pygame.draw.rect(s, C_BOT_BODY,
                         (cx - 13, cy - 13, 26, 26), border_radius=3)
        # right-side / bottom shading
        pygame.draw.rect(s, C_BOT_DARK, (cx + 10, cy - 13, 3, 26))
        pygame.draw.rect(s, C_BOT_DARK, (cx - 13, cy + 10, 26, 3))

        # face panel + eyes by direction
        d = robot.direction
        if d == Direction.RIGHT:
            fp = (cx + 4, cy - 7, 9, 14)
            e1 = (cx + 6, cy - 4)
            e2 = (cx + 6, cy + 2)
        elif d == Direction.LEFT:
            fp = (cx - 13, cy - 7, 9, 14)
            e1 = (cx - 10, cy - 4)
            e2 = (cx - 10, cy + 2)
        elif d == Direction.DOWN:
            fp = (cx - 7, cy + 4, 14, 9)
            e1 = (cx - 4, cy + 6)
            e2 = (cx + 2, cy + 6)
        else:  # UP
            fp = (cx - 7, cy - 13, 14, 9)
            e1 = (cx - 4, cy - 10)
            e2 = (cx + 2, cy - 10)

        pygame.draw.rect(s, C_BOT_FACE, fp)
        pygame.draw.rect(s, C_BOT_EYE, (*e1, 3, 3))
        pygame.draw.rect(s, C_BOT_EYE, (*e2, 3, 3))

        # LED dot (top-right of body)
        pygame.draw.rect(s, C_BOT_LED, (cx + 7, cy - 12, 4, 4))

    # ── environment ──────────────────────────────────────────────────────────

    def _draw_left_bg(self):
        s = self.screen
        # Sky fill
        s.fill(C_SKY, (0, 0, PANEL_W, WIN_H))

        # Grass strip at bottom
        s.fill(C_GRASS, (0, WIN_H - 48, PANEL_W, 48))
        s.fill(C_GRASS_DK, (0, WIN_H - 48, PANEL_W, 4))
        # grass pixel bumps along seam
        for i in range(0, PANEL_W, 14):
            pygame.draw.rect(s, C_GRASS_LT, (i, WIN_H - 50, 5, 5))
            pygame.draw.rect(s, C_GRASS,    (i + 7, WIN_H - 52, 4, 5))

        # Farm border frame (slightly larger than grid)
        fm = 14
        farm = pygame.Rect(GRID_X - fm, GRID_Y - fm,
                           GRID_PX + fm * 2, GRID_PX + fm * 2)
        pygame.draw.rect(s, C_FARM_BORDER, farm, border_radius=4)
        # inner shadow
        farm2 = pygame.Rect(farm.x + 3, farm.y + 3, farm.w - 6, farm.h - 6)
        pygame.draw.rect(s, C_TILE_BDR, farm2, 2, border_radius=2)

    def _draw_wood_panel(self):
        s = self.screen
        pygame.draw.rect(s, C_WOOD_BG, (PANEL_W, 0, PANEL_W, WIN_H))
        # horizontal plank lines
        for y in range(0, WIN_H, 58):
            pygame.draw.line(s, C_WOOD_GRAIN, (PANEL_W, y), (WIN_W, y), 1)
            pygame.draw.line(s, C_WOOD_LT,    (PANEL_W, y + 1), (WIN_W, y + 1), 1)
        # panel divider
        pygame.draw.rect(s, C_DIVIDER, (PANEL_W, 0, 4, WIN_H))

    def _draw_run_button(self, btn: pygame.Rect, is_running: bool, hover: bool):
        s = self.screen
        if is_running:
            bg    = C_BTN_DIS
            txt_c = C_BTN_DIS_TXT
            label = "Running..."
        else:
            bg    = C_BTN_LT if hover else C_BTN_WOOD
            txt_c = C_BTN_TXT
            label = "Run  >"

        # shadow
        shd = pygame.Rect(btn.x + 3, btn.y + 3, btn.w, btn.h)
        pygame.draw.rect(s, C_BTN_DK, shd, border_radius=5)
        # main button body
        pygame.draw.rect(s, bg, btn, border_radius=5)
        # highlight top edge
        pygame.draw.line(s, C_BTN_LT,
                         (btn.x + 4, btn.y + 2), (btn.right - 4, btn.y + 2), 1)
        # border
        pygame.draw.rect(s, C_BTN_DK, btn, 2, border_radius=5)
        # label
        bl = self.font_ui.render(label, True, txt_c)
        s.blit(bl, (btn.x + (btn.w - bl.get_width())  // 2,
                    btn.y + (btn.h - bl.get_height()) // 2))

    # ── main draw call ────────────────────────────────────────────────────────

    def draw(self, state: GameState,
             editor: EditorComponent,
             console: ConsoleComponent,
             btn_rect: pygame.Rect,
             btn_hover: bool):
        s = self.screen

        # ── left panel ───────────────────────────────────────────────────────
        self._draw_left_bg()

        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                px = GRID_X + c * TILE_SIZE
                py = GRID_Y + r * TILE_SIZE
                self.draw_tile(state.grid.get(r, c), px, py, r, c)

        self.draw_robot(state.robot, state.anim_is_move and state.animating)

        # Title
        title = self.font_big.render("Farm Bot", True, C_GOLD)
        s.blit(title, (GRID_X, 18))
        # Points
        pts = self.font_ui.render(f"Points: {state.points}", True, C_WARM_WHT)
        s.blit(pts, (GRID_X, 52))

        # Command reference (bottom-left)
        ref_y = WIN_H - 150
        hdr = self.font_label.render("Commands:", True, C_WARM_GRY)
        s.blit(hdr, (GRID_X, ref_y))
        cmds = ["move()", "turn_left()", "turn_right()",
                "plant()", "harvest()", "wait()"]
        for i, cmd in enumerate(cmds):
            cs = self.font_label.render(cmd, True, C_CON_GRY)
            s.blit(cs, (GRID_X + 4, ref_y + 16 + i * 17))

        # ── right panel ──────────────────────────────────────────────────────
        self._draw_wood_panel()

        # Editor label
        el = self.font_ui.render("Code Editor", True, C_GOLD)
        s.blit(el, (editor.rect.x, editor.rect.y - 22))
        editor.draw(s)

        # Run button
        self._draw_run_button(btn_rect, state.running, btn_hover)

        # Console label
        cl = self.font_ui.render("Console", True, C_GOLD)
        s.blit(cl, (console.rect.x, console.rect.y - 22))
        console.draw(s, state.console_msgs)

# ─────────────────────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Farm Bot")
    clock = pygame.time.Clock()

    state    = GameState()
    renderer = Renderer(screen)

    RIGHT_X      = PANEL_W + 20
    editor_rect  = pygame.Rect(RIGHT_X, 40, PANEL_W - 40, 310)
    btn_rect     = pygame.Rect(RIGHT_X, 365, 130, 36)
    console_rect = pygame.Rect(RIGHT_X, 430, PANEL_W - 40, WIN_H - 450)

    editor  = EditorComponent(editor_rect, renderer.font_mono)
    console = ConsoleComponent(console_rect, renderer.font_mono)

    state.log("Welcome! Write commands and press Run.", C_CON_GRY)
    state.log("Commands: move()  turn_left()  turn_right()  plant()  harvest()  wait()", C_CON_GRY)

    game_running = True
    while game_running:
        dt  = clock.tick(60) / 1000.0   # delta time in seconds
        now = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()
        btn_hover = btn_rect.collidepoint(mouse_pos) and not state.running

        # ── events ──────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_hover:
                    run_player_code(editor.text, state)
                elif editor_rect.collidepoint(event.pos):
                    editor.focused = True
                else:
                    editor.focused = False

            elif event.type == pygame.KEYDOWN and editor.focused:
                editor.handle_event(event)

        # ── animation update (delta-time) ────────────────────────────────────
        robot = state.robot
        if state.running and state.animating:
            if state.anim_is_move:
                dx   = robot.target_px - robot.px
                dy   = robot.target_py - robot.py
                dist = math.hypot(dx, dy)
                if dist > 0.5:
                    step = min(dist, MOVE_SPEED * dt)
                    robot.px += (dx / dist) * step
                    robot.py += (dy / dist) * step
                else:
                    robot.px = robot.target_px
                    robot.py = robot.target_py
                    state.animating = False
            else:
                state.anim_timer += dt
                if state.anim_timer >= PAUSE_DURATION:
                    state.animating = False

        # ── dispatch next action when previous animation finishes ────────────
        if state.running and not state.animating:
            if state.action_queue:
                action = state.action_queue.popleft()
                state.dispatch(action)
            else:
                state.running = False
                state.log("Done.", C_CON_GRY)

        # ── draw ─────────────────────────────────────────────────────────────
        renderer.draw(state, editor, console, btn_rect, btn_hover)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
