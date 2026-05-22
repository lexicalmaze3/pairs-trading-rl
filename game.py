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

ISO_HALF_W      = 64    # half-width of iso diamond (full face = 128 px)
ISO_HALF_H      = 32    # half-height of iso diamond (full face = 64 px)
BLOCK_H         = 14    # visible side-face height for 3D cube look

# Animation timing
MOVE_DURATION  = 0.35   # s per tile
TURN_DURATION  = 0.20   # s for turn arc
BUMP_DURATION  = 0.22   # s for invalid-move bump
PAUSE_DURATION = 0.15   # s for plant / harvest / wait
BUMP_DIST      = 18     # px offset during bump

CURSOR_BLINK_MS = 530

# Shop panel dimensions
SHOP_W, SHOP_H  = 660, 500
SHOP_X          = (WIN_W - SHOP_W) // 2   # 220
SHOP_Y          = (WIN_H - SHOP_H) // 2   # 100

# ─────────────────────────────────────────────────────────────────────────────
# Colour palette  (cozy warm pixel-art; additions marked NEW)
# ─────────────────────────────────────────────────────────────────────────────

# Sky gradient
C_SKY_TOP       = (132, 185, 218)   # pale azure
C_SKY_BOT       = (208, 210, 190)   # warm horizon cream

# Environment
C_SKY           = (148, 193, 228)
C_GRASS         = ( 76, 118,  56)
C_GRASS_DK      = ( 58,  94,  42)
C_GRASS_LT      = ( 96, 140,  70)

# Isometric tile faces
C_ISO_SOIL_T    = (110,  78,  50)   # top face (lit)
C_ISO_SOIL_L    = ( 80,  54,  32)   # left / NW face
C_ISO_SOIL_R    = ( 58,  36,  18)   # right / SE face (shadow)
C_ISO_STONE_T   = ( 96,  89,  82)
C_ISO_STONE_L   = ( 70,  64,  57)
C_ISO_STONE_R   = ( 50,  44,  38)
C_ISO_LOCK_T    = ( 48,  32,  16)
C_ISO_LOCK_L    = ( 34,  22,  10)
C_ISO_LOCK_R    = ( 24,  14,   6)
C_ISO_PLAT_F    = ( 54,  34,  14)   # platform front face
C_ISO_SHADOW    = ( 28,  16,   6)   # shadow under objects

# Overalls / hat
C_OV_MAIN       = ( 72, 106, 158)   # denim blue
C_OV_DARK       = ( 52,  78, 118)
C_HAT_BRIM      = (184, 148,  60)   # straw gold
C_HAT_DOME      = (202, 166,  76)
C_HAT_BAND      = (138,  76,  36)

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

def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def dir_to_angle(d: Direction) -> float:
    return {Direction.RIGHT: 0.0, Direction.DOWN: 90.0,
            Direction.LEFT: 180.0, Direction.UP: 270.0}[d]

# Isometric geometry helpers – top vertex is the "north" point of the diamond
def _iso_verts(sx: int, sy: int) -> list:
    return [(sx, sy),
            (sx + ISO_HALF_W, sy + ISO_HALF_H),
            (sx, sy + ISO_HALF_H * 2),
            (sx - ISO_HALF_W, sy + ISO_HALF_H)]

def _iso_left_pts(sx: int, sy: int) -> list:
    """Left (NW) side face of BLOCK_H-tall cube."""
    return [(sx - ISO_HALF_W, sy + ISO_HALF_H),
            (sx, sy + ISO_HALF_H * 2),
            (sx, sy + ISO_HALF_H * 2 + BLOCK_H),
            (sx - ISO_HALF_W, sy + ISO_HALF_H + BLOCK_H)]

def _iso_right_pts(sx: int, sy: int) -> list:
    """Right (SE) side face of BLOCK_H-tall cube."""
    return [(sx, sy + ISO_HALF_H * 2),
            (sx + ISO_HALF_W, sy + ISO_HALF_H),
            (sx + ISO_HALF_W, sy + ISO_HALF_H + BLOCK_H),
            (sx, sy + ISO_HALF_H * 2 + BLOCK_H)]

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

    def tile_px(self, r: int, c: int) -> tuple:
        """Top (north) vertex of tile's iso diamond in screen space."""
        # Derive a stable origin so the visual centre of the grid is at PANEL_W/2
        vr0, vr1, vc0, vc1 = self._vis_extent()
        span_h = (vc1 - vc0 + vr1 - vr0 + 2) * ISO_HALF_H
        top_m, bot_m = 92, 168
        oy_base = top_m + max(0, (WIN_H - top_m - bot_m - span_h) // 2)
        # ox is always the panel centre; oy_base is the y of tile(0,0) top vertex
        return (PANEL_W // 2 + (c - r) * ISO_HALF_W,
                oy_base + (c + r) * ISO_HALF_H)

    def tile_center(self, r: int, c: int) -> tuple:
        """Centre of the iso top face (robot anchor point)."""
        sx, sy = self.tile_px(r, c)
        return sx, sy + ISO_HALF_H

    def visual_rect(self) -> pygame.Rect:
        """Bounding rectangle of the full visible grid (used for background framing)."""
        vr0, vr1, vc0, vc1 = self._vis_extent()
        # corners of the diamond grid
        top_sx, top_sy    = self.tile_px(vr0, vc0)
        right_sx, right_sy = self.tile_px(vr0, vc1)
        bot_sx,  bot_sy    = self.tile_px(vr1, vc1)
        left_sx, left_sy   = self.tile_px(vr1, vc0)
        lx = left_sx  - ISO_HALF_W - 8
        rx = right_sx + ISO_HALF_W + 8
        ty = top_sy               - 8
        by = bot_sy   + ISO_HALF_H * 2 + BLOCK_H + 8
        return pygame.Rect(lx, ty, rx - lx, by - ty)

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
    row:          int       = 0
    col:          int       = 0
    direction:    Direction = Direction.RIGHT
    px:           float     = 0.0
    py:           float     = 0.0
    target_px:    float     = 0.0
    target_py:    float     = 0.0
    start_px:     float     = 0.0
    start_py:     float     = 0.0
    visual_angle: float     = 0.0   # degrees: 0=right 90=down 180=left 270=up
    start_angle:  float     = 0.0
    target_angle: float     = 0.0

    def snap_to(self, grid: Grid):
        cx, cy = grid.tile_center(self.row, self.col)
        self.px = self.target_px = self.start_px = float(cx)
        self.py = self.target_py = self.start_py = float(cy)
        self.visual_angle = dir_to_angle(self.direction)

    def set_target(self, r: int, c: int, grid: Grid):
        self.start_px = self.px
        self.start_py = self.py
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
        # execution state
        self.running       = False
        self.animating     = False
        self.anim_type     = 'none'   # 'move' | 'turn' | 'bump' | 'pause'
        self.anim_elapsed  = 0.0
        self.anim_duration = 0.0
        self.anim_bump_dx  = 0.0
        self.anim_bump_dy  = 0.0
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

    def _start_anim(self, anim_type: str, duration: float):
        self.animating     = True
        self.anim_type     = anim_type
        self.anim_elapsed  = 0.0
        self.anim_duration = duration

    def _start_move(self):
        self._start_anim('move', MOVE_DURATION)

    def _start_turn(self, new_dir: Direction):
        from_a = self.robot.visual_angle
        to_a   = dir_to_angle(new_dir)
        delta  = (to_a - from_a + 180.0) % 360.0 - 180.0
        self.robot.start_angle  = from_a
        self.robot.target_angle = from_a + delta
        self._start_anim('turn', TURN_DURATION)

    def _start_bump(self, dr: int, dc: int):
        self.robot.start_px = self.robot.px
        self.robot.start_py = self.robot.py
        self.anim_bump_dx   = float(dc) * BUMP_DIST
        self.anim_bump_dy   = float(dr) * BUMP_DIST
        self._start_anim('bump', BUMP_DURATION)

    def _start_pause(self):
        self._start_anim('pause', PAUSE_DURATION)

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
                self._start_bump(dr, dc)
            elif grid.get(nr, nc).state == TileState.OBSTACLE:
                self.log("move(): obstacle in the way.", C_CON_RED)
                self._start_bump(dr, dc)
            else:
                robot.row, robot.col = nr, nc
                robot.set_target(nr, nc, grid)
                self._start_move()
            grid.tick()

        elif verb == 'turn_left':
            idx = DIR_ORDER.index(robot.direction)
            new_dir = DIR_ORDER[(idx - 1) % 4]
            robot.direction = new_dir
            grid.tick();  self._start_turn(new_dir)

        elif verb == 'turn_right':
            idx = DIR_ORDER.index(robot.direction)
            new_dir = DIR_ORDER[(idx + 1) % 4]
            robot.direction = new_dir
            grid.tick();  self._start_turn(new_dir)

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
                grid.tick();  self._start_turn(d)
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
    state.animating    = False
    state.anim_type    = 'none'
    state.anim_elapsed = 0.0
    state.robot.snap_to(state.grid)
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
        pygame.draw.rect(surf, (12, 12, 12), self.rect)
        line_h = self.font.get_linesize()
        pad = 8
        vis_lines = (self.rect.height - pad * 2) // line_h
        # Line-number gutter
        pygame.draw.rect(surf, (24, 24, 24), (self.rect.x, self.rect.y, 28, self.rect.height))
        pygame.draw.line(surf, (50, 50, 50),
                         (self.rect.x + 28, self.rect.y), (self.rect.x + 28, self.rect.bottom), 1)
        for i in range(vis_lines):
            li = i + self.scroll_offset
            if li >= len(self.lines): break
            surf.blit(self.font.render(str(li + 1), True, (80, 80, 80)),
                      (self.rect.x + 4, self.rect.y + pad + i * line_h))
            surf.blit(self.font.render(self.lines[li], True, (220, 220, 220)),
                      (self.rect.x + 34, self.rect.y + pad + i * line_h))
        show_cursor = (pygame.time.get_ticks() // CURSOR_BLINK_MS) % 2 == 0
        if self.focused and show_cursor:
            vis_li = self.cursor_line - self.scroll_offset
            if 0 <= vis_li < vis_lines:
                partial = self.lines[self.cursor_line][:self.cursor_col]
                cx = self.rect.x + 34 + self.font.size(partial)[0]
                cy = self.rect.y + pad + vis_li * line_h
                pygame.draw.line(surf, (200, 200, 200), (cx, cy), (cx, cy + line_h - 2), 2)
        pygame.draw.rect(surf, (50, 50, 50), self.rect, 1)

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
        self._soil_dots: dict = {}
        self._overlay   = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 165))
        self.shop_tab_rects: list = []
        self.shop_buy_rects: list = []
        # Pre-render sky gradient (pale azure → warm cream horizon)
        self._sky_surf = pygame.Surface((PANEL_W, WIN_H))
        for _y in range(WIN_H):
            _t = min(1.0, _y / (WIN_H * 0.62))
            _c = (int(C_SKY_TOP[0] + (C_SKY_BOT[0]-C_SKY_TOP[0])*_t),
                  int(C_SKY_TOP[1] + (C_SKY_BOT[1]-C_SKY_TOP[1])*_t),
                  int(C_SKY_TOP[2] + (C_SKY_BOT[2]-C_SKY_TOP[2])*_t))
            self._sky_surf.fill(_c, (0, _y, PANEL_W, 1))

    # ── iso tile rendering ────────────────────────────────────────────────────

    def _get_iso_dots(self, r: int, c: int) -> list:
        """Stable per-tile texture dots positioned within the diamond."""
        if (r, c) in self._soil_dots:
            return self._soil_dots[(r, c)]
        dots = []
        h = r * 0x6B + c * 0xA3 + 0xFF
        for _ in range(40):
            h = (h * 0x41C6 + 0x3039) & 0xFFFF
            dx = (h % (ISO_HALF_W * 2)) - ISO_HALF_W
            h = (h * 0x41C6 + 0x3039) & 0xFFFF
            dy = (h % (ISO_HALF_H * 2)) - ISO_HALF_H
            # reject outside diamond (|dx|/IHW + |dy|/IHH > 0.72)
            if abs(dx) / ISO_HALF_W + abs(dy) / ISO_HALF_H > 0.72:
                continue
            h = (h * 0x41C6 + 0x3039) & 0xFFFF
            col = C_SOIL_LT if h % 3 != 0 else C_SOIL_DK
            dots.append((dx, dy, col))
            if len(dots) >= 8:
                break
        self._soil_dots[(r, c)] = dots
        return dots

    def _draw_iso_cube(self, sx: int, sy: int,
                       top_c, left_c, right_c, edge_c=None):
        """Draw a flat iso cube block with three visible faces."""
        s = self.screen
        pygame.draw.polygon(s, right_c, _iso_right_pts(sx, sy))
        pygame.draw.polygon(s, left_c,  _iso_left_pts(sx, sy))
        pygame.draw.polygon(s, top_c,   _iso_verts(sx, sy))
        # Crisp outline on top face only
        ec = edge_c or C_TILE_BDR
        pygame.draw.polygon(s, ec, _iso_verts(sx, sy), 1)

    def _draw_iso_sprout(self, sx: int, sy: int, tile):
        """Small plant above the tile surface during growth."""
        s  = self.screen
        cx = sx;  cy = sy + ISO_HALF_H   # tile face centre
        crop = CROPS.get(tile.crop_type, CROPS['carrot'])
        prog = max(0.0, 1.0 - tile.growth_turns / max(1, crop.turns))
        ht   = int(10 + prog * 22)
        # Shadow ellipse
        pygame.draw.ellipse(s, C_ISO_SHADOW, (cx - 10, cy - 3, 20, 7))
        if tile.crop_type == 'wheat':
            for ox in (-4, 0, 4):
                pygame.draw.line(s, C_STEM, (cx+ox, cy), (cx+ox, cy-ht), 1)
                pygame.draw.line(s, C_STEM_LT, (cx+ox+1, cy), (cx+ox+1, cy-ht+2), 1)
            if prog > 0.3:
                pygame.draw.ellipse(s, (118,158,56), (cx-9, cy-ht-2, 10, 5))
                pygame.draw.ellipse(s, (118,158,56), (cx+1, cy-ht+1, 10, 5))
        elif tile.crop_type == 'pumpkin':
            pygame.draw.line(s, C_STEM_DK, (cx, cy), (cx, cy-ht), 2)
            pygame.draw.line(s, C_STEM,    (cx+1, cy), (cx+1, cy-ht+2), 1)
            if prog > 0.35:
                pygame.draw.ellipse(s, C_PUMPKIN,    (cx-6, cy-ht-4, 13, 10))
                pygame.draw.ellipse(s, C_PUMPKIN_LT, (cx-4, cy-ht-3,  5,  5))
        else:  # carrot
            pygame.draw.line(s, C_STEM, (cx, cy), (cx, cy-ht), 2)
            pygame.draw.line(s, C_STEM_LT, (cx+1, cy), (cx+1, cy-ht+2), 1)
            if prog > 0.3:
                for ox, oy2 in ((-8, -4), (2, -2), (-6, -8)):
                    pygame.draw.ellipse(s, C_LEAF,    (cx+ox, cy-ht+oy2, 10, 5))
                    pygame.draw.ellipse(s, C_LEAF_DK, (cx+ox, cy-ht+oy2+3, 10, 3))

    def _draw_iso_crop(self, sx: int, sy: int, tile):
        """Full mature crop above the tile surface."""
        s  = self.screen
        cx = sx;  cy = sy + ISO_HALF_H
        pygame.draw.ellipse(s, C_ISO_SHADOW, (cx - 14, cy - 4, 28, 9))
        if tile.crop_type == 'wheat':
            ht = 46
            for ox in (-7, -3, 1, 5):
                pygame.draw.line(s, C_STEM,    (cx+ox, cy), (cx+ox,   cy-ht), 1)
                pygame.draw.line(s, C_STEM_LT, (cx+ox+1, cy), (cx+ox+1, cy-ht+4), 1)
                # drooping head
                pygame.draw.line(s, C_WHEAT, (cx+ox, cy-ht), (cx+ox+4, cy-ht+10), 2)
                pygame.draw.ellipse(s, C_WHEAT,    (cx+ox+1, cy-ht+6, 6, 9))
                pygame.draw.ellipse(s, C_WHEAT_LT, (cx+ox+2, cy-ht+7, 3, 5))
            for ox in (-9, -5, -1, 3):
                pygame.draw.ellipse(s, C_LEAF, (cx+ox, cy-ht//2-2, 9, 4))
        elif tile.crop_type == 'pumpkin':
            ht = 16
            pygame.draw.line(s, C_STEM_DK, (cx, cy), (cx, cy-ht), 2)
            pygame.draw.line(s, C_STEM,    (cx+1, cy), (cx+1, cy-ht), 1)
            # Three pumpkin lobes side by side
            for ox, ow in ((-14, 13), (-4, 15), (6, 13)):
                pygame.draw.ellipse(s, C_PUMPKIN,    (cx+ox, cy-ht-16, ow, 18), border_radius=2)
                pygame.draw.ellipse(s, C_PUMPKIN_LT, (cx+ox+2, cy-ht-14, ow//2, 7))
            for ox in (-12, -2, 8):
                pygame.draw.line(s, C_PUMPKIN_DK,
                                 (cx+ox, cy-ht-1), (cx+ox, cy-ht-16), 1)
            # Stem curls
            pygame.draw.arc(s, C_STEM_DK,
                            pygame.Rect(cx-4, cy-ht-22, 10, 8), 0, math.pi, 2)
        else:  # carrot
            ht = 40
            pygame.draw.line(s, C_STEM,    (cx, cy), (cx,   cy-ht), 2)
            pygame.draw.line(s, C_STEM_LT, (cx+1, cy), (cx+1, cy-ht+4), 1)
            for i, (ox, oy2) in enumerate([(-10, -8), (3, -12), (-8, -20),
                                           (2, -22), (-6, -30)]):
                lc = C_LEAF if i % 2 == 0 else C_LEAF_DK
                pygame.draw.ellipse(s, lc, (cx+ox, cy-ht+oy2, 12, 5))
            # small orange tip hint
            pygame.draw.ellipse(s, (200, 110, 50), (cx-3, cy-4, 6, 6))
            pygame.draw.ellipse(s, (220, 140, 70), (cx-2, cy-3, 3, 3))

    def _draw_iso_pips(self, sx: int, sy: int, tile):
        """Growth progress indicators along the front edge of the tile."""
        crop_info = CROPS.get(tile.crop_type, CROPS['carrot'])
        total     = max(1, crop_info.turns)
        done      = total - tile.growth_turns
        num       = min(total, 6)
        cx = sx;  base_y = sy + ISO_HALF_H * 2 + 2
        step = 8
        for i in range(num):
            filled = i < round(done / total * num)
            col    = C_STEM if filled else C_SOIL_DK
            bx     = cx - (num * step) // 2 + i * step
            pygame.draw.rect(self.screen, col, (bx, base_y, 5, 4))

    def _draw_iso_locked(self, sx: int, sy: int):
        """Locked / purchasable tile block."""
        self._draw_iso_cube(sx, sy, C_ISO_LOCK_T, C_ISO_LOCK_L, C_ISO_LOCK_R, C_LOCKED_ICON)
        cx = sx;  cy = sy + ISO_HALF_H
        pygame.draw.rect(self.screen, C_LOCKED_ICON, (cx-6, cy, 12, 9),  border_radius=2)
        pygame.draw.rect(self.screen, C_LOCKED_ICON, (cx-4, cy-7, 8, 8))
        pygame.draw.rect(self.screen, C_ISO_LOCK_T,  (cx-2, cy-6, 4, 7))
        pygame.draw.rect(self.screen, C_ISO_LOCK_T,  (cx-2, cy+2, 4, 4))
        hint = self.font_small.render("[S]", True, C_LOCKED_ICON)
        self.screen.blit(hint, (sx + ISO_HALF_W - 18, sy + ISO_HALF_H))

    def draw_iso_tile(self, sx: int, sy: int, tile, r: int, c: int):
        """Draw a single tile at iso top-vertex position (sx, sy)."""
        seed  = (r * 0x6B + c * 0xA3 + 0xFF) & 0xFF
        dv    = (seed % 20) - 10

        if tile.state == TileState.OBSTACLE:
            top_c = tuple(max(0, min(255, v + dv // 2)) for v in C_ISO_STONE_T)
            self._draw_iso_cube(sx, sy, top_c, C_ISO_STONE_L, C_ISO_STONE_R)
            # Stone cracks
            s = self.screen;  cx2 = sx;  cy2 = sy + ISO_HALF_H
            h2 = r * 23 + c * 41 + 7
            for i in range(3):
                ox2 = ((h2 * (i+1) * 17) % (ISO_HALF_W)) - ISO_HALF_W // 2
                oy2 = ((h2 * (i+1) * 11) % (ISO_HALF_H)) - ISO_HALF_H // 2
                pygame.draw.line(s, C_ISO_STONE_R, (cx2+ox2, cy2+oy2),
                                 (cx2+ox2+5, cy2+oy2+3), 1)
        else:
            base = C_ISO_SOIL_T
            if tile.state == TileState.PLANTED:
                base = (max(0, C_ISO_SOIL_T[0]-14), max(0, C_ISO_SOIL_T[1]-8),
                        min(255, C_ISO_SOIL_T[2]+6))
            top_c = tuple(max(0, min(255, v + dv // 2)) for v in base)
            self._draw_iso_cube(sx, sy, top_c, C_ISO_SOIL_L, C_ISO_SOIL_R)
            # Texture dots on top face
            cx2 = sx;  cy2 = sy + ISO_HALF_H
            for ddx, ddy, col in self._get_iso_dots(r, c):
                pygame.draw.rect(self.screen, col, (cx2+ddx, cy2+ddy, 2, 1))
            if tile.state == TileState.PLANTED:
                self._draw_iso_sprout(sx, sy, tile)
                self._draw_iso_pips(sx, sy, tile)
            elif tile.state == TileState.READY:
                self._draw_iso_crop(sx, sy, tile)

    # ── isometric robot ───────────────────────────────────────────────────────

    def draw_robot(self, robot: Robot, anim_type: str, t_raw: float):
        s = self.screen
        bob = int(-math.sin(t_raw * math.pi) * 4) if anim_type == 'move' else 0
        cx  = int(robot.px)
        cy  = int(robot.py) + bob   # tile-face centre is the "feet" anchor

        # 1. Ground shadow
        pygame.draw.ellipse(s, C_ISO_SHADOW, (cx - 15, cy - 5, 30, 11))

        # 2. Legs (short, under the body)
        leg_y = cy - 4
        pygame.draw.rect(s, C_OV_DARK, (cx - 7, leg_y - 8, 5, 9))
        pygame.draw.rect(s, C_OV_DARK, (cx + 2,  leg_y - 8, 5, 9))
        pygame.draw.rect(s, C_BOT_DARK, (cx - 5,  leg_y + 1, 4, 3))  # boot
        pygame.draw.rect(s, C_BOT_DARK, (cx + 3,  leg_y + 1, 4, 3))

        # 3. Overall body (trapezoidal iso feel)
        body_y = leg_y - 8
        body_h = 18
        pygame.draw.polygon(s, C_OV_DARK, [
            (cx - 8,  body_y + body_h),
            (cx + 8,  body_y + body_h),
            (cx + 10, body_y),
            (cx - 10, body_y)])
        pygame.draw.polygon(s, C_OV_MAIN, [
            (cx - 10, body_y + body_h),
            (cx + 10, body_y + body_h),
            (cx + 10, body_y),
            (cx - 10, body_y)])
        # Overalls bib
        pygame.draw.rect(s, C_OV_MAIN, (cx - 5, body_y + 2, 10, 10))
        # Straps
        pygame.draw.line(s, (102, 140, 195), (cx - 4, body_y + 2), (cx - 6, body_y + body_h - 2), 2)
        pygame.draw.line(s, (102, 140, 195), (cx + 4, body_y + 2), (cx + 6, body_y + body_h - 2), 2)
        # Side shading
        pygame.draw.polygon(s, C_OV_DARK, [
            (cx + 7,  body_y + body_h),
            (cx + 10, body_y + body_h),
            (cx + 10, body_y),
            (cx + 7,  body_y)])

        # 4. Head
        head_y = body_y - 13
        pygame.draw.rect(s, C_BOT_FACE, (cx - 7, head_y, 14, 13))
        pygame.draw.rect(s, C_BOT_DARK, (cx + 4, head_y + 1, 3, 12))   # right shading

        # 5. Face panel + eyes from visual_angle (smooth rotation)
        ar   = math.radians(robot.visual_angle)
        fr   = 6.0
        fcx  = cx + math.cos(ar) * fr
        fcy  = (head_y + 6) + math.sin(ar) * 2.5
        abss = abs(math.sin(ar));  absc = abs(math.cos(ar))
        fw   = round(8 * absc + 12 * abss)
        fh   = round(12 * absc + 8  * abss)
        pygame.draw.rect(s, C_BOT_FACE, (int(fcx - fw/2), int(fcy - fh/2), fw, fh))
        px2 = -math.sin(ar);  py2 = math.cos(ar)
        e1  = (int(fcx - px2 * 2.5 - 1), int(fcy - py2 * 2.5 - 1))
        e2  = (int(fcx + px2 * 2.5 - 1), int(fcy + py2 * 2.5 - 1))
        pygame.draw.rect(s, C_BOT_EYE, (*e1, 3, 3))
        pygame.draw.rect(s, C_BOT_EYE, (*e2, 3, 3))

        # 6. Straw hat
        hat_by = head_y - 2
        pygame.draw.ellipse(s, (156, 120, 44), (cx - 14, hat_by - 2, 28, 10))  # brim shadow
        pygame.draw.ellipse(s, C_HAT_BRIM,     (cx - 14, hat_by - 4, 28, 10))  # brim
        pygame.draw.ellipse(s, C_HAT_DOME,     (cx - 8,  hat_by - 16, 16, 16)) # dome
        pygame.draw.ellipse(s, (156, 120, 44), (cx - 5,  hat_by - 2,  10,  6)) # brim indent
        pygame.draw.rect(s,    C_HAT_BAND,     (cx - 7,  hat_by - 8,  14,  3)) # band

    # ── isometric environment ─────────────────────────────────────────────────

    def _draw_left_bg(self, grid: Grid):
        s = self.screen
        # Sky gradient
        s.blit(self._sky_surf, (0, 0))

        # Soft ground fill below the grid
        vrec = grid.visual_rect()
        ground_y = vrec.bottom - 10
        pygame.draw.rect(s, C_GRASS, (0, ground_y, PANEL_W, WIN_H - ground_y))
        pygame.draw.rect(s, C_GRASS_DK, (0, ground_y, PANEL_W, 4))
        for i in range(0, PANEL_W, 12):
            pygame.draw.rect(s, C_GRASS_LT, (i,     ground_y - 3, 4, 5))
            pygame.draw.rect(s, C_GRASS,    (i + 6, ground_y - 5, 3, 5))

        # Platform base: draw front face below the bottom-row tiles
        vr0, vr1, vc0, vc1 = grid._vis_extent()
        plat_points = []
        for c in range(vc0, vc1 + 1):
            sx, sy = grid.tile_px(vr1, c)
            if not plat_points:
                plat_points.append((sx - ISO_HALF_W, sy + ISO_HALF_H))
            plat_points.append((sx, sy + ISO_HALF_H * 2))
        for sx_r, sy_r in reversed(plat_points):
            plat_points.append((sx_r, sy_r + BLOCK_H + 6))
        if len(plat_points) >= 3:
            pygame.draw.polygon(s, C_ISO_PLAT_F, plat_points)
            pygame.draw.polygon(s, C_TILE_BDR,   plat_points, 1)

        # Right edge platform side face (right column tiles)
        r_pts = []
        for r in range(vr0, vr1 + 1):
            sx, sy = grid.tile_px(r, vc1)
            if not r_pts:
                r_pts.append((sx, sy + ISO_HALF_H * 2))
            r_pts.append((sx + ISO_HALF_W, sy + ISO_HALF_H))
        for sx2, sy2 in reversed(r_pts):
            r_pts.append((sx2, sy2 + BLOCK_H + 6))
        if len(r_pts) >= 3:
            pygame.draw.polygon(s, C_ISO_SOIL_R, r_pts)
            pygame.draw.polygon(s, C_TILE_BDR,   r_pts, 1)

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
            ('repeat',        'repeat(n, [cmd, …])',
             'Repeats a list of commands n times.',
             'repeat(3, [move, harvest])'),
            ('if_crop_ready', 'if_crop_ready()',
             'Returns True if the current tile has a crop ready to harvest.',
             'if if_crop_ready(): harvest()'),
            ('face',          'face(direction)',
             'Instantly faces the robot in a cardinal direction.',
             'face("north")'),
        ]
        row_h   = 96
        row_gap = 6
        for i, (key, sig, desc, example) in enumerate(CMDS):
            owned   = key in state.unlocked_cmds
            row     = pygame.Rect(x0, cy + 4 + i * (row_h + row_gap), SHOP_W - 16, row_h)
            bg_col  = C_SHOP_ROW_A if i % 2 == 0 else C_SHOP_ROW_B
            pygame.draw.rect(s, bg_col,   row, border_radius=4)
            pygame.draw.rect(s, C_WOOD_LT, row, 1, border_radius=4)

            txt_col  = C_WARM_WHT if owned else C_SHOP_LOCK_TXT
            desc_col = C_WARM_GRY if owned else (80, 65, 50)

            # Signature
            s.blit(self.font_ui.render(sig, True, txt_col),
                   (row.x + 12, row.y + 8))

            # One-line description
            s.blit(self.font_label.render(desc, True, desc_col),
                   (row.x + 12, row.y + 30))

            # Example box (dark warm rect + monospace yellow text)
            ex_surf = self.font_mono.render(example, True, C_CON_YLW)
            ex_rect = pygame.Rect(row.x + 12, row.y + 50,
                                  ex_surf.get_width() + 10, ex_surf.get_height() + 4)
            pygame.draw.rect(s, (28, 18, 8),   ex_rect, border_radius=3)
            pygame.draw.rect(s, C_DIVIDER,      ex_rect, 1, border_radius=3)
            s.blit(ex_surf, (ex_rect.x + 5, ex_rect.y + 2))

            # Cost + buy button
            cost_col = C_GOLD if not owned else C_WARM_GRY
            s.blit(self.font_label.render("10 pts", True, cost_col),
                   (row.x + 12, row.y + row_h - 18))
            self._shop_buy_btn(s, row.right - 80, row.y + (row_h - 34) // 2, 68, 34,
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

        # Painter's algorithm: sorted by (r+c) ascending, r ascending within depth
        grid = state.grid
        _locked = set(grid.locked_positions())
        _all    = {(r, c): ('locked', None) for r, c in _locked}
        for (r, c), tile in grid.tiles.items():
            _all[(r, c)] = ('tile', tile)
        for (r, c) in sorted(_all, key=lambda rc: (rc[0]+rc[1], rc[0])):
            sx, sy = grid.tile_px(r, c)
            kind, tile = _all[(r, c)]
            if kind == 'locked':
                self._draw_iso_locked(sx, sy)
            else:
                self.draw_iso_tile(sx, sy, tile, r, c)

        # Robot drawn last (flat grid — always on top of tiles)
        _t_raw = min(1.0, state.anim_elapsed / state.anim_duration) if (state.animating and state.anim_duration > 0) else 0.0
        self.draw_robot(state.robot, state.anim_type if state.animating else 'none', _t_raw)

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
            state.anim_elapsed += dt
            dur   = state.anim_duration if state.anim_duration > 0 else 1e-6
            t_raw = min(1.0, state.anim_elapsed / dur)
            t     = smoothstep(t_raw)
            if state.anim_type == 'move':
                robot.px = robot.start_px + (robot.target_px - robot.start_px) * t
                robot.py = robot.start_py + (robot.target_py - robot.start_py) * t
            elif state.anim_type == 'bump':
                bump_t   = math.sin(t_raw * math.pi)
                robot.px = robot.start_px + state.anim_bump_dx * bump_t
                robot.py = robot.start_py + state.anim_bump_dy * bump_t
            elif state.anim_type == 'turn':
                delta = robot.target_angle - robot.start_angle
                robot.visual_angle = robot.start_angle + delta * t
            if t_raw >= 1.0:
                if state.anim_type == 'move':
                    robot.px = robot.target_px
                    robot.py = robot.target_py
                elif state.anim_type == 'bump':
                    robot.px = robot.start_px
                    robot.py = robot.start_py
                elif state.anim_type == 'turn':
                    robot.visual_angle = dir_to_angle(robot.direction)
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
