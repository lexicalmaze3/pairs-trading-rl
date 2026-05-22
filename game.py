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

# Animation tuning (unchanged)
MOVE_SPEED      = TILE_SIZE / 0.32
PAUSE_DURATION  = 0.18

CURSOR_BLINK_MS = 530

# Shop panel dimensions
SHOP_W, SHOP_H  = 660, 500
SHOP_X          = (WIN_W - SHOP_W) // 2   # 220
SHOP_Y          = (WIN_H - SHOP_H) // 2   # 100

# ─────────────────────────────────────────────────────────────────────────────
# Colour palette  (cozy warm pixel-art; additions marked NEW)
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
C_STEM_DK       = ( 52, 104,  28)
C_LEAF          = ( 92, 156,  54)
C_LEAF_DK       = ( 65, 120,  36)
C_WHEAT         = (200, 168,  54)
C_WHEAT_LT      = (224, 196,  80)

# NEW: pumpkin colours
C_PUMPKIN       = (210, 130,  45)
C_PUMPKIN_LT    = (235, 158,  68)
C_PUMPKIN_DK    = (162,  94,  26)

# NEW: locked tile
C_LOCKED_BG     = ( 42,  28,  16)
C_LOCKED_ICON   = ( 70,  54,  36)

# Obstacle / stone
C_STONE         = ( 86,  80,  72)
C_STONE_DK      = ( 62,  56,  50)
C_STONE_LT      = (110, 103,  94)

# Robot (unchanged)
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

# NEW: shop overlay colours
C_SHOP_BG       = ( 34,  20,  10)
C_SHOP_HDR      = ( 52,  34,  18)
C_SHOP_TAB_A    = ( 76,  55,  30)    # active tab
C_SHOP_TAB_I    = ( 44,  28,  14)    # inactive tab
C_SHOP_ROW_A    = ( 55,  38,  22)    # item row primary
C_SHOP_ROW_B    = ( 46,  30,  16)    # item row alternate
C_SHOP_BUY      = ( 58,  98,  42)    # buy button
C_SHOP_BUY_H    = ( 78, 124,  58)    # buy button hover
C_SHOP_BUY_D    = ( 38,  52,  28)    # buy button disabled
C_SHOP_LOCK_TXT = (100,  82,  60)    # locked item text

# ─────────────────────────────────────────────────────────────────────────────
# Crop catalogue
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class CropInfo:
    name:    str
    turns:   int
    points:  int
    hint:    str   # editor hint

CROPS: dict = {
    "wheat":   CropInfo("Wheat",   2, 1, 'crop = "wheat"'),
    "carrot":  CropInfo("Carrot",  3, 2, 'crop = "carrot"  (default)'),
    "pumpkin": CropInfo("Pumpkin", 6, 4, 'crop = "pumpkin"'),
}

# ─────────────────────────────────────────────────────────────────────────────
# Enums & data classes
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
    state:     TileState = TileState.EMPTY
    growth_turns: int    = 0
    crop_type: str       = "carrot"   # NEW

# ─────────────────────────────────────────────────────────────────────────────
# Grid  (dict-based for dynamic expansion)
# ─────────────────────────────────────────────────────────────────────────────
class Grid:
    def __init__(self):
        self.tiles: dict = {}   # (r, c) → Tile
        self.r_min = 0;  self.r_max = 2
        self.c_min = 0;  self.c_max = 2
        for r in range(3):
            for c in range(3):
                self.tiles[(r, c)] = Tile()
        self._exp_gen  = self._expansion_sequence()
        self._exp_buf: list = []
        self._fill_buf(1)

    # spiral expansion: right col → bottom row → left col → top row → …
    @staticmethod
    def _expansion_sequence():
        r0, r1, c0, c1 = 0, 2, 0, 2
        while True:
            for r in range(r0, r1 + 1): yield r, c1 + 1
            c1 += 1
            for c in range(c0, c1 + 1): yield r1 + 1, c
            r1 += 1
            for r in range(r1, r0 - 1, -1): yield r, c0 - 1
            c0 -= 1
            for c in range(c0, c1 + 1): yield r0 - 1, c
            r0 -= 1

    def _fill_buf(self, n: int):
        while len(self._exp_buf) < n:
            self._exp_buf.append(next(self._exp_gen))

    def peek_next(self) -> tuple:
        self._fill_buf(1)
        return self._exp_buf[0]

    def unlock_next(self) -> tuple:
        self._fill_buf(1)
        r, c = self._exp_buf.pop(0)
        self.tiles[(r, c)] = Tile()
        self.r_min = min(self.r_min, r)
        self.r_max = max(self.r_max, r)
        self.c_min = min(self.c_min, c)
        self.c_max = max(self.c_max, c)
        self._fill_buf(1)
        return r, c

    @property
    def rows(self) -> int: return self.r_max - self.r_min + 1
    @property
    def cols(self) -> int: return self.c_max - self.c_min + 1

    def get(self, r, c) -> 'Tile | None':
        return self.tiles.get((r, c))

    def in_bounds(self, r, c) -> bool:
        return (r, c) in self.tiles

    # ── layout helpers (dynamic, includes preview tile) ────────────────────
    def _vis_extent(self) -> tuple:
        """(vr0, vr1, vc0, vc1) including the locked preview tile."""
        nr, nc = self.peek_next()
        return (min(self.r_min, nr), max(self.r_max, nr),
                min(self.c_min, nc), max(self.c_max, nc))

    def tile_origin(self) -> tuple:
        """Returns (left, top, vr0, vc0) pixel origin of the visual grid."""
        vr0, vr1, vc0, vc1 = self._vis_extent()
        gw = (vc1 - vc0 + 1) * TILE_SIZE
        gh = (vr1 - vr0 + 1) * TILE_SIZE
        avail_h = WIN_H - 85 - 150
        left = max(4, (PANEL_W - gw) // 2)
        top  = 85 + max(0, (avail_h - gh) // 2)
        return left, top, vr0, vc0

    def tile_px(self, r, c) -> tuple:
        left, top, vr0, vc0 = self.tile_origin()
        return left + (c - vc0) * TILE_SIZE, top + (r - vr0) * TILE_SIZE

    def tile_center(self, r, c) -> tuple:
        tx, ty = self.tile_px(r, c)
        return tx + TILE_SIZE // 2, ty + TILE_SIZE // 2

    def visual_rect(self) -> pygame.Rect:
        left, top, vr0, vc0 = self.tile_origin()
        vr0b, vr1, vc0b, vc1 = self._vis_extent()
        gw = (vc1 - vc0b + 1) * TILE_SIZE
        gh = (vr1 - vr0b + 1) * TILE_SIZE
        return pygame.Rect(left, top, gw, gh)

    def locked_positions(self):
        """Yield all (r, c) within the visual extent that are not yet unlocked."""
        vr0, vr1, vc0, vc1 = self._vis_extent()
        for r in range(vr0, vr1 + 1):
            for c in range(vc0, vc1 + 1):
                if not self.in_bounds(r, c):
                    yield r, c

    def tick(self):
        for tile in self.tiles.values():
            if tile.state == TileState.PLANTED:
                tile.growth_turns -= 1
                if tile.growth_turns <= 0:
                    tile.state = TileState.READY

# ─────────────────────────────────────────────────────────────────────────────
# Pricing helper
# ─────────────────────────────────────────────────────────────────────────────
def tile_cost(tiles_purchased: int) -> int:
    if tiles_purchased == 0: return 5
    if tiles_purchased == 1: return 10
    if tiles_purchased == 2: return 17
    cost = 17
    for _ in range(tiles_purchased - 2):
        cost = round(cost * 1.5)
    return cost

# ─────────────────────────────────────────────────────────────────────────────
# Robot
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Robot:
    row:       int       = 0
    col:       int       = 0
    direction: Direction = Direction.RIGHT
    px:        float     = 0.0
    py:        float     = 0.0
    target_px: float     = 0.0
    target_py: float     = 0.0

    def snap_to(self, grid: Grid):
        cx, cy = grid.tile_center(self.row, self.col)
        self.px = self.target_px = float(cx)
        self.py = self.target_py = float(cy)

    def set_target(self, r: int, c: int, grid: Grid):
        cx, cy = grid.tile_center(r, c)
        self.target_px = float(cx)
        self.target_py = float(cy)

# ─────────────────────────────────────────────────────────────────────────────
# GameState
# ─────────────────────────────────────────────────────────────────────────────
class GameState:
    def __init__(self):
        self.grid  = Grid()
        self.robot = Robot()
        self.robot.snap_to(self.grid)
        self.points = 0
        self.action_queue: deque = deque()  # tuples: ('move',), ('plant','carrot'), …
        # execution state (animation system — unchanged)
        self.running      = False
        self.animating    = False
        self.anim_is_move = False
        self.anim_timer   = 0.0
        self.console_msgs: list = []
        # NEW: progression & shop state
        self.tiles_purchased = 0
        self.unlocked_cmds: set = set()   # 'repeat', 'if_crop_ready', 'face'
        self.shop_open = False
        self.shop_tab  = 0                # 0=Grid 1=Crops 2=Commands

    def log(self, msg, color=C_CON_WHT):
        self.console_msgs.append((msg, color))
        if len(self.console_msgs) > 60:
            self.console_msgs.pop(0)

    def _start_move(self):
        self.animating = True;  self.anim_is_move = True

    def _start_pause(self):
        self.animating = True;  self.anim_is_move = False;  self.anim_timer = 0.0

    def dispatch(self, action: tuple):
        verb = action[0]
        robot = self.robot
        grid  = self.grid
        r, c  = robot.row, robot.col
        dr, dc = robot.direction.value

        if verb == 'move':
            nr, nc = r + dr, c + dc
            if not grid.in_bounds(nr, nc):
                self.log("move(): can't move there — tile not available.", C_CON_RED)
                self._start_pause()
            elif grid.get(nr, nc).state == TileState.OBSTACLE:
                self.log("move(): obstacle in the way.", C_CON_RED)
                self._start_pause()
            else:
                robot.row, robot.col = nr, nc
                robot.set_target(nr, nc, grid)
                self._start_move()
            grid.tick()

        elif verb == 'turn_left':
            idx = DIR_ORDER.index(robot.direction)
            robot.direction = DIR_ORDER[(idx - 1) % 4]
            grid.tick();  self._start_pause()

        elif verb == 'turn_right':
            idx = DIR_ORDER.index(robot.direction)
            robot.direction = DIR_ORDER[(idx + 1) % 4]
            grid.tick();  self._start_pause()

        elif verb == 'plant':
            crop_name = action[1] if len(action) > 1 else 'carrot'
            crop_info = CROPS.get(crop_name, CROPS['carrot'])
            tile = grid.get(r, c)
            if tile.state == TileState.EMPTY:
                tile.state = TileState.PLANTED
                tile.growth_turns = crop_info.turns
                tile.crop_type    = crop_name
                self.log(
                    f"Planted {crop_info.name} at ({r},{c}). "
                    f"Grows in {crop_info.turns} turns.", C_CON_YLW)
            else:
                self.log(f"plant(): tile ({r},{c}) is not empty soil.", C_CON_RED)
            grid.tick();  self._start_pause()

        elif verb == 'harvest':
            tile = grid.get(r, c)
            if tile.state == TileState.READY:
                crop_info = CROPS.get(tile.crop_type, CROPS['carrot'])
                tile.state = TileState.EMPTY
                tile.growth_turns = 0
                self.points += crop_info.points
                self.log(
                    f"Harvested {crop_info.name} at ({r},{c})! "
                    f"+{crop_info.points} pts  (total: {self.points})", C_CON_GRN)
            else:
                self.log(f"harvest(): tile ({r},{c}) not ready to harvest.", C_CON_RED)
            grid.tick();  self._start_pause()

        elif verb == 'wait':
            grid.tick();  self._start_pause()

        elif verb == 'face':
            dir_map = {
                'north': Direction.UP,   'south': Direction.DOWN,
                'east':  Direction.RIGHT,'west':  Direction.LEFT,
            }
            d = dir_map.get(str(action[1]).lower())
            if d:
                robot.direction = d
            else:
                self.log(f"face(): unknown direction '{action[1]}'", C_CON_RED)
            grid.tick();  self._start_pause()

# ─────────────────────────────────────────────────────────────────────────────
# Sandbox executor
# ─────────────────────────────────────────────────────────────────────────────
def build_sandbox(queue: deque, state: GameState) -> dict:
    ns = {'crop': 'carrot', '__builtins__': {}}

    def move():       queue.append(('move',))
    def turn_left():  queue.append(('turn_left',))
    def turn_right(): queue.append(('turn_right',))
    def plant():      queue.append(('plant', ns.get('crop', 'carrot')))
    def harvest():    queue.append(('harvest',))
    def wait():       queue.append(('wait',))

    ns.update({'move': move, 'turn_left': turn_left, 'turn_right': turn_right,
               'plant': plant, 'harvest': harvest, 'wait': wait})

    if 'repeat' in state.unlocked_cmds:
        def repeat(n, block):
            for _ in range(int(n)):
                for fn in block: fn()
        ns['repeat'] = repeat

    if 'if_crop_ready' in state.unlocked_cmds:
        def if_crop_ready():
            t = state.grid.get(state.robot.row, state.robot.col)
            return t is not None and t.state == TileState.READY
        ns['if_crop_ready'] = if_crop_ready

    if 'face' in state.unlocked_cmds:
        def face(d): queue.append(('face', d))
        ns['face'] = face

    return ns

def run_player_code(code: str, state: GameState):
    state.action_queue.clear()
    state.animating = False
    sandbox = build_sandbox(state.action_queue, state)
    try:
        exec(compile(code, '<editor>', 'exec'), sandbox)
    except SyntaxError as e:
        state.log(f"SyntaxError: {e.msg} (line {e.lineno})", C_CON_RED)
        state.action_queue.clear();  return
    except Exception as e:
        state.log(f"Error: {e}", C_CON_RED)
        state.action_queue.clear();  return
    if state.action_queue:
        state.running = True
        state.log(f"Running {len(state.action_queue)} command(s)…", C_CON_GRY)
    else:
        state.log("No commands queued.", C_CON_GRY)

# ─────────────────────────────────────────────────────────────────────────────
# Shop purchase handler
# ─────────────────────────────────────────────────────────────────────────────
def handle_buy(key: str, state: GameState):
    if key == 'tile':
        cost = tile_cost(state.tiles_purchased)
        if state.points >= cost:
            state.points -= cost
            r, c = state.grid.unlock_next()
            state.tiles_purchased += 1
            state.robot.snap_to(state.grid)   # recentre pixel pos after grid shift
            state.log(f"Unlocked new tile at ({r},{c})! Grid: "
                      f"{state.grid.rows}x{state.grid.cols}", C_CON_GRN)
        else:
            state.log(f"Need {cost} pts to buy next tile.", C_CON_RED)
    elif key in ('repeat', 'if_crop_ready', 'face'):
        if key in state.unlocked_cmds:
            state.log(f"{key}() is already unlocked.", C_CON_GRY)
        elif state.points >= 10:
            state.points -= 10
            state.unlocked_cmds.add(key)
            state.log(f"Unlocked {key}()!", C_CON_GRN)
        else:
            state.log("Need 10 pts to unlock a command.", C_CON_RED)

# ─────────────────────────────────────────────────────────────────────────────
# Editor Component  (unchanged)
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
        if event.type != pygame.KEYDOWN: return
        key  = event.key
        ctrl = event.mod & pygame.KMOD_CTRL

        if ctrl and key == pygame.K_a:
            self.cursor_col = 0; return
        if ctrl and key == pygame.K_e:
            self.cursor_col = len(self.lines[self.cursor_line]); return

        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            line = self.lines[self.cursor_line]
            self.lines[self.cursor_line] = line[:self.cursor_col]
            self.lines.insert(self.cursor_line + 1, line[self.cursor_col:])
            self.cursor_line += 1; self.cursor_col = 0

        elif key == pygame.K_BACKSPACE:
            if self.cursor_col > 0:
                line = self.lines[self.cursor_line]
                self.lines[self.cursor_line] = line[:self.cursor_col-1] + line[self.cursor_col:]
                self.cursor_col -= 1
            elif self.cursor_line > 0:
                prev = self.lines[self.cursor_line - 1]
                self.cursor_col = len(prev)
                self.lines[self.cursor_line - 1] = prev + self.lines[self.cursor_line]
                self.lines.pop(self.cursor_line); self.cursor_line -= 1

        elif key == pygame.K_DELETE:
            line = self.lines[self.cursor_line]
            if self.cursor_col < len(line):
                self.lines[self.cursor_line] = line[:self.cursor_col] + line[self.cursor_col+1:]
            elif self.cursor_line < len(self.lines) - 1:
                self.lines[self.cursor_line] += self.lines.pop(self.cursor_line + 1)

        elif key == pygame.K_LEFT:
            if self.cursor_col > 0: self.cursor_col -= 1
            elif self.cursor_line > 0:
                self.cursor_line -= 1; self.cursor_col = len(self.lines[self.cursor_line])
        elif key == pygame.K_RIGHT:
            if self.cursor_col < len(self.lines[self.cursor_line]): self.cursor_col += 1
            elif self.cursor_line < len(self.lines) - 1:
                self.cursor_line += 1; self.cursor_col = 0
        elif key == pygame.K_UP:
            if self.cursor_line > 0:
                self.cursor_line -= 1
                self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_line]))
        elif key == pygame.K_DOWN:
            if self.cursor_line < len(self.lines) - 1:
                self.cursor_line += 1
                self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_line]))
        elif key == pygame.K_HOME: self.cursor_col = 0
        elif key == pygame.K_END:  self.cursor_col = len(self.lines[self.cursor_line])
        elif event.unicode and event.unicode.isprintable():
            line = self.lines[self.cursor_line]
            self.lines[self.cursor_line] = line[:self.cursor_col] + event.unicode + line[self.cursor_col:]
            self.cursor_col += 1

        self._clamp_cursor()
        line_h = self.font.get_linesize()
        vis    = (self.rect.height - 12) // line_h
        if self.cursor_line < self.scroll_offset:
            self.scroll_offset = self.cursor_line
        elif self.cursor_line >= self.scroll_offset + vis:
            self.scroll_offset = self.cursor_line - vis + 1

    def draw(self, surf: pygame.Surface):
        pygame.draw.rect(surf, C_PARCHMENT, self.rect)
        line_h = self.font.get_linesize()
        pad = 8
        vis_lines = (self.rect.height - pad * 2) // line_h
        for i in range(vis_lines + 1):
            ly = self.rect.y + pad + i * line_h + line_h - 2
            if ly < self.rect.bottom - 2:
                pygame.draw.line(surf, C_PARCH_LINE,
                                 (self.rect.x + 4, ly), (self.rect.right - 4, ly), 1)
        pygame.draw.rect(surf, C_PARCH_DK, (self.rect.x, self.rect.y, 28, self.rect.height))
        pygame.draw.line(surf, C_EDITOR_BDR,
                         (self.rect.x + 28, self.rect.y), (self.rect.x + 28, self.rect.bottom), 1)
        for i in range(vis_lines):
            li = i + self.scroll_offset
            if li >= len(self.lines): break
            surf.blit(self.font.render(str(li + 1), True, C_WARM_GRY),
                      (self.rect.x + 4, self.rect.y + pad + i * line_h))
            surf.blit(self.font.render(self.lines[li], True, C_INK),
                      (self.rect.x + 34, self.rect.y + pad + i * line_h))
        show_cursor = (pygame.time.get_ticks() // CURSOR_BLINK_MS) % 2 == 0
        if self.focused and show_cursor:
            vis_li = self.cursor_line - self.scroll_offset
            if 0 <= vis_li < vis_lines:
                partial = self.lines[self.cursor_line][:self.cursor_col]
                cx = self.rect.x + 34 + self.font.size(partial)[0]
                cy = self.rect.y + pad + vis_li * line_h
                pygame.draw.line(surf, C_CURSOR_AMB, (cx, cy), (cx, cy + line_h - 2), 2)
        pygame.draw.rect(surf, C_EDITOR_BDR, self.rect, 2)

# ─────────────────────────────────────────────────────────────────────────────
# Console Component  (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
class ConsoleComponent:
    def __init__(self, rect: pygame.Rect, font: pygame.font.Font):
        self.rect = rect; self.font = font

    def draw(self, surf: pygame.Surface, msgs: list):
        pygame.draw.rect(surf, C_CON_BG, self.rect)
        pygame.draw.rect(surf, C_EDITOR_BDR, self.rect, 2)
        line_h = self.font.get_linesize()
        pad    = 7
        vis    = (self.rect.height - pad * 2) // line_h
        start  = max(0, len(msgs) - vis)
        for i, (text, color) in enumerate(msgs[start:]):
            surf.blit(self.font.render(text, True, color),
                      (self.rect.x + pad, self.rect.y + pad + i * line_h))

# ─────────────────────────────────────────────────────────────────────────────
# Renderer
# ─────────────────────────────────────────────────────────────────────────────
class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen     = screen
        self.font_mono  = pygame.font.SysFont("monospace", 14)
        self.font_ui    = pygame.font.SysFont("sans", 15, bold=True)
        self.font_big   = pygame.font.SysFont("sans", 24, bold=True)
        self.font_label = pygame.font.SysFont("monospace", 13)
        self.font_small = pygame.font.SysFont("monospace", 12)
        self._soil_dots: dict = {}   # lazy: (r,c) → dot list
        self._overlay   = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 165))
        # shop clickable rects — rebuilt each draw_shop_overlay call
        self.shop_tab_rects: list = []
        self.shop_buy_rects: list = []   # [(key, pygame.Rect), …]

    def _get_soil_dots(self, r, c):
        if (r, c) not in self._soil_dots:
            dots = []
            h = r * 0x6B + c * 0xA3 + 0xFF
            for _ in range(9):
                h = (h * 0x41C6 + 0x3039) & 0xFFFF; dx = 7 + h % 88
                h = (h * 0x41C6 + 0x3039) & 0xFFFF; dy = 7 + h % 88
                h = (h * 0x41C6 + 0x3039) & 0xFFFF
                dots.append((dx, dy, C_SOIL_LT if h % 3 != 0 else C_SOIL_DK))
            self._soil_dots[(r, c)] = dots
        return self._soil_dots[(r, c)]

    # ── tile sprites ─────────────────────────────────────────────────────────

    def _draw_soil_base(self, px, py, r, c):
        s = self.screen
        pygame.draw.rect(s, C_SOIL, (px + 3, py + 3, TILE_SIZE - 6, TILE_SIZE - 6))
        for dx, dy, col in self._get_soil_dots(r, c):
            pygame.draw.rect(s, col, (px + dx, py + dy, 3, 3))

    def _draw_sprout(self, px, py, crop_type='carrot'):
        s  = self.screen
        cx = px + TILE_SIZE // 2
        if crop_type == 'wheat':
            sc, lc = (118, 158, 56), (138, 178, 68)
        elif crop_type == 'pumpkin':
            sc, lc = C_STEM_DK, (115, 158, 52)
        else:
            sc, lc = C_STEM, C_LEAF
        pygame.draw.rect(s, sc,      (cx - 1, py + 48, 2, 38))
        pygame.draw.rect(s, C_STEM_LT,(cx,    py + 50, 1, 34))
        pygame.draw.rect(s, lc,      (cx - 11, py + 56, 10, 5))
        pygame.draw.rect(s, sc,      (cx - 11, py + 60, 10, 2))
        pygame.draw.rect(s, lc,      (cx + 1,  py + 64, 10, 5))
        pygame.draw.rect(s, sc,      (cx + 1,  py + 68, 10, 2))

    def _draw_crop(self, px, py, crop_type='carrot'):
        s  = self.screen
        cx = px + TILE_SIZE // 2
        if crop_type == 'wheat':
            pygame.draw.rect(s, C_STEM,    (cx - 1, py + 40, 2, 48))
            pygame.draw.rect(s, C_STEM_LT, (cx,     py + 42, 1, 44))
            pygame.draw.rect(s, C_LEAF,    (cx - 10, py + 60, 9, 4))
            pygame.draw.rect(s, C_LEAF,    (cx + 1,  py + 68, 9, 4))
            for ox in (-3, 0, 3):
                pygame.draw.rect(s, C_WHEAT,    (cx + ox - 1, py + 32, 3, 10))
                pygame.draw.rect(s, C_WHEAT_LT, (cx + ox,     py + 32, 2,  5))
        elif crop_type == 'pumpkin':
            pygame.draw.rect(s, C_STEM_DK, (cx - 1, py + 50, 2, 30))
            pygame.draw.rect(s, C_STEM,    (cx,     py + 52, 1, 26))
            for ox, ow in ((-14, 13), (-5, 15), (5, 13)):
                pygame.draw.rect(s, C_PUMPKIN,
                                 (cx + ox, py + 62, ow, 22), border_radius=4)
            for ox in (-12, -4, 6):
                pygame.draw.rect(s, C_PUMPKIN_LT, (cx + ox, py + 63, 3, 6))
            for ox in (-2, 6):
                pygame.draw.rect(s, C_PUMPKIN_DK, (cx + ox, py + 62, 2, 22))
            pygame.draw.rect(s, C_STEM_DK, (cx - 1, py + 50, 2, 14))
        else:  # carrot (original drawing, unchanged)
            pygame.draw.rect(s, C_STEM,    (cx - 1, py + 30, 2, 58))
            pygame.draw.rect(s, C_STEM_LT, (cx,     py + 32, 1, 54))
            for i, (side, ry) in enumerate([(-12, 50), (2, 60), (-12, 70)]):
                pygame.draw.rect(s, C_LEAF if i % 2 == 0 else C_LEAF_DK,
                                 (cx + side, py + ry,     11, 5))
                pygame.draw.rect(s, C_LEAF_DK if i % 2 == 0 else C_LEAF,
                                 (cx + side, py + ry + 4, 11, 2))
            for ox in (-4, 0, 4):
                pygame.draw.rect(s, C_WHEAT,    (cx + ox - 1, py + 30, 3, 9))
                pygame.draw.rect(s, C_WHEAT_LT, (cx + ox,     py + 30, 2, 4))

    def _draw_growth_pips(self, px, py, tile: Tile):
        crop_info = CROPS.get(tile.crop_type, CROPS['carrot'])
        total = crop_info.turns
        turns_done = total - tile.growth_turns
        num = min(total, 6)
        for i in range(num):
            filled = i < round(turns_done / total * num)
            col = C_STEM if filled else C_SOIL_DK
            pygame.draw.rect(self.screen, col,
                             (px + 8 + i * 9, py + TILE_SIZE - 14, 6, 6))

    def _draw_obstacle(self, px, py, r, c):
        s = self.screen
        pygame.draw.rect(s, C_STONE, (px + 3, py + 3, TILE_SIZE - 6, TILE_SIZE - 6))
        seed = r * 23 + c * 41 + 7
        for i in range(4):
            sx = px + 12 + ((seed * (i + 1) * 17) % 70)
            sy = py + 12 + ((seed * (i + 1) * 11) % 70)
            sw = 14 + ((seed * i * 7) % 18)
            sh = 10 + ((seed * i * 5) % 14)
            pygame.draw.rect(s, C_STONE_DK, (sx, sy, sw, sh))
            pygame.draw.rect(s, C_STONE_LT, (sx, sy, sw, 2))
            pygame.draw.rect(s, C_STONE_LT, (sx, sy, 2, sh))

    def _draw_locked_tile(self, px, py):
        s = self.screen
        pygame.draw.rect(s, C_LOCKED_BG, (px + 3, py + 3, TILE_SIZE - 6, TILE_SIZE - 6))
        cx = px + TILE_SIZE // 2;  cy = py + TILE_SIZE // 2
        pygame.draw.rect(s, C_LOCKED_ICON, (cx - 7, cy,     14, 11), border_radius=2)
        pygame.draw.rect(s, C_LOCKED_ICON, (cx - 5, cy - 8, 10,  9))
        pygame.draw.rect(s, C_LOCKED_BG,   (cx - 3, cy - 7,  6,  8))
        pygame.draw.rect(s, C_LOCKED_BG,   (cx - 2, cy + 2,  4,  4))
        hint = self.font_small.render("[S]", True, C_LOCKED_ICON)
        s.blit(hint, (px + TILE_SIZE - 22, py + TILE_SIZE - 18))
        pygame.draw.rect(s, C_TILE_BDR,
                         (px + 3, py + 3, TILE_SIZE - 6, TILE_SIZE - 6), 2)

    def draw_tile(self, tile: Tile, px, py, r, c):
        if tile.state == TileState.OBSTACLE:
            self._draw_obstacle(px, py, r, c)
        else:
            self._draw_soil_base(px, py, r, c)
            if tile.state == TileState.PLANTED:
                self._draw_sprout(px, py, tile.crop_type)
                self._draw_growth_pips(px, py, tile)
            elif tile.state == TileState.READY:
                self._draw_crop(px, py, tile.crop_type)
        pygame.draw.rect(self.screen, C_TILE_BDR,
                         (px + 3, py + 3, TILE_SIZE - 6, TILE_SIZE - 6), 2)

    # ── robot (unchanged) ─────────────────────────────────────────────────────

    def draw_robot(self, robot: Robot, anim_is_move: bool):
        s = self.screen
        cy_off = 0
        if anim_is_move:
            dist   = math.hypot(robot.target_px - robot.px, robot.target_py - robot.py)
            prog   = max(0.0, 1.0 - dist / TILE_SIZE)
            cy_off = int(-math.sin(prog * math.pi) * 5)
        cx = int(robot.px);  cy = int(robot.py) + cy_off
        pygame.draw.rect(s, C_BOT_DARK, (cx - 13, cy - 13 + 4, 26, 26), border_radius=3)
        pygame.draw.rect(s, C_BOT_BODY, (cx - 13, cy - 13,     26, 26), border_radius=3)
        pygame.draw.rect(s, C_BOT_DARK, (cx + 10, cy - 13, 3, 26))
        pygame.draw.rect(s, C_BOT_DARK, (cx - 13, cy + 10, 26,  3))
        d = robot.direction
        if   d == Direction.RIGHT: fp=(cx+4,cy-7,9,14); e1=(cx+6,cy-4); e2=(cx+6,cy+2)
        elif d == Direction.LEFT:  fp=(cx-13,cy-7,9,14);e1=(cx-10,cy-4);e2=(cx-10,cy+2)
        elif d == Direction.DOWN:  fp=(cx-7,cy+4,14,9); e1=(cx-4,cy+6); e2=(cx+2,cy+6)
        else:                      fp=(cx-7,cy-13,14,9);e1=(cx-4,cy-10);e2=(cx+2,cy-10)
        pygame.draw.rect(s, C_BOT_FACE, fp)
        pygame.draw.rect(s, C_BOT_EYE, (*e1, 3, 3))
        pygame.draw.rect(s, C_BOT_EYE, (*e2, 3, 3))
        pygame.draw.rect(s, C_BOT_LED, (cx + 7, cy - 12, 4, 4))

    # ── environment (updated for dynamic grid) ────────────────────────────────

    def _draw_left_bg(self, grid: Grid):
        s = self.screen
        s.fill(C_SKY, (0, 0, PANEL_W, WIN_H))
        s.fill(C_GRASS, (0, WIN_H - 48, PANEL_W, 48))
        s.fill(C_GRASS_DK, (0, WIN_H - 48, PANEL_W, 4))
        for i in range(0, PANEL_W, 14):
            pygame.draw.rect(s, C_GRASS_LT, (i,     WIN_H - 50, 5, 5))
            pygame.draw.rect(s, C_GRASS,    (i + 7, WIN_H - 52, 4, 5))
        fm   = 14
        vrec = grid.visual_rect()
        farm = pygame.Rect(vrec.x - fm, vrec.y - fm, vrec.w + fm * 2, vrec.h + fm * 2)
        pygame.draw.rect(s, C_FARM_BORDER, farm, border_radius=4)
        pygame.draw.rect(s, C_TILE_BDR,
                         pygame.Rect(farm.x + 3, farm.y + 3, farm.w - 6, farm.h - 6),
                         2, border_radius=2)

    def _draw_wood_panel(self):
        s = self.screen
        pygame.draw.rect(s, C_WOOD_BG, (PANEL_W, 0, PANEL_W, WIN_H))
        for y in range(0, WIN_H, 58):
            pygame.draw.line(s, C_WOOD_GRAIN, (PANEL_W, y),     (WIN_W, y),     1)
            pygame.draw.line(s, C_WOOD_LT,    (PANEL_W, y + 1), (WIN_W, y + 1), 1)
        pygame.draw.rect(s, C_DIVIDER, (PANEL_W, 0, 4, WIN_H))

    def _draw_run_button(self, btn: pygame.Rect, is_running: bool, hover: bool):
        s = self.screen
        if is_running:
            bg, txt_c, label = C_BTN_DIS, C_BTN_DIS_TXT, "Running..."
        else:
            bg, txt_c, label = (C_BTN_LT if hover else C_BTN_WOOD), C_BTN_TXT, "Run  >"
        pygame.draw.rect(s, C_BTN_DK, pygame.Rect(btn.x+3,btn.y+3,btn.w,btn.h), border_radius=5)
        pygame.draw.rect(s, bg, btn, border_radius=5)
        pygame.draw.line(s, C_BTN_LT, (btn.x+4, btn.y+2), (btn.right-4, btn.y+2), 1)
        pygame.draw.rect(s, C_BTN_DK, btn, 2, border_radius=5)
        bl = self.font_ui.render(label, True, txt_c)
        s.blit(bl, (btn.x + (btn.w - bl.get_width())  // 2,
                    btn.y + (btn.h - bl.get_height()) // 2))

    # ── shop overlay ──────────────────────────────────────────────────────────

    def draw_shop_overlay(self, state: GameState, mouse_pos: tuple):
        s = self.screen
        s.blit(self._overlay, (0, 0))

        # Panel background
        panel = pygame.Rect(SHOP_X, SHOP_Y, SHOP_W, SHOP_H)
        pygame.draw.rect(s, C_SHOP_BG, panel, border_radius=6)
        for y in range(SHOP_Y, SHOP_Y + SHOP_H, 52):
            pygame.draw.line(s, (28, 16, 8), (SHOP_X+2, y), (SHOP_X+SHOP_W-2, y), 1)
        pygame.draw.rect(s, C_WOOD_LT, panel, 2, border_radius=6)

        # Title bar
        hdr = pygame.Rect(SHOP_X, SHOP_Y, SHOP_W, 38)
        pygame.draw.rect(s, C_SHOP_HDR, hdr, border_radius=6)
        pygame.draw.rect(s, C_SHOP_HDR, (SHOP_X, SHOP_Y + 20, SHOP_W, 18))
        tit = self.font_big.render("SHOP", True, C_GOLD)
        s.blit(tit, (SHOP_X + 16, SHOP_Y + 8))
        hint = self.font_label.render("Press S or ESC to close", True, C_WARM_GRY)
        s.blit(hint, (SHOP_X + SHOP_W - hint.get_width() - 14, SHOP_Y + 12))

        # Tab row
        tab_y   = SHOP_Y + 38
        tab_h   = 32
        tab_w   = SHOP_W // 3
        tab_labels = ["Grid", "Crops", "Commands"]
        self.shop_tab_rects = []
        for i, lbl in enumerate(tab_labels):
            tr = pygame.Rect(SHOP_X + i * tab_w, tab_y, tab_w, tab_h)
            self.shop_tab_rects.append(tr)
            active = (i == state.shop_tab)
            bg = C_SHOP_TAB_A if active else C_SHOP_TAB_I
            pygame.draw.rect(s, bg, tr)
            pygame.draw.rect(s, C_WOOD_LT, tr, 1)
            ts = self.font_ui.render(lbl, True, C_GOLD if active else C_WARM_GRY)
            s.blit(ts, (tr.x + (tr.w - ts.get_width()) // 2,
                        tr.y + (tr.h - ts.get_height()) // 2))

        # Content area
        content_y = tab_y + tab_h + 4
        content_h = SHOP_H - 38 - tab_h - 4 - 28
        self.shop_buy_rects = []

        if state.shop_tab == 0:
            self._draw_shop_grid_tab(s, content_y, content_h, state, mouse_pos)
        elif state.shop_tab == 1:
            self._draw_shop_crops_tab(s, content_y, content_h)
        else:
            self._draw_shop_cmds_tab(s, content_y, content_h, state, mouse_pos)

        # Footer
        foot = self.font_label.render(
            "Earn points by harvesting crops  ·  S opens / closes shop", True, C_WARM_GRY)
        s.blit(foot, (SHOP_X + (SHOP_W - foot.get_width()) // 2,
                      SHOP_Y + SHOP_H - 22))

    def _shop_buy_btn(self, s, x, y, w, h, key, can_afford, already_owned, mouse_pos):
        rect = pygame.Rect(x, y, w, h)
        self.shop_buy_rects.append((key, rect))
        if already_owned:
            pygame.draw.rect(s, C_SHOP_BUY_D, rect, border_radius=4)
            lbl = self.font_small.render("OWNED", True, C_WARM_GRY)
        elif can_afford:
            hover = rect.collidepoint(mouse_pos)
            pygame.draw.rect(s, C_SHOP_BUY_H if hover else C_SHOP_BUY, rect, border_radius=4)
            lbl = self.font_small.render("Buy", True, C_BTN_TXT)
        else:
            pygame.draw.rect(s, C_SHOP_BUY_D, rect, border_radius=4)
            lbl = self.font_small.render("Buy", True, C_SHOP_LOCK_TXT)
        pygame.draw.rect(s, C_WOOD_LT, rect, 1, border_radius=4)
        s.blit(lbl, (rect.x + (rect.w - lbl.get_width())  // 2,
                     rect.y + (rect.h - lbl.get_height()) // 2))

    def _draw_shop_grid_tab(self, s, cy, ch, state: GameState, mouse_pos):
        x0 = SHOP_X + 16
        cost = tile_cost(state.tiles_purchased)
        nr, nc = state.grid.peek_next()

        # Info header
        info1 = self.font_ui.render(
            f"Current grid: {state.grid.rows}×{state.grid.cols}  "
            f"({state.grid.rows * state.grid.cols} tiles)", True, C_WARM_WHT)
        s.blit(info1, (x0, cy + 8))
        nr2, nc2 = state.grid.rows, state.grid.cols
        if nc == state.grid.c_max + 1 or nc == state.grid.c_min - 1:
            nc2 = state.grid.cols + 1
        else:
            nr2 = state.grid.rows + 1
        info2 = self.font_label.render(
            f"Next tile at ({nr},{nc})  →  grid becomes {nr2}×{nc2}", True, C_WARM_GRY)
        s.blit(info2, (x0, cy + 30))

        # Item row
        row = pygame.Rect(SHOP_X + 8, cy + 58, SHOP_W - 16, 66)
        pygame.draw.rect(s, C_SHOP_ROW_A, row, border_radius=4)
        pygame.draw.rect(s, C_WOOD_LT, row, 1, border_radius=4)

        name_s = self.font_ui.render("Expand Grid  (+1 tile)", True, C_WARM_WHT)
        s.blit(name_s, (row.x + 12, row.y + 10))
        desc_s = self.font_small.render(
            "Unlocks a new farmable tile on the nearest edge of the grid.", True, C_WARM_GRY)
        s.blit(desc_s, (row.x + 12, row.y + 32))
        cost_s = self.font_ui.render(f"{cost} pts", True, C_GOLD)
        s.blit(cost_s, (row.x + 12, row.y + 46))

        self._shop_buy_btn(s, row.right - 78, row.y + 16, 66, 34,
                           'tile', state.points >= cost, False, mouse_pos)

        purch_s = self.font_label.render(
            f"Tiles purchased: {state.tiles_purchased}   "
            f"Next after that: {tile_cost(state.tiles_purchased + 1)} pts",
            True, C_WARM_GRY)
        s.blit(purch_s, (x0, cy + 136))

    def _draw_shop_crops_tab(self, s, cy, ch):
        x0 = SHOP_X + 8
        hdr = self.font_ui.render("All crops are available from the start.", True, C_WARM_GRY)
        s.blit(hdr, (x0 + 8, cy + 8))
        set_hint = self.font_label.render(
            'Set  crop = "name"  before calling plant()   (default: carrot)', True, C_WARM_GRY)
        s.blit(set_hint, (x0 + 8, cy + 28))

        for i, (k, ci) in enumerate(CROPS.items()):
            row = pygame.Rect(x0, cy + 56 + i * 68, SHOP_W - 16, 60)
            pygame.draw.rect(s, C_SHOP_ROW_A if i % 2 == 0 else C_SHOP_ROW_B,
                             row, border_radius=4)
            pygame.draw.rect(s, C_WOOD_LT, row, 1, border_radius=4)
            nm = self.font_ui.render(ci.name, True, C_GOLD)
            s.blit(nm, (row.x + 12, row.y + 8))
            det = self.font_label.render(
                f"{ci.turns} turns to grow  ·  +{ci.points} pt{'s' if ci.points > 1 else ''} on harvest",
                True, C_WARM_GRY)
            s.blit(det, (row.x + 12, row.y + 30))
            usage = self.font_small.render(ci.hint, True, C_CON_YLW)
            s.blit(usage, (row.right - usage.get_width() - 12, row.y + 22))

    def _draw_shop_cmds_tab(self, s, cy, ch, state: GameState, mouse_pos):
        x0 = SHOP_X + 8
        CMDS = [
            ('repeat',       'repeat(n, [cmd, …])',
             'Repeat a list of commands n times.    e.g.  repeat(3, [move, harvest])'),
            ('if_crop_ready','if_crop_ready()',
             'Returns True if current tile has a ready-to-harvest crop.'),
            ('face',         'face(direction)',
             'Instantly face a direction.    e.g.  face("north") / face("east")'),
        ]
        for i, (key, sig, desc) in enumerate(CMDS):
            owned = key in state.unlocked_cmds
            row = pygame.Rect(x0, cy + 6 + i * 80, SHOP_W - 16, 72)
            pygame.draw.rect(s, C_SHOP_ROW_A if i % 2 == 0 else C_SHOP_ROW_B,
                             row, border_radius=4)
            pygame.draw.rect(s, C_WOOD_LT, row, 1, border_radius=4)
            txt_col = C_WARM_WHT if owned else C_SHOP_LOCK_TXT
            nm = self.font_ui.render(sig, True, txt_col)
            s.blit(nm, (row.x + 12, row.y + 8))
            ds = self.font_small.render(desc, True, C_WARM_GRY if owned else (80, 65, 50))
            s.blit(ds, (row.x + 12, row.y + 32))
            cost_s = self.font_label.render("10 pts", True, C_GOLD if not owned else C_WARM_GRY)
            s.blit(cost_s, (row.x + 12, row.y + 52))
            self._shop_buy_btn(s, row.right - 80, row.y + 18, 68, 34,
                               key, state.points >= 10, owned, mouse_pos)

    # ── main draw call ────────────────────────────────────────────────────────

    def draw(self, state: GameState,
             editor: EditorComponent,
             console: ConsoleComponent,
             btn_rect: pygame.Rect,
             btn_hover: bool,
             mouse_pos: tuple):
        s = self.screen

        # ── left panel ───────────────────────────────────────────────────────
        self._draw_left_bg(state.grid)

        for r, c in state.grid.locked_positions():
            self._draw_locked_tile(*state.grid.tile_px(r, c))

        for (r, c), tile in state.grid.tiles.items():
            self.draw_tile(tile, *state.grid.tile_px(r, c), r, c)

        self.draw_robot(state.robot, state.anim_is_move and state.animating)

        # Title + points
        s.blit(self.font_big.render("Farm Bot", True, C_GOLD), (20, 14))
        s.blit(self.font_ui.render(f"Points: {state.points}", True, C_WARM_WHT), (20, 46))
        cost = tile_cost(state.tiles_purchased)
        s.blit(self.font_small.render(f"Next tile: {cost} pts  [S]", True, C_WARM_GRY), (20, 66))

        # Command reference (bottom-left)
        ref_y = WIN_H - 152
        s.blit(self.font_label.render("Commands:", True, C_WARM_GRY), (20, ref_y))
        for i, cmd in enumerate(["move()", "turn_left()", "turn_right()",
                                  "plant()", "harvest()", "wait()"]):
            s.blit(self.font_label.render(cmd, True, C_CON_GRY), (24, ref_y + 16 + i * 17))

        # ── right panel ──────────────────────────────────────────────────────
        self._draw_wood_panel()

        el = self.font_ui.render("Code Editor", True, C_GOLD)
        s.blit(el, (editor.rect.x, editor.rect.y - 22))
        editor.draw(s)

        self._draw_run_button(btn_rect, state.running, btn_hover)

        # Unlocked commands line
        if state.unlocked_cmds:
            ul_txt = "Unlocked: " + "   ".join(sorted(state.unlocked_cmds))
        else:
            ul_txt = "Unlocked commands: none yet  (visit shop with S)"
        s.blit(self.font_small.render(ul_txt, True, C_WARM_GRY),
               (editor.rect.x, btn_rect.bottom + 8))

        cl = self.font_ui.render("Console", True, C_GOLD)
        s.blit(cl, (console.rect.x, console.rect.y - 22))
        console.draw(s, state.console_msgs)

        # ── shop overlay (drawn on top when open) ─────────────────────────────
        if state.shop_open:
            self.draw_shop_overlay(state, mouse_pos)

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
    editor_rect  = pygame.Rect(RIGHT_X, 40, PANEL_W - 40, 296)
    btn_rect     = pygame.Rect(RIGHT_X, 350, 130, 34)
    console_rect = pygame.Rect(RIGHT_X, 420, PANEL_W - 40, WIN_H - 438)

    editor  = EditorComponent(editor_rect, renderer.font_mono)
    console = ConsoleComponent(console_rect, renderer.font_mono)

    state.log("Welcome! Write commands and press Run.  Press S to open the shop.", C_CON_GRY)
    state.log("Commands: move()  turn_left()  turn_right()  plant()  harvest()  wait()", C_CON_GRY)
    state.log('Set crop type with: crop = "wheat" / "carrot" / "pumpkin"', C_CON_GRY)

    game_running = True
    while game_running:
        dt        = clock.tick(60) / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        btn_hover = btn_rect.collidepoint(mouse_pos) and not state.running and not state.shop_open

        # ── events ──────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_s,) and not editor.focused:
                    state.shop_open = not state.shop_open
                elif event.key == pygame.K_ESCAPE and state.shop_open:
                    state.shop_open = False
                elif state.shop_open:
                    pass   # all other keys blocked by shop
                elif editor.focused:
                    editor.handle_event(event)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state.shop_open:
                    for i, rect in enumerate(renderer.shop_tab_rects):
                        if rect.collidepoint(event.pos):
                            state.shop_tab = i
                    for key, rect in renderer.shop_buy_rects:
                        if rect.collidepoint(event.pos):
                            handle_buy(key, state)
                else:
                    if btn_hover:
                        run_player_code(editor.text, state)
                    elif editor_rect.collidepoint(event.pos):
                        editor.focused = True
                    else:
                        editor.focused = False

        # ── animation update (paused when shop is open) ──────────────────────
        robot = state.robot
        if not state.shop_open and state.running and state.animating:
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

        # ── dispatch next action ─────────────────────────────────────────────
        if not state.shop_open and state.running and not state.animating:
            if state.action_queue:
                state.dispatch(state.action_queue.popleft())
            else:
                state.running = False
                state.log("Done.", C_CON_GRY)

        # ── draw ─────────────────────────────────────────────────────────────
        renderer.draw(state, editor, console, btn_rect, btn_hover, mouse_pos)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
