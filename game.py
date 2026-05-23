import ast
import random
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

TILE_W          = 88    # tile width in pixels
TILE_H          = 66    # tile height (compressed ~75 % for slight-tilt look)
TILE_DEPTH      = 5     # bottom-edge depth strip suggesting tilt

# Animation timing
MOVE_DURATION  = 0.35   # s per tile
TURN_DURATION  = 0.20   # s for turn arc
BUMP_DURATION  = 0.22   # s for invalid-move bump
PAUSE_DURATION = 0.15   # s for plant / harvest / wait
BUMP_DIST      = 18     # px offset during bump
DAY_DURATION   = 180.0  # real seconds per full day/night cycle

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

# ─────────────────────────────────────────────────────────────────────────────
# Day / night colour helpers
# ─────────────────────────────────────────────────────────────────────────────
# Keyframes: (time_of_day, sky_top_rgb, sky_bot_rgb)
# 0.0=dawn  0.25=midday  0.5=dusk  0.75=midnight
_SKY_KEYS = [
    (0.00, (200, 115,  75), (245, 170, 105)),   # dawn  — pink / soft orange
    (0.25, (132, 185, 218), (208, 210, 190)),   # midday — pale blue / warm cream
    (0.50, (148,  68,  52), (105,  58, 118)),   # dusk  — deep orange / purple
    (0.75, ( 10,  14,  44), (  5,   8,  28)),   # midnight — deep navy
    (1.00, (200, 115,  75), (245, 170, 105)),   # wraps back to dawn
]

def _lerp_c(ca, cb, t):
    return (int(ca[0] + (cb[0]-ca[0])*t),
            int(ca[1] + (cb[1]-ca[1])*t),
            int(ca[2] + (cb[2]-ca[2])*t))

def _sky_colors(tod: float):
    """Return (top_rgb, bot_rgb) for the given time-of-day."""
    for i in range(len(_SKY_KEYS) - 1):
        t0, a0, b0 = _SKY_KEYS[i]
        t1, a1, b1 = _SKY_KEYS[i + 1]
        if t0 <= tod <= t1:
            f = (tod - t0) / (t1 - t0)
            return _lerp_c(a0, a1, f), _lerp_c(b0, b1, f)
    return _SKY_KEYS[0][1], _SKY_KEYS[0][2]

def _night_alpha(tod: float) -> int:
    """Overlay opacity: 0 at midday (0.25), 160 at midnight (0.75), smooth cosine."""
    phase = (tod - 0.75) * 2 * math.pi   # 0 at midnight, ±π at midday
    return max(0, int((math.cos(phase) + 1) / 2 * 160))

@dataclass
class Tile:
    state:     TileState = TileState.EMPTY
    growth_turns: int    = 0
    crop_type: str       = "carrot"   # NEW

@dataclass
class Challenge:
    key:         str
    name:        str
    desc:        str
    goal:        int
    progress:    int   = 0
    reward_type: str   = 'cosmetic'   # 'cosmetic','command','decoration','points'
    reward_key:  str   = ''
    reward_name: str   = ''
    completed:   bool  = False
    flash_timer: float = 0.0

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
        """Top-left corner of the tile's screen rectangle."""
        vr0, vr1, vc0, vc1 = self._vis_extent()
        n_cols = vc1 - vc0 + 1
        n_rows = vr1 - vr0 + 1
        ox = PANEL_W // 2 - (n_cols * TILE_W) // 2 - vc0 * TILE_W
        top_m, bot_m = 90, 130
        oy = top_m + max(0, (WIN_H - top_m - bot_m - n_rows * TILE_H) // 2) - vr0 * TILE_H
        return ox + c * TILE_W, oy + r * TILE_H

    def tile_center(self, r: int, c: int) -> tuple:
        """Centre of the tile's screen rectangle (robot anchor)."""
        sx, sy = self.tile_px(r, c)
        return sx + TILE_W // 2, sy + TILE_H // 2

    def visual_rect(self) -> pygame.Rect:
        """Bounding rectangle of the full visible grid."""
        vr0, vr1, vc0, vc1 = self._vis_extent()
        sx, sy = self.tile_px(vr0, vc0)
        w = (vc1 - vc0 + 1) * TILE_W
        h = (vr1 - vr0 + 1) * TILE_H + TILE_DEPTH
        return pygame.Rect(sx - 6, sy - 6, w + 12, h + 12)

    def locked_positions(self):
        """Yield all (r, c) within the visual extent that are not yet unlocked."""
        vr0, vr1, vc0, vc1 = self._vis_extent()
        for r in range(vr0, vr1 + 1):
            for c in range(vc0, vc1 + 1):
                if not self.in_bounds(r, c):
                    yield r, c

    def tick(self, is_day: bool = True):
        for tile in self.tiles.values():
            if tile.state == TileState.PLANTED and is_day:
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

CMD_PRICES: dict = {
    'repeat':        10,
    'if_crop_ready': 10,
    'face':          10,
    'variables':     35,
    'is_soil':       20,
    'is_blocked':    20,
    'crop_type':     25,
    'position':      20,
    'count':         25,
    'for_loop':      40,
    'while_loop':    50,
    'if_else':       45,
    'def_func':      60,
}

SHOP_CMDS: list = [
    ("Basics", [
        ('repeat',        'repeat(n, [cmd, …])',
         'Repeats a list of commands n times.',
         'repeat(3, [move, harvest])'),
        ('if_crop_ready', 'if_crop_ready()',
         'Returns True if current tile has a crop ready to harvest.',
         'if if_crop_ready(): harvest()'),
        ('face',          'face(direction)',
         'Instantly faces the robot in a cardinal direction.',
         'face("north")'),
    ]),
    ("Awareness", [
        ('is_soil',    'is_soil()',
         'Returns True if the current tile is empty plantable soil.',
         'if is_soil(): plant()'),
        ('is_blocked', 'is_blocked()',
         'Returns True if the tile ahead is a wall or off-grid.',
         'if not is_blocked(): move()'),
        ('crop_type',  'crop_type()',
         'Returns the crop name on the current tile, or None.',
         'if crop_type() == "carrot": harvest()'),
        ('position',   'position()',
         'Returns (row, col) of the robot.',
         'r, c = position()'),
        ('count',      'count()',
         'Returns how many tiles currently have a ready crop.',
         'if count() > 0: harvest()'),
    ]),
    ("Control Flow", [
        ('for_loop',   'for i in range(n):',
         'Standard Python for-loop. Also unlocks range().',
         'for i in range(3): move()'),
        ('while_loop', 'while <condition>:',
         'Standard Python while-loop.',
         'while not is_blocked(): move()'),
        ('if_else',    'if / else',
         'Standard Python if/else branching.',
         'if is_soil(): plant()'),
        ('variables',  'x = value',
         'Assign and use variables (except crop = "name").',
         'n = 4'),
    ]),
    ("Functions", [
        ('def_func',   'def name():',
         'Define reusable functions.',
         'def farm(): plant()'),
    ]),
]

_SHOP_CMD_ROW_H      = 84
_SHOP_CMD_ROW_GAP    = 4
_SHOP_CMD_SEC_H      = 22
_SHOP_CMD_SEC_GAP    = 6
_SHOP_CMD_CONTENT_H  = SHOP_H - 38 - 32 - 4 - 28   # 398
_SHOP_CMD_TOTAL_H    = sum(
    (_SHOP_CMD_SEC_H + _SHOP_CMD_SEC_GAP if title else 0)
    + len(items) * (_SHOP_CMD_ROW_H + _SHOP_CMD_ROW_GAP)
    for title, items in SHOP_CMDS
)
_SHOP_CMD_MAX_SCROLL = max(0, _SHOP_CMD_TOTAL_H - _SHOP_CMD_CONTENT_H)

# ─────────────────────────────────────────────────────────────────────────────
# Challenge definitions
# ─────────────────────────────────────────────────────────────────────────────
CHALLENGE_POOL = [
    dict(key='first_harvest',    name='First Harvest',      desc='Harvest any crop for the first time.',
         goal=1,  reward_type='cosmetic',    reward_key='golden_skin',   reward_name='Golden Skin'),
    dict(key='green_thumb',      name='Green Thumb',        desc='Have 4+ crops planted at the same time.',
         goal=4,  reward_type='cosmetic',    reward_key='hat_orange',    reward_name='Orange Hat'),
    dict(key='efficient_farmer', name='Efficient Farmer',   desc='Harvest 5 crops in a single run.',
         goal=5,  reward_type='cosmetic',    reward_key='overalls_blue', reward_name='Blue Overalls'),
    dict(key='explorer',         name='Explorer',           desc='Visit every tile in a single run.',
         goal=9,  reward_type='decoration',  reward_key='scarecrow',     reward_name='Scarecrow'),
    dict(key='pumpkin_rush',     name='Pumpkin Rush',       desc='Harvest 3 pumpkins in one run.',
         goal=3,  reward_type='cosmetic',    reward_key='hat_dark',      reward_name='Dark Hat'),
    dict(key='wheat_baron',      name='Wheat Baron',        desc='Harvest 20 wheat total.',
         goal=20, reward_type='decoration',  reward_key='well',          reward_name='Stone Well'),
    dict(key='night_owl',        name='Night Owl',          desc='Harvest 5 crops at night.',
         goal=5,  reward_type='cosmetic',    reward_key='lantern',       reward_name='Lantern'),
    dict(key='programmer',       name='Programmer',         desc='Use a for-loop in your code.',
         goal=1,  reward_type='cosmetic',    reward_key='scarf_red',     reward_name='Red Scarf'),
    dict(key='master_coder',     name='Master Coder',       desc='Use for, while, and def in one run.',
         goal=3,  reward_type='points',      reward_key='',              reward_name='+50 Points'),
    dict(key='century',          name='Century',            desc='Earn 100 total points.',
         goal=100, reward_type='points',     reward_key='',              reward_name='+25 Points'),
    dict(key='teleporter',       name='Teleporter',         desc='Use teleport() 5 times.',
         goal=5,  reward_type='cosmetic',    reward_key='overalls_blue', reward_name='Blue Overalls'),
    dict(key='scanner',          name='Scanner',            desc='Use scan() 3 times.',
         goal=3,  reward_type='points',      reward_key='',              reward_name='+20 Points'),
]

def _make_challenge(d: dict) -> Challenge:
    return Challenge(
        key=d['key'], name=d['name'], desc=d['desc'], goal=d['goal'],
        reward_type=d['reward_type'], reward_key=d['reward_key'],
        reward_name=d['reward_name'],
    )

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
        self.shop_tab        = 0     # 0=Grid 1=Crops 2=Commands 3=Challenges
        self.shop_cmd_scroll = 0
        self.shop_ch_scroll  = 0
        # Day / night
        self.time_of_day  = 0.0   # 0=dawn 0.25=midday 0.5=dusk 0.75=midnight
        self.total_time   = 0.0   # real seconds elapsed
        self.day_number   = 1
        # Cosmetics & decorations
        self.cosmetics:   set = set()
        self.decorations: set = set()
        # Challenges
        self.active_challenges:    list = []
        self.completed_challenge_keys: set = set()
        # Per-run trackers (reset each Run press)
        self.run_harvest_count  = 0
        self.run_pumpkin_count  = 0
        self.run_wheat_count    = 0
        self.run_action_count   = 0
        self.run_tiles_visited: set = set()
        self.run_has_for   = False
        self.run_has_while = False
        self.run_has_def   = False
        self.run_teleport_count = 0
        self.run_scan_count     = 0
        # Persistent counters
        self.total_any_harvests    = 0
        self.total_wheat_harvests  = 0
        self.total_pumpkin_harvests = 0
        self.total_night_harvests  = 0
        self.total_points_earned   = 0
        self.total_teleports       = 0
        self.total_scans           = 0
        # End-of-run completion flags (prevent double-awarding)
        self._efficient_done   = False
        self._explorer_done    = False
        self._programmer_done  = False
        self._pumpkin_rush_done = False
        self._master_coder_done = False
        self._init_challenges()

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
        is_day = self.time_of_day < 0.5

        self.run_action_count += 1
        self.run_tiles_visited.add((r, c))

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
                self.run_tiles_visited.add((nr, nc))
                self._start_move()
            grid.tick(is_day)

        elif verb == 'turn_left':
            idx = DIR_ORDER.index(robot.direction)
            new_dir = DIR_ORDER[(idx - 1) % 4]
            robot.direction = new_dir
            grid.tick(is_day);  self._start_turn(new_dir)

        elif verb == 'turn_right':
            idx = DIR_ORDER.index(robot.direction)
            new_dir = DIR_ORDER[(idx + 1) % 4]
            robot.direction = new_dir
            grid.tick(is_day);  self._start_turn(new_dir)

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
                    f"Grows in {crop_info.turns} turns.", C_CON_WHT)
            else:
                self.log(f"plant(): tile ({r},{c}) is not empty soil.", C_CON_RED)
            grid.tick(is_day);  self._start_pause()

        elif verb == 'harvest':
            tile = grid.get(r, c)
            if tile.state == TileState.READY:
                crop_info = CROPS.get(tile.crop_type, CROPS['carrot'])
                tile.state = TileState.EMPTY
                tile.growth_turns = 0
                self.points += crop_info.points
                self.total_points_earned += crop_info.points
                self.total_any_harvests  += 1
                self.run_harvest_count   += 1
                if tile.crop_type == 'wheat':
                    self.total_wheat_harvests += 1
                    self.run_wheat_count      += 1
                if tile.crop_type == 'pumpkin':
                    self.total_pumpkin_harvests += 1
                    self.run_pumpkin_count      += 1
                if not is_day:
                    self.total_night_harvests += 1
                self.log(
                    f"Harvested {crop_info.name} at ({r},{c})! "
                    f"+{crop_info.points} pts  (total: {self.points})", C_CON_GRN)
            else:
                self.log(f"harvest(): tile ({r},{c}) not ready to harvest.", C_CON_RED)
            grid.tick(is_day);  self._start_pause()

        elif verb == 'wait':
            grid.tick(is_day);  self._start_pause()

        elif verb == 'face':
            dir_map = {
                'north': Direction.UP,   'south': Direction.DOWN,
                'east':  Direction.RIGHT,'west':  Direction.LEFT,
            }
            d = dir_map.get(str(action[1]).lower())
            if d:
                robot.direction = d
                grid.tick(is_day);  self._start_turn(d)
            else:
                self.log(f"face(): unknown direction '{action[1]}'", C_CON_RED)
                grid.tick(is_day);  self._start_pause()

        elif verb == 'teleport':
            nr, nc = int(action[1]), int(action[2])
            if not grid.in_bounds(nr, nc):
                self.log(f"teleport(): ({nr},{nc}) is not an unlocked tile.", C_CON_RED)
                self._start_pause()
            elif grid.get(nr, nc).state == TileState.OBSTACLE:
                self.log(f"teleport(): ({nr},{nc}) is an obstacle.", C_CON_RED)
                self._start_pause()
            else:
                robot.row, robot.col = nr, nc
                robot.set_target(nr, nc, grid)
                robot.px, robot.py = robot.target_px, robot.target_py
                self.run_teleport_count += 1
                self.total_teleports    += 1
                self.log(f"Teleported to ({nr},{nc}).", C_CON_WHT)
                self._start_pause()
            grid.tick(is_day)

        elif verb == 'scan':
            results = []
            for (tr, tc), tile in grid.tiles.items():
                results.append(f"({tr},{tc}):{tile.state.name[:1]}")
            self.log("scan(): " + "  ".join(results), C_CON_WHT)
            self.run_scan_count += 1
            self.total_scans    += 1
            grid.tick(is_day);  self._start_pause()

        elif verb == 'auto_harvest':
            harvested = 0
            for (tr, tc), tile in list(grid.tiles.items()):
                if tile.state == TileState.READY:
                    crop_info = CROPS.get(tile.crop_type, CROPS['carrot'])
                    tile.state = TileState.EMPTY
                    tile.growth_turns = 0
                    self.points += crop_info.points
                    self.total_points_earned += crop_info.points
                    self.total_any_harvests  += 1
                    if tile.crop_type == 'wheat':
                        self.total_wheat_harvests += 1
                        self.run_wheat_count      += 1
                    if tile.crop_type == 'pumpkin':
                        self.total_pumpkin_harvests += 1
                        self.run_pumpkin_count      += 1
                    if not is_day:
                        self.total_night_harvests += 1
                    harvested += 1
                    self.run_harvest_count += 1
            self.log(f"auto_harvest(): harvested {harvested} crop(s). Total: {self.points} pts", C_CON_GRN)
            grid.tick(is_day);  self._start_pause()

    # ── challenge methods ────────────────────────────────────────────────────

    def _init_challenges(self):
        pool = list(CHALLENGE_POOL)
        random.shuffle(pool)
        avail = [d for d in pool if d['key'] not in self.completed_challenge_keys]
        self.active_challenges = [_make_challenge(d) for d in avail[:2]]

    def _replace_challenge(self, idx: int):
        pool = [d for d in CHALLENGE_POOL
                if d['key'] not in self.completed_challenge_keys
                and not any(c.key == d['key'] for c in self.active_challenges)]
        if pool:
            random.shuffle(pool)
            self.active_challenges[idx] = _make_challenge(pool[0])

    def _get_ch_progress(self, ch: Challenge) -> int:
        k = ch.key
        if k == 'first_harvest':   return self.total_any_harvests
        if k == 'green_thumb':
            return sum(1 for t in self.grid.tiles.values() if t.state == TileState.PLANTED)
        if k == 'efficient_farmer': return self.run_harvest_count
        if k == 'explorer':         return len(self.run_tiles_visited)
        if k == 'pumpkin_rush':     return self.run_pumpkin_count
        if k == 'wheat_baron':      return self.total_wheat_harvests
        if k == 'night_owl':        return self.total_night_harvests
        if k == 'programmer':       return 1 if self.run_has_for else 0
        if k == 'master_coder':
            return sum([self.run_has_for, self.run_has_while, self.run_has_def])
        if k == 'century':          return self.total_points_earned
        if k == 'teleporter':       return self.total_teleports
        if k == 'scanner':          return self.total_scans
        return 0

    def _complete_challenge(self, idx: int):
        ch = self.active_challenges[idx]
        ch.completed   = True
        ch.flash_timer = 3.0
        self.completed_challenge_keys.add(ch.key)
        if ch.reward_type == 'cosmetic' and ch.reward_key:
            self.cosmetics.add(ch.reward_key)
            self.log(f"Challenge '{ch.name}' done! Reward: {ch.reward_name}", C_CON_GRN)
        elif ch.reward_type == 'decoration' and ch.reward_key:
            self.decorations.add(ch.reward_key)
            self.log(f"Challenge '{ch.name}' done! Reward: {ch.reward_name}", C_CON_GRN)
        elif ch.reward_type == 'points':
            bonus = {'master_coder': 50, 'century': 25, 'scanner': 20}.get(ch.key, 15)
            self.points += bonus
            self.total_points_earned += bonus
            self.log(f"Challenge '{ch.name}' done! Reward: +{bonus} pts", C_CON_GRN)

    def update_challenges(self):
        for i, ch in enumerate(self.active_challenges):
            if ch.completed:
                continue
            prog = self._get_ch_progress(ch)
            ch.progress = prog
            if prog >= ch.goal:
                self._complete_challenge(i)

# ─────────────────────────────────────────────────────────────────────────────
# Sandbox executor
# ─────────────────────────────────────────────────────────────────────────────
def _check_syntax_locks(code: str, unlocked: set) -> str:
    """Return an error string if code uses a locked syntax feature, else ''."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ''   # SyntaxError reported later by exec
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and 'for_loop' not in unlocked:
            return "for-loop is locked — unlock it in the shop"
        if isinstance(node, ast.While) and 'while_loop' not in unlocked:
            return "while-loop is locked — unlock it in the shop"
        if isinstance(node, ast.If) and 'if_else' not in unlocked:
            return "if/else is locked — unlock it in the shop"
        if isinstance(node, ast.FunctionDef) and 'def_func' not in unlocked:
            return "def is locked — unlock it in the shop"
        if 'variables' not in unlocked:
            if isinstance(node, ast.AugAssign):
                return "variables are locked — unlock in the shop"
            if isinstance(node, ast.Assign):
                tgts = node.targets
                if not (len(tgts) == 1 and isinstance(tgts[0], ast.Name)
                        and tgts[0].id == 'crop'):
                    return "variables are locked — unlock in the shop"
    return ''

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

    if 'is_soil' in state.unlocked_cmds:
        def is_soil():
            t = state.grid.get(state.robot.row, state.robot.col)
            return t is not None and t.state == TileState.EMPTY
        ns['is_soil'] = is_soil

    if 'is_blocked' in state.unlocked_cmds:
        def is_blocked():
            dr, dc = state.robot.direction.value
            nr, nc = state.robot.row + dr, state.robot.col + dc
            t = state.grid.get(nr, nc)
            return t is None or t.state == TileState.OBSTACLE
        ns['is_blocked'] = is_blocked

    if 'crop_type' in state.unlocked_cmds:
        def crop_type():
            t = state.grid.get(state.robot.row, state.robot.col)
            return t.crop_type if t is not None else None
        ns['crop_type'] = crop_type

    if 'position' in state.unlocked_cmds:
        def position():
            return (state.robot.row, state.robot.col)
        ns['position'] = position

    if 'count' in state.unlocked_cmds:
        def count():
            return sum(1 for t in state.grid.tiles.values()
                       if t.state == TileState.READY)
        ns['count'] = count

    if 'for_loop' in state.unlocked_cmds:
        ns['range'] = range

    # scan / teleport / auto_harvest are always available
    def scan(): queue.append(('scan',))
    def teleport(row, col): queue.append(('teleport', int(row), int(col)))
    def auto_harvest(): queue.append(('auto_harvest',))
    ns['scan'] = scan
    ns['teleport'] = teleport
    ns['auto_harvest'] = auto_harvest

    return ns

def run_player_code(code: str, state: GameState):
    state.action_queue.clear()
    state.animating    = False
    state.anim_type    = 'none'
    state.anim_elapsed = 0.0
    state.robot.snap_to(state.grid)
    # Reset per-run counters
    state.run_harvest_count  = 0
    state.run_pumpkin_count  = 0
    state.run_wheat_count    = 0
    state.run_action_count   = 0
    state.run_tiles_visited  = set()
    state.run_has_for        = False
    state.run_has_while      = False
    state.run_has_def        = False
    state.run_teleport_count = 0
    state.run_scan_count     = 0
    state._efficient_done    = False
    state._explorer_done     = False
    state._programmer_done   = False
    state._pumpkin_rush_done = False
    state._master_coder_done = False
    # Detect AST patterns for challenges
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.For):    state.run_has_for   = True
            if isinstance(node, ast.While):  state.run_has_while = True
            if isinstance(node, ast.FunctionDef): state.run_has_def = True
    except SyntaxError:
        pass
    lock_err = _check_syntax_locks(code, state.unlocked_cmds)
    if lock_err:
        state.log(f"Locked: {lock_err}", C_CON_RED)
        return
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
    elif key in CMD_PRICES:
        cost = CMD_PRICES[key]
        if key in state.unlocked_cmds:
            state.log(f"{key} is already unlocked.", C_CON_GRY)
        elif state.points >= cost:
            state.points -= cost
            state.unlocked_cmds.add(key)
            state.log(f"Unlocked {key}!", C_CON_GRN)
        else:
            state.log(f"Need {cost} pts to unlock {key}.", C_CON_RED)

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
        self._overlay   = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 165))
        self.shop_tab_rects: list = []
        self.shop_buy_rects: list = []
        # Sky surface regenerated lazily as time-of-day changes
        self._sky_surf = pygame.Surface((PANEL_W, WIN_H))
        self._sky_tod  = -1.0   # force redraw on first frame
        self._night_ov = pygame.Surface((PANEL_W, WIN_H), pygame.SRCALPHA)
        # Per-tile baked surfaces (pre-rendered once, keyed by (r,c,state_key))
        self._tile_surf_cache: dict = {}
        # Pre-rendered robot ground shadow
        _sh = pygame.Surface((40, 16), pygame.SRCALPHA)
        for _sw, _ssh, _sa in [(40, 16, 55), (32, 12, 80), (22, 8, 105)]:
            pygame.draw.ellipse(_sh, (8, 4, 0, _sa),
                                (20 - _sw//2, 8 - _ssh//2, _sw, _ssh))
        self._robot_shadow = _sh

    # ── top-down tile rendering ───────────────────────────────────────────────

    def _bake_tile(self, r: int, c: int, state_key: str) -> pygame.Surface:
        """Pre-render a tile's static base to a Surface (called once per tile/state)."""
        surf = pygame.Surface((TILE_W, TILE_H))

        # Fast integer LCG seeded by tile position
        h = (r * 73856093 ^ c * 19349663 ^ 83492791) & 0x7FFFFFFF
        def nxt() -> int:
            nonlocal h
            h = (h * 1664525 + 1013904223) & 0x7FFFFFFF
            return h

        if state_key == 'obs':
            # ── Stone obstacle ────────────────────────────────────────────────
            surf.fill((86, 80, 72))
            grey_vars = [(64, 58, 50), (100, 94, 86), (74, 68, 60), (94, 88, 80), (78, 72, 64)]
            for _ in range(8):
                ex = nxt() % (TILE_W - 14) + 7
                ey = nxt() % (TILE_H - 10) + 5
                ew = nxt() % 18 + 8
                eh = nxt() % 10 + 5
                pygame.draw.ellipse(surf, grey_vars[nxt() % 5],
                                    (ex - ew//2, ey - eh//2, ew, eh))
            # Crack lines
            for _ in range(4):
                x1 = nxt() % (TILE_W - 16) + 8
                y1 = nxt() % (TILE_H - 12) + 6
                x2 = x1 + (nxt() % 16) - 8
                y2 = y1 + (nxt() % 12) - 6
                pygame.draw.aaline(surf, (48, 42, 36), (x1, y1), (x2, y2))
            # Lit far edge (top 2 rows)
            pygame.draw.rect(surf, (98, 92, 84), (0, 0, TILE_W, 2))
            pygame.draw.rect(surf, (102, 96, 88), (0, 0, TILE_W, 1))
            # Depth strip gradient
            for i in range(TILE_DEPTH):
                t = i / max(1, TILE_DEPTH - 1)
                dc = _lerp_c((54, 48, 42), (34, 28, 22), t)
                pygame.draw.rect(surf, dc, (0, TILE_H - TILE_DEPTH + i, TILE_W, 1))

        else:
            # ── Soil tile ─────────────────────────────────────────────────────
            wet = (state_key == 'wet')
            if wet:
                base = (72, 48, 26)
                var_cols = [(54, 34, 16), (86, 60, 34), (64, 42, 22), (78, 54, 30),
                            (58, 38, 18), (90, 64, 38)]
                hi_col   = (84, 58, 32)
                far_edge = (46, 26, 10)
                dep0     = (56, 34, 14)
            else:
                base = (100, 70, 44)
                var_cols = [(76, 50, 28), (122, 90, 58), (88, 62, 38), (112, 82, 54),
                            (80, 56, 32), (116, 86, 56)]
                hi_col   = (116, 86, 56)
                far_edge = (62, 40, 20)
                dep0     = (70, 46, 24)

            surf.fill(base)

            # Large organic variation patches (9 ellipses)
            for _ in range(9):
                ex = nxt() % (TILE_W - 12) + 6
                ey = nxt() % (TILE_H -  8) + 4
                ew = nxt() % 24 + 10
                eh = nxt() % 14 +  5
                pygame.draw.ellipse(surf, var_cols[nxt() % 6],
                                    (ex - ew//2, ey - eh//2, ew, eh))

            # Small texture pebbles/dirt clods (14 scattered dots)
            for _ in range(14):
                px = nxt() % (TILE_W - 6) + 3
                py = nxt() % (TILE_H - 6) + 3
                pr = nxt() % 3 + 1
                pygame.draw.circle(surf, var_cols[nxt() % 6], (px, py), pr)

            # Soft upper-left highlight (3 nested ellipses, decreasing)
            for i in range(3):
                hw = max(4, TILE_W // 3 - i * 7)
                hh = max(3, TILE_H // 3 - i * 5)
                pygame.draw.ellipse(surf, hi_col,
                                    (TILE_W // 5 - hw//2, TILE_H // 6 - hh//2, hw, hh))

            # Far edge shadow: top 3 rows, darkening toward y=0
            for i in range(3):
                dv = 16 * (3 - i)
                dc = (max(0, far_edge[0]-dv), max(0, far_edge[1]-dv), max(0, far_edge[2]-dv))
                pygame.draw.rect(surf, dc, (0, i, TILE_W, 1))

            # Depth strip: gradient from dep0 to nearly-black
            for i in range(TILE_DEPTH):
                t  = i / max(1, TILE_DEPTH - 1)
                dc = _lerp_c(dep0, (36, 20, 6), t)
                pygame.draw.rect(surf, dc, (0, TILE_H - TILE_DEPTH + i, TILE_W, 1))

        return surf

    def _draw_sprout(self, sx: int, sy: int, tile):
        """Growing plant — 3 stages, layered organic shapes."""
        s    = self.screen
        cx   = sx + TILE_W // 2
        cy   = sy + TILE_H // 2 - 4
        crop = CROPS.get(tile.crop_type, CROPS['carrot'])
        prog = max(0.0, 1.0 - tile.growth_turns / max(1, crop.turns))

        if tile.crop_type == 'wheat':
            # Stage 1 (<0.4): sparse tiny green nubs
            # Stage 2 (0.4–0.75): growing shoots with stems
            # Stage 3 (>0.75): golden heads just forming
            num = max(2, int(prog * 8) + 2)
            for i in range(num):
                ang  = math.radians(i * (360 / num) + 12)
                rad  = 3 + prog * 8
                tx   = int(cx + math.cos(ang) * rad)
                ty   = int(cy + math.sin(ang) * rad * 0.65)
                ht   = max(2, int(3 + prog * 5))
                if prog > 0.7:
                    gcol = _lerp_c((60, 108, 30), (190, 155, 45), (prog - 0.7) / 0.3)
                else:
                    gcol = (55 + int(prog*30), 108 + int(prog*10), 28)
                pygame.draw.line(s, (36, 76, 18), (tx, ty), (tx, ty - ht), 1)
                pygame.draw.circle(s, gcol, (tx, ty - ht), 1 + (1 if prog > 0.6 else 0))

        elif tile.crop_type == 'pumpkin':
            # Stage 1: 2 small leaf lobes
            # Stage 2: spreading vine cluster + orange hint
            # Stage 3: large orange blob with green
            r_base = int(2 + prog * 9)
            g_dk   = (38, 88, 22)
            g_main = (56 + int(prog*16), 118 - int(prog*8), 32)
            # Green shoot lobes
            for i in range(max(1, int(prog * 4) + 1)):
                ang = math.radians(i * (360 / max(1, int(prog*4)+1)) + 20)
                ox  = int(math.cos(ang) * r_base * 0.5)
                oy  = int(math.sin(ang) * r_base * 0.4)
                pygame.draw.circle(s, g_dk,   (cx+ox+1, cy+oy+1), r_base)
                pygame.draw.circle(s, g_main, (cx+ox,   cy+oy),   r_base)
            # Orange tinge grows from stage 2 onward
            if prog > 0.35:
                t_o = (prog - 0.35) / 0.65
                oc  = int(t_o * 150)
                pygame.draw.circle(s, (100 + oc, 50 + oc//3, 10), (cx, cy), max(1, int(r_base*0.75)))

        else:  # carrot
            # Feathery leaf crown growing outward
            num = max(2, int(prog * 6) + 2)
            for i in range(num):
                ang = math.radians(i * (360 / num) + 8)
                r   = max(1, int(2 + prog * 10))
                lx  = int(cx + math.cos(ang) * r * 0.75)
                ly  = int(cy + math.sin(ang) * r * 0.55)
                lw  = max(2, int(2 + prog * 6))
                lh  = max(1, int(1 + prog * 4))
                g_dk   = (38, 82, 20)
                g_main = (60, 116, 34) if i % 2 == 0 else (50, 102, 26)
                pygame.draw.ellipse(s, g_dk,   (lx - lw//2+1, ly - lh//2+1, lw, lh))
                pygame.draw.ellipse(s, g_main, (lx - lw//2,   ly - lh//2,   lw, lh))

    def _draw_crop(self, sx: int, sy: int, tile):
        """Full mature crop — rich layered painterly shapes."""
        s  = self.screen
        cx = sx + TILE_W // 2
        cy = sy + TILE_H // 2 - 4

        if tile.crop_type == 'wheat':
            # Warm golden wheat — ring of drooping oval heads with stems
            stem_col = (68, 110, 38)
            heads    = [(170, 138, 36), (198, 162, 50), (218, 186, 68)]
            for j, ang_deg in enumerate(range(0, 360, 40)):
                ang = math.radians(ang_deg)
                r   = 11
                hx  = int(cx + math.cos(ang) * r)
                hy  = int(cy + math.sin(ang) * r * 0.68)
                # Stem
                pygame.draw.aaline(s, stem_col, (cx, cy), (hx, hy))
                # Head — 3 layered ellipses for volume
                pygame.draw.ellipse(s, heads[0], (hx - 5, hy - 6, 10, 12))
                pygame.draw.ellipse(s, heads[1], (hx - 4, hy - 5,  8, 10))
                pygame.draw.ellipse(s, heads[2], (hx - 2, hy - 4,  4,  6))
            # Centre tuft
            for r_, c_ in [(5, stem_col), (3, (98, 148, 52)), (2, (128, 178, 64))]:
                pygame.draw.circle(s, c_, (cx, cy), r_)

        elif tile.crop_type == 'pumpkin':
            # Soft cast shadow
            shad = pygame.Surface((38, 13), pygame.SRCALPHA)
            pygame.draw.ellipse(shad, (12, 4, 0, 80), (0, 0, 38, 13))
            s.blit(shad, (cx - 19, cy + 9))

            # 4-lobe pumpkin body: offset ellipses per lobe
            for la_d in (0, 90, 180, 270):
                la  = math.radians(la_d)
                lx_ = int(cx + math.cos(la) * 4)
                ly_ = int(cy + math.sin(la) * 3)
                pygame.draw.ellipse(s, (140, 74, 14), (lx_ - 11, ly_ - 9, 22, 18))

            # Main body — 3 layered circles for depth
            for col, r_ in [((142, 76, 14), 14), ((188, 106, 28), 13), ((212, 130, 42), 11)]:
                pygame.draw.circle(s, col, (cx, cy), r_)

            # Highlight upper-left
            pygame.draw.ellipse(s, (236, 162, 64), (cx - 8, cy - 8,  10,  8))
            pygame.draw.ellipse(s, (252, 190, 88), (cx - 5, cy - 6,   5,  4))

            # Shadow lower-right
            pygame.draw.ellipse(s, (106, 52,  8), (cx + 3, cy + 4,   9,  7))

            # Lobe divider grooves
            for la_d in (30, 150, 270):
                la = math.radians(la_d)
                pygame.draw.line(s, (120, 60, 10), (cx, cy),
                                 (int(cx + math.cos(la)*13), int(cy + math.sin(la)*11)), 2)

            # Curling green stem
            for r_, off, gc in [(4, 0, (44, 94, 22)), (3, -1, (64, 122, 34)), (2, -1, (86, 148, 48))]:
                pygame.draw.circle(s, gc, (cx + off, cy - 13 + off), r_)

        else:  # carrot — lush layered leaf rosette
            # Leaf petals — 6 directional leaves with shadow + highlight layers
            leaf_params = [
                (0,   13, 10, (48,  96, 24)),
                (60,  12,  9, (62, 112, 32)),
                (120, 13, 10, (44,  90, 22)),
                (180, 12,  9, (66, 118, 36)),
                (240, 13, 10, (52, 102, 28)),
                (300, 12,  9, (58, 110, 30)),
            ]
            for ang_d, lw, lh, col in leaf_params:
                ang = math.radians(ang_d)
                lx  = int(cx + math.cos(ang) * 9)
                ly  = int(cy + math.sin(ang) * 7)
                shadow_c = (max(0,col[0]-12), max(0,col[1]-12), max(0,col[2]-6))
                pygame.draw.ellipse(s, shadow_c, (lx - lw//2+1, ly - lh//2+1, lw, lh))
                pygame.draw.ellipse(s, col,       (lx - lw//2,   ly - lh//2,   lw, lh))

            # Centre hub layers
            for r_, c_ in [(6, (48, 96, 24)), (4, (72, 128, 40)), (3, (88, 148, 50))]:
                pygame.draw.circle(s, c_, (cx, cy), r_)

            # Orange carrot crown hint
            pygame.draw.circle(s, (195, 108, 38), (cx, cy), 3)
            pygame.draw.circle(s, (218, 134, 56), (cx, cy), 2)
            pygame.draw.circle(s, (235, 158, 74), (cx, cy), 1)

    def _draw_pips(self, sx: int, sy: int, tile):
        """Growth progress circles along the bottom edge of the tile."""
        crop_info = CROPS.get(tile.crop_type, CROPS['carrot'])
        total = max(1, crop_info.turns)
        done  = total - tile.growth_turns
        num   = min(total, 6)
        step  = 9
        bx0   = sx + TILE_W // 2 - (num * step) // 2
        by    = sy + TILE_H - TILE_DEPTH - 6
        for i in range(num):
            filled = i < round(done / total * num)
            if filled:
                pygame.draw.circle(self.screen, (88, 148, 48), (bx0 + i*step + 3, by + 2), 3)
                pygame.draw.circle(self.screen, (112, 178, 64),(bx0 + i*step + 3, by + 2), 2)
            else:
                pygame.draw.circle(self.screen, (58, 36, 16),  (bx0 + i*step + 3, by + 2), 3)
                pygame.draw.circle(self.screen, (72, 48, 24),  (bx0 + i*step + 3, by + 2), 2)

    def _draw_locked(self, sx: int, sy: int):
        """Locked / purchasable tile — dark textured base + padlock."""
        s  = self.screen
        ck = ('__locked__', 0, 0)
        if ck not in self._tile_surf_cache:
            lsurf = pygame.Surface((TILE_W, TILE_H))
            lsurf.fill((26, 16, 8))
            h = 0xA3F713
            for _ in range(7):
                h  = (h * 1664525 + 1013904223) & 0x7FFFFFFF
                ex = h % (TILE_W - 12) + 6
                h  = (h * 1664525 + 1013904223) & 0x7FFFFFFF
                ey = h % (TILE_H - 10) + 5
                h  = (h * 1664525 + 1013904223) & 0x7FFFFFFF
                ew = h % 16 + 8
                pygame.draw.ellipse(lsurf, (18, 10, 4), (ex - ew//2, ey - 4, ew, 8))
            pygame.draw.rect(lsurf, (18, 10, 4), (0, 0, TILE_W, 2))
            for i in range(TILE_DEPTH):
                t  = i / max(1, TILE_DEPTH - 1)
                dc = _lerp_c((22, 12, 4), (12, 6, 2), t)
                pygame.draw.rect(lsurf, dc, (0, TILE_H - TILE_DEPTH + i, TILE_W, 1))
            self._tile_surf_cache[ck] = lsurf
        s.blit(self._tile_surf_cache[ck], (sx, sy))

        cx = sx + TILE_W // 2
        cy = sy + TILE_H // 2

        # Padlock body — layered for depth
        for col, rect in [
            ((44, 30, 16), (cx - 7, cy + 1, 14, 11)),
            ((58, 42, 24), (cx - 6, cy + 2, 12, 9)),
        ]:
            pygame.draw.rect(s, col, rect, border_radius=2)
        # Keyhole
        pygame.draw.circle(s, (32, 20, 8), (cx, cy + 6), 3)
        pygame.draw.circle(s, (22, 12, 4), (cx, cy + 6), 2)

        # Shackle (U shape)
        pygame.draw.rect(s, (50, 36, 20), (cx - 4, cy - 8, 8, 9))
        pygame.draw.rect(s, (26, 16, 8),  (cx - 2, cy - 6, 4, 7))

        hint = self.font_small.render("[S]", True, (56, 40, 22))
        s.blit(hint, (cx - hint.get_width() // 2, sy + TILE_H - hint.get_height() - 4))

    def draw_tile(self, sx: int, sy: int, tile, r: int, c: int):
        """Draw a tile using pre-baked surface + dynamic crop overlay."""
        if tile.state == TileState.OBSTACLE:
            sk = 'obs'
        elif tile.state == TileState.PLANTED:
            sk = 'wet'
        else:
            sk = 'dry'
        ck = (r, c, sk)
        if ck not in self._tile_surf_cache:
            self._tile_surf_cache[ck] = self._bake_tile(r, c, sk)
        self.screen.blit(self._tile_surf_cache[ck], (sx, sy))

        if tile.state == TileState.PLANTED:
            self._draw_sprout(sx, sy, tile)
            self._draw_pips(sx, sy, tile)
        elif tile.state == TileState.READY:
            self._draw_crop(sx, sy, tile)

    # ── top-down robot ────────────────────────────────────────────────────────

    def draw_robot(self, robot: Robot, anim_type: str, t_raw: float,
                   cosmetics: set = None, tod: float = 0.25):
        s   = self.screen
        cos = cosmetics or set()
        bob = int(-math.sin(t_raw * math.pi) * 3) if anim_type == 'move' else 0
        cx  = int(robot.px)
        cy  = int(robot.py) + bob

        # Soft ground shadow (pre-rendered SRCALPHA surface)
        s.blit(self._robot_shadow, (cx - 20, cy + 4))

        # ── Body / overalls ───────────────────────────────────────────────────
        if 'overalls_blue' in cos:
            body_colors = ((18, 42, 90), (30, 72, 160), (50, 100, 200), (70, 120, 220))
        else:
            body_colors = ((38, 58, 96), (60, 94, 148), (80, 118, 172), (92, 132, 182))
        pygame.draw.ellipse(s, body_colors[0], (cx - 10, cy - 6, 20, 16))
        pygame.draw.ellipse(s, body_colors[1], (cx -  9, cy - 7, 18, 14))
        pygame.draw.ellipse(s, body_colors[2], (cx - 6, cy - 8, 12, 8))
        pygame.draw.ellipse(s, body_colors[3], (cx - 3, cy - 7,  6, 6))

        # ── Red scarf ─────────────────────────────────────────────────────────
        if 'scarf_red' in cos:
            pygame.draw.ellipse(s, (160, 30, 20), (cx - 9, cy - 4, 18, 7))
            pygame.draw.ellipse(s, (200, 50, 40), (cx - 7, cy - 5, 14, 5))

        # ── Straw hat ─────────────────────────────────────────────────────────
        if 'hat_orange' in cos:
            hat_c = [(110, 58, 10), (170, 90, 20), (200, 120, 30), (120, 70, 18), (150, 100, 28), (180, 140, 60), (60, 30, 8), (80, 46, 16)]
        elif 'hat_dark' in cos:
            hat_c = [(20, 18, 16), (40, 35, 28), (60, 50, 38), (28, 22, 16), (50, 40, 30), (70, 60, 48), (14, 10, 6), (26, 20, 12)]
        else:
            hat_c = [(132, 96, 26), (158, 120, 40), (178, 142, 54), (148, 112, 32), (186, 152, 52), (208, 176, 72), (82, 46, 18), (98, 58, 26)]
        # Wide brim
        pygame.draw.ellipse(s, hat_c[0], (cx - 18, cy - 23, 36, 23))
        pygame.draw.ellipse(s, hat_c[1], (cx - 17, cy - 25, 34, 22))
        pygame.draw.ellipse(s, hat_c[2], (cx - 14, cy - 26, 28, 21))
        # Dome
        pygame.draw.ellipse(s, hat_c[3], (cx - 10, cy - 31, 20, 17))
        pygame.draw.ellipse(s, hat_c[4], (cx -  9, cy - 32, 18, 16))
        pygame.draw.ellipse(s, hat_c[5], (cx -  5, cy - 33,  9,  9))
        # Hat band
        pygame.draw.ellipse(s, hat_c[6], (cx - 11, cy - 18, 22,  7))
        pygame.draw.ellipse(s, hat_c[7], (cx - 10, cy - 19, 20,  6))

        # ── Face direction dot on brim edge ───────────────────────────────────
        ar  = math.radians(robot.visual_angle)
        fr  = 12.0
        fdx = math.cos(ar) * fr
        fdy = math.sin(ar) * fr * 0.55
        fx  = int(cx + fdx)
        fy  = int(cy - 22 + fdy)
        if 'golden_skin' in cos:
            skin_c = ((220, 180, 60), (200, 155, 40), (120, 80, 10))
        else:
            skin_c = ((200, 155, 100), (178, 130, 78), (60, 36, 14))
        pygame.draw.circle(s, skin_c[0], (fx, fy), 4)
        pygame.draw.circle(s, skin_c[1], (fx, fy), 2)
        pygame.draw.circle(s, skin_c[2], (fx, fy), 1)

        # ── Lantern (night only) ──────────────────────────────────────────────
        if 'lantern' in cos and tod > 0.45:
            lx, ly = cx + 10, cy - 2
            # Glow halo
            glow = pygame.Surface((26, 26), pygame.SRCALPHA)
            night_alpha = min(180, int(_night_alpha(tod) * 1.2))
            pygame.draw.circle(glow, (255, 200, 80, night_alpha // 2), (13, 13), 13)
            s.blit(glow, (lx - 13, ly - 13))
            pygame.draw.circle(s, (200, 140, 30), (lx, ly), 4)
            pygame.draw.circle(s, (255, 200, 80), (lx, ly), 2)

    def _draw_scarecrow(self, vrec: pygame.Rect):
        s  = self.screen
        sx = vrec.right + 22
        sy = vrec.centery - 10
        # Post
        pygame.draw.rect(s, (90, 60, 20), (sx - 2, sy - 10, 4, 32))
        # Crossbar
        pygame.draw.rect(s, (110, 75, 28), (sx - 14, sy, 28, 4))
        # Straw hat
        pygame.draw.ellipse(s, (158, 120, 40), (sx - 10, sy - 22, 20, 12))
        pygame.draw.ellipse(s, (178, 142, 54), (sx - 7, sy - 24, 14, 10))
        # Face
        pygame.draw.circle(s, (220, 180, 100), (sx, sy - 12), 6)
        pygame.draw.circle(s, (60, 36, 14), (sx - 2, sy - 13), 1)
        pygame.draw.circle(s, (60, 36, 14), (sx + 2, sy - 13), 1)
        # Shirt
        pygame.draw.ellipse(s, (160, 40, 20), (sx - 8, sy + 4, 16, 12))

    def _draw_well(self, vrec: pygame.Rect):
        s  = self.screen
        sx = vrec.left - 28
        sy = vrec.centery + 20
        # Stone base
        pygame.draw.ellipse(s, (80, 72, 64), (sx - 16, sy - 4, 32, 14))
        pygame.draw.ellipse(s, (100, 92, 82), (sx - 14, sy - 6, 28, 12))
        # Well posts
        pygame.draw.rect(s, (60, 45, 28), (sx - 14, sy - 20, 4, 18))
        pygame.draw.rect(s, (60, 45, 28), (sx + 10, sy - 20, 4, 18))
        # Roof beam
        pygame.draw.rect(s, (80, 55, 30), (sx - 15, sy - 24, 30, 5))
        # Rope
        pygame.draw.line(s, (120, 90, 40), (sx, sy - 22), (sx, sy - 6), 2)

    # ── top-down environment ──────────────────────────────────────────────────

    def _draw_left_bg(self, grid: Grid, tod: float = 0.25):
        s = self.screen

        # ── Sky gradient (lazily regenerated per 0.4% tod step) ───────────────
        sky_top, sky_bot = _sky_colors(tod)
        if abs(tod - self._sky_tod) > 0.004:
            self._sky_tod = tod
            for _y in range(WIN_H):
                _t  = min(1.0, _y / (WIN_H * 0.72))
                _c  = _lerp_c(sky_top, sky_bot, _t)
                self._sky_surf.fill(_c, (0, _y, PANEL_W, 1))
        s.blit(self._sky_surf, (0, 0))

        # Faint horizon glow strip (warm lighter band near horizon)
        hz_y   = int(WIN_H * 0.30)
        hz_col = _lerp_c(sky_bot, (235, 225, 205), 0.28)
        for dy in range(-3, 4):
            alpha = max(0, 55 - abs(dy) * 14)
            hsurf = pygame.Surface((PANEL_W, 1), pygame.SRCALPHA)
            hsurf.fill((*hz_col, alpha))
            s.blit(hsurf, (0, hz_y + dy))

        vrec     = grid.visual_rect()
        ground_y = vrec.bottom - 4

        # ── Grass ground — multiple layered tones ─────────────────────────────
        pygame.draw.rect(s, (46, 74, 28),  (0, ground_y + 6, PANEL_W, WIN_H))
        pygame.draw.rect(s, (52, 84, 34),  (0, ground_y,     PANEL_W, WIN_H))

        # Organic grass edge: seeded ellipses, random heights and green tones
        gh = 0xDEAD1337
        for i in range(0, PANEL_W + 18, 9):
            gh = (gh * 1664525 + 1013904223) & 0x7FFFFFFF
            jitter = (gh % 8) - 4
            hvar   = (gh % 10) + 4
            gh = (gh * 1664525 + 1013904223) & 0x7FFFFFFF
            gr  = 52 + gh % 18
            gg  = 90 + gh % 22
            gb  = 28 + gh % 14
            pygame.draw.ellipse(s, (gr, gg, gb),
                                (i - 7, ground_y - hvar//2 + jitter, 16, hvar + 6))

        # ── Farm platform: raised earth side face below grid ──────────────────
        plat_y = vrec.bottom - 2
        plat_h = 10
        for i in range(plat_h):
            t   = i / plat_h
            col = _lerp_c((72, 48, 26), (36, 20, 8), t)
            pygame.draw.rect(s, col, (vrec.x - 4, plat_y + i, vrec.w + 8, 1))
        # Grass fringe along top of platform
        for i in range(vrec.x - 2, vrec.x + vrec.w + 4, 7):
            pygame.draw.ellipse(s, (60, 96, 36), (i - 4, plat_y - 4, 9, 6))

        # ── Ambient-occlusion shadow under the grid block ─────────────────────
        ao_w   = vrec.w + 16
        ao_h   = 12
        ao_s   = pygame.Surface((ao_w, ao_h), pygame.SRCALPHA)
        for i in range(6):
            alpha = int((1.0 - i / 6) * 48)
            pygame.draw.rect(ao_s, (0, 0, 0, alpha),
                             (i, i, ao_w - i * 2, ao_h - i * 2))
        s.blit(ao_s, (vrec.x - 8, vrec.y - 6))

    def _draw_time_indicator(self, s, tod: float, day: int):
        """Small arc + sun/moon dial showing current time of day."""
        cx, cy = PANEL_W - 80, 60
        arc_r  = 26

        # Horizon line
        h_col = (85, 68, 45) if tod < 0.5 else (55, 58, 88)
        pygame.draw.line(s, h_col, (cx - arc_r - 4, cy), (cx + arc_r + 4, cy), 1)

        # Semi-circle arc (upper half)
        arc_col = (130, 110, 75) if tod < 0.5 else (65, 72, 115)
        arc_rect = pygame.Rect(cx - arc_r, cy - arc_r, arc_r * 2, arc_r * 2)
        pygame.draw.arc(s, arc_col, arc_rect, 0, math.pi, 1)

        if tod < 0.5:
            # Sun: left at dawn (0.0) → top at midday (0.25) → right at dusk (0.5)
            sun_ang = math.pi * (1.0 - tod / 0.5)
            sx = int(cx + arc_r * math.cos(sun_ang))
            sy = int(cy - arc_r * math.sin(sun_ang))
            pygame.draw.circle(s, (255, 210,  70), (sx, sy), 9)
            pygame.draw.circle(s, (255, 238, 140), (sx, sy), 6)
            pygame.draw.circle(s, (255, 252, 210), (sx, sy), 3)
        else:
            # Moon: left at dusk (0.5) → top at midnight (0.75) → right at dawn (1.0)
            moon_frac = (tod - 0.5) / 0.5
            moon_ang  = math.pi * (1.0 - moon_frac)
            mx = int(cx + arc_r * math.cos(moon_ang))
            my = int(cy - arc_r * math.sin(moon_ang))
            pygame.draw.circle(s, (190, 200, 225), (mx, my), 7)
            pygame.draw.circle(s, (215, 222, 240), (mx, my), 5)
            # Crescent cutout using approximate sky colour at that y position
            sky_top, sky_bot = _sky_colors(tod)
            sky_t = min(1.0, my / (WIN_H * 0.62))
            sky_here = _lerp_c(sky_top, sky_bot, sky_t)
            pygame.draw.circle(s, sky_here, (mx + 4, my - 2), 5)

        # Day counter below arc
        day_lbl = self.font_small.render(f"Day {day}", True, C_WARM_GRY)
        s.blit(day_lbl, (cx - day_lbl.get_width() // 2, cy + arc_r + 4))

    def _draw_wood_panel(self):
        s = self.screen
        # 4-layer walnut base — subtle gradient from left to right
        for i, col in enumerate([(32, 18, 8), (36, 22, 10), (40, 26, 12), (42, 28, 14)]):
            pygame.draw.rect(s, col, (PANEL_W + i * (PANEL_W//4), 0, PANEL_W//4 + 2, WIN_H))

        # Diagonal grain lines (slightly off-45°, alternating dark and warm-light)
        grain_stride = 44
        for base_y in range(-WIN_H, WIN_H * 2, grain_stride):
            # Dark grain
            pygame.draw.aaline(s, (24, 12, 4),
                               (PANEL_W, base_y), (WIN_W, base_y + WIN_W // 3))
            # Light grain (slightly offset)
            pygame.draw.aaline(s, (52, 36, 18),
                               (PANEL_W, base_y + grain_stride // 2),
                               (WIN_W, base_y + grain_stride // 2 + WIN_W // 3))

        # Horizontal plank seams every ~56px
        for y in range(0, WIN_H, 56):
            pygame.draw.aaline(s, (22, 10, 2), (PANEL_W, y),     (WIN_W, y))
            pygame.draw.aaline(s, (54, 38, 20),(PANEL_W, y + 1), (WIN_W, y + 1))

        # Left divider strip — 3 layers for chiselled edge
        pygame.draw.rect(s, (46, 30, 14), (PANEL_W,     0, 4, WIN_H))
        pygame.draw.rect(s, (62, 46, 26), (PANEL_W + 1, 0, 2, WIN_H))
        pygame.draw.rect(s, (70, 54, 32), (PANEL_W + 1, 0, 1, WIN_H))

    def _draw_run_button(self, btn: pygame.Rect, is_running: bool, hover: bool):
        s = self.screen
        if is_running:
            bg0, bg1 = (50, 30, 12), (60, 38, 16)
            txt_c    = (92, 70, 46)
            label    = "Running..."
        elif hover:
            bg0, bg1 = (118, 78, 36), (142, 98, 50)
            txt_c    = (252, 230, 178)
            label    = "Run  >"
        else:
            bg0, bg1 = (86, 52, 22), (106, 68, 30)
            txt_c    = (244, 222, 170)
            label    = "Run  >"

        # Drop shadow (inset look)
        pygame.draw.rect(s, (20, 10, 2),
                         pygame.Rect(btn.x + 3, btn.y + 3, btn.w, btn.h), border_radius=5)

        # Button face — two-tone top-to-bottom gradient (2 halves)
        h2 = btn.h // 2
        pygame.draw.rect(s, bg0, btn, border_radius=5)
        pygame.draw.rect(s, bg1, pygame.Rect(btn.x, btn.y, btn.w, h2), border_radius=5)

        # Top highlight edge (carved wood lit-top)
        pygame.draw.aaline(s, (148, 108, 58), (btn.x + 6, btn.y + 2), (btn.right - 6, btn.y + 2))

        # Bottom shadow edge
        pygame.draw.aaline(s, (20, 8, 2), (btn.x + 6, btn.bottom - 3), (btn.right - 6, btn.bottom - 3))

        # Border
        pygame.draw.rect(s, (52, 28, 8), btn, 2, border_radius=5)

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
        tab_w   = SHOP_W // 4
        tab_labels = ["Grid", "Crops", "Commands", "Challenges"]
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
        elif state.shop_tab == 2:
            self._draw_shop_cmds_tab(s, content_y, content_h, state, mouse_pos)
        else:
            self._draw_shop_challenges_tab(s, content_y, content_h, state)

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
        x0      = SHOP_X + 8
        row_w   = SHOP_W - 28   # leave 12px for scrollbar on right
        scroll  = state.shop_cmd_scroll

        # Clip to content area
        clip = pygame.Rect(x0, cy, row_w, ch)
        s.set_clip(clip)

        y       = cy - scroll + 4
        parity  = 0

        for title, items in SHOP_CMDS:
            # Section header
            if cy <= y + _SHOP_CMD_SEC_H and y < cy + ch:
                pygame.draw.rect(s, (40, 26, 14),
                                 (x0, y, row_w, _SHOP_CMD_SEC_H), border_radius=3)
                hdr_s = self.font_label.render(title.upper(), True, C_WARM_GRY)
                s.blit(hdr_s, (x0 + 8, y + 4))
            y += _SHOP_CMD_SEC_H + _SHOP_CMD_SEC_GAP

            for key, sig, desc, example in items:
                row_top = y
                row_bot = y + _SHOP_CMD_ROW_H
                if row_bot >= cy and row_top < cy + ch:
                    owned    = key in state.unlocked_cmds
                    cost     = CMD_PRICES.get(key, 10)
                    row      = pygame.Rect(x0, y, row_w, _SHOP_CMD_ROW_H)
                    bg_col   = C_SHOP_ROW_A if parity % 2 == 0 else C_SHOP_ROW_B
                    pygame.draw.rect(s, bg_col,    row, border_radius=4)
                    pygame.draw.rect(s, C_WOOD_LT, row, 1, border_radius=4)

                    txt_col  = C_WARM_WHT if owned else C_SHOP_LOCK_TXT
                    desc_col = C_WARM_GRY if owned else (80, 65, 50)

                    s.blit(self.font_ui.render(sig, True, txt_col),
                           (row.x + 12, row.y + 7))
                    s.blit(self.font_label.render(desc, True, desc_col),
                           (row.x + 12, row.y + 27))

                    ex_line = example.split('\n')[0]
                    ex_surf = self.font_mono.render(ex_line, True, C_CON_WHT)
                    ex_rect = pygame.Rect(row.x + 12, row.y + 47,
                                         ex_surf.get_width() + 10, ex_surf.get_height() + 4)
                    pygame.draw.rect(s, (28, 18, 8), ex_rect, border_radius=3)
                    pygame.draw.rect(s, C_DIVIDER,   ex_rect, 1, border_radius=3)
                    s.blit(ex_surf, (ex_rect.x + 5, ex_rect.y + 2))

                    cost_col = C_GOLD if not owned else C_WARM_GRY
                    s.blit(self.font_label.render(f"{cost} pts", True, cost_col),
                           (row.x + 12, row.y + _SHOP_CMD_ROW_H - 18))

                    self._shop_buy_btn(s, row.right - 78, row.y + 12, 66, 30,
                                       key, state.points >= cost, owned, mouse_pos)

                y    += _SHOP_CMD_ROW_H + _SHOP_CMD_ROW_GAP
                parity += 1

        s.set_clip(None)

        # Scrollbar
        if _SHOP_CMD_MAX_SCROLL > 0:
            sb_x    = SHOP_X + SHOP_W - 14
            thumb_h = max(20, int(ch * ch / (ch + _SHOP_CMD_MAX_SCROLL)))
            thumb_y = cy + int(scroll / _SHOP_CMD_MAX_SCROLL * (ch - thumb_h))
            pygame.draw.rect(s, (40, 28, 16), (sb_x, cy, 8, ch), border_radius=4)
            pygame.draw.rect(s, C_WARM_GRY,   (sb_x, thumb_y, 8, thumb_h), border_radius=4)

    def _draw_shop_challenges_tab(self, s, cy, ch, state: GameState):
        x0   = SHOP_X + 16
        row_h = 90
        pad   = 8

        completed_total = len(state.completed_challenge_keys)
        hdr = self.font_ui.render(
            f"Active Challenges  ·  Completed: {completed_total}/{len(CHALLENGE_POOL)}",
            True, C_WARM_WHT)
        s.blit(hdr, (x0, cy + 6))

        clip_rect = pygame.Rect(SHOP_X, cy + 30, SHOP_W, ch - 30)
        s.set_clip(clip_rect)

        scroll = state.shop_ch_scroll
        y = cy + 34 - scroll

        for ch_obj in state.active_challenges:
            row = pygame.Rect(SHOP_X + 8, y, SHOP_W - 16, row_h)
            if row.bottom < clip_rect.top or row.top > clip_rect.bottom:
                y += row_h + pad
                continue

            # Flash completed rows green
            if ch_obj.completed and ch_obj.flash_timer > 0:
                alpha = int(min(1.0, ch_obj.flash_timer) * 80)
                flash_surf = pygame.Surface((row.w, row.h), pygame.SRCALPHA)
                flash_surf.fill((60, 200, 80, alpha))
                bg_col = (38, 52, 38)
            elif ch_obj.completed:
                bg_col = (28, 42, 28)
            else:
                bg_col = (26, 22, 14)

            pygame.draw.rect(s, bg_col, row, border_radius=6)
            if ch_obj.completed and ch_obj.flash_timer > 0:
                s.blit(flash_surf, row.topleft)
            pygame.draw.rect(s, C_WOOD_LT, row, 1, border_radius=6)

            # Name
            name_col = C_GOLD if not ch_obj.completed else (120, 200, 90)
            name_surf = self.font_ui.render(ch_obj.name, True, name_col)
            s.blit(name_surf, (row.x + 12, row.y + 10))

            # Description
            desc_surf = self.font_label.render(ch_obj.desc, True, C_WARM_GRY)
            s.blit(desc_surf, (row.x + 12, row.y + 30))

            # Reward
            rew_surf = self.font_small.render(
                f"Reward: {ch_obj.reward_name}", True, (180, 160, 90))
            s.blit(rew_surf, (row.x + 12, row.y + 48))

            # Progress bar
            prog = min(ch_obj.progress, ch_obj.goal)
            bar_x = row.x + 12
            bar_y = row.y + row_h - 16
            bar_w = row.w - 24
            bar_h = 8
            pygame.draw.rect(s, (40, 28, 16), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
            if ch_obj.goal > 0:
                fill_w = int(bar_w * prog / ch_obj.goal)
                if fill_w > 0:
                    fill_col = (80, 180, 60) if not ch_obj.completed else (60, 200, 80)
                    pygame.draw.rect(s, fill_col, (bar_x, bar_y, fill_w, bar_h), border_radius=4)
            prog_lbl = self.font_small.render(
                f"{prog}/{ch_obj.goal}" + ("  ✓" if ch_obj.completed else ""), True,
                (140, 200, 100) if ch_obj.completed else C_WARM_GRY)
            s.blit(prog_lbl, (bar_x + bar_w - prog_lbl.get_width(), bar_y - 14))

            y += row_h + pad

        # Completed note
        if not state.active_challenges:
            note = self.font_ui.render("All challenges complete!", True, C_GOLD)
            s.blit(note, (SHOP_X + (SHOP_W - note.get_width()) // 2, cy + 80))

        s.set_clip(None)

    # ── main draw call ────────────────────────────────────────────────────────

    def draw(self, state: GameState,
             editor: EditorComponent,
             console: ConsoleComponent,
             btn_rect: pygame.Rect,
             btn_hover: bool,
             mouse_pos: tuple):
        s = self.screen

        # ── left panel ───────────────────────────────────────────────────────
        self._draw_left_bg(state.grid, state.time_of_day)

        # Painter's algorithm: back rows first (r ascending), then c ascending
        grid = state.grid
        _locked = set(grid.locked_positions())
        _all    = {(r, c): ('locked', None) for r, c in _locked}
        for (r, c), tile in grid.tiles.items():
            _all[(r, c)] = ('tile', tile)
        for (r, c) in sorted(_all, key=lambda rc: (rc[0], rc[1])):
            sx, sy = grid.tile_px(r, c)
            kind, tile = _all[(r, c)]
            if kind == 'locked':
                self._draw_locked(sx, sy)
            else:
                self.draw_tile(sx, sy, tile, r, c)

        # Robot drawn last (flat grid — always on top of tiles)
        _t_raw = min(1.0, state.anim_elapsed / state.anim_duration) if (state.animating and state.anim_duration > 0) else 0.0
        self.draw_robot(state.robot, state.anim_type if state.animating else 'none', _t_raw,
                        cosmetics=state.cosmetics, tod=state.time_of_day)
        # Decorations
        vrec = state.grid.visual_rect()
        if 'scarecrow' in state.decorations:
            self._draw_scarecrow(vrec)
        if 'well' in state.decorations:
            self._draw_well(vrec)

        # Night overlay (after tiles + robot, before UI labels)
        _nalpha = _night_alpha(state.time_of_day)
        if _nalpha > 0:
            self._night_ov.fill((30, 20, 60, _nalpha))
            s.blit(self._night_ov, (0, 0))

        # Time-of-day indicator (sun/moon arc + day counter)
        self._draw_time_indicator(s, state.time_of_day, state.day_number)

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
# Sound system  (numpy procedural audio; silent fallback if numpy missing)
# ─────────────────────────────────────────────────────────────────────────────
class SoundManager:
    _SR = 44100

    def __init__(self):
        self._sounds: dict = {}
        try:
            import numpy as _np
            self._build(_np)
        except Exception:
            pass   # no numpy or mixer not ready → stay silent

    @staticmethod
    def _to_sound(arr, np) -> pygame.mixer.Sound:
        arr = np.clip(arr, -1.0, 1.0)
        buf = (arr * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack([buf, buf]))

    def _build(self, np):
        SR = self._SR

        def t(dur):
            return np.linspace(0, dur, int(dur * SR), endpoint=False)

        def dec(time, tau):
            return np.exp(-time / tau)

        def mk(arr, vol=0.22):
            s = self._to_sound(arr, np)
            s.set_volume(vol)
            return s

        # move — soft muted footstep: gentle 100 Hz thud, 0.12 s
        _t = t(0.12)
        sig = np.sin(2*np.pi*100*_t) * dec(_t, 0.035)
        sig += np.random.RandomState(1).randn(len(_t)) * 0.06 * dec(_t, 0.018)
        self._sounds['move'] = mk(sig, vol=0.18)

        # turn — soft cloth swish: low-amplitude noise burst, 0.07 s
        _t = t(0.07)
        freq = np.linspace(260, 110, len(_t))
        phase = np.cumsum(2*np.pi * freq / SR)
        sig = np.sin(phase) * dec(_t, 0.035) * 0.25
        sig += np.random.RandomState(2).randn(len(_t)) * 0.08 * dec(_t, 0.025)
        self._sounds['turn'] = mk(sig, vol=0.14)

        # plant — gentle earth pat: soft warm thud, 0.14 s
        _t = t(0.14)
        sig  = np.sin(2*np.pi*140*_t) * dec(_t, 0.045) * 0.60
        sig += np.sin(2*np.pi*70*_t)  * dec(_t, 0.060) * 0.35
        sig += np.random.RandomState(3).randn(len(_t)) * 0.08 * dec(_t, 0.020)
        self._sounds['plant'] = mk(sig, vol=0.20)

        # harvest — soft warm bell: pure 660 Hz, long gentle fade, 0.45 s
        _t = t(0.45)
        sig = (np.sin(2*np.pi*660*_t) * 0.70 +
               np.sin(2*np.pi*660*2.0*_t) * 0.15 +
               np.sin(2*np.pi*660*3.0*_t) * 0.06) * dec(_t, 0.18)
        self._sounds['harvest'] = mk(sig, vol=0.24)

        # wait — barely-there soft tick, 0.05 s
        _t = t(0.05)
        sig = np.sin(2*np.pi*200*_t) * dec(_t, 0.010) * 0.40
        self._sounds['wait'] = mk(sig, vol=0.08)

        # bump — very soft low thud (quieter than move), 0.09 s
        _t = t(0.09)
        sig  = np.sin(2*np.pi*70*_t) * dec(_t, 0.028) * 0.55
        sig += np.random.RandomState(5).randn(len(_t)) * 0.07 * dec(_t, 0.018)
        self._sounds['bump'] = mk(sig, vol=0.15)

        # shop_open — gentle soft pop/click, 0.18 s
        _t = t(0.18)
        freq = np.linspace(300, 120, len(_t))
        phase = np.cumsum(2*np.pi * freq / SR)
        sig = np.sin(phase) * dec(_t, 0.08) * 0.45
        sig += np.random.RandomState(6).randn(len(_t)) * 0.05 * dec(_t, 0.04)
        self._sounds['shop_open'] = mk(sig, vol=0.18)

        # purchase — soft gentle chime: 880 Hz, clean, 0.30 s
        _t = t(0.30)
        sig = (np.sin(2*np.pi*880*_t) * 0.65 +
               np.sin(2*np.pi*1320*_t) * 0.20 +
               np.sin(2*np.pi*660*_t)  * 0.12) * dec(_t, 0.12)
        self._sounds['purchase'] = mk(sig, vol=0.22)

        # fail — very soft low bump, 0.08 s
        _t = t(0.08)
        sig  = np.sin(2*np.pi*60*_t) * dec(_t, 0.030) * 0.50
        sig += np.sin(2*np.pi*90*_t) * dec(_t, 0.022) * 0.25
        self._sounds['fail'] = mk(sig, vol=0.14)

    def play(self, name: str):
        snd = self._sounds.get(name)
        if snd:
            snd.play()

    def play_for_dispatch(self, action: tuple, anim_type: str):
        verb = action[0]
        if verb == 'move':
            self.play('bump' if anim_type == 'bump' else 'move')
        elif verb in ('turn_left', 'turn_right', 'face'):
            self.play('turn')
        elif verb == 'plant':
            self.play('plant')
        elif verb == 'harvest':
            self.play('harvest')
        elif verb == 'wait':
            self.play('wait')


# ─────────────────────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────────────────────
def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Farm Bot")
    clock = pygame.time.Clock()

    state     = GameState()
    renderer  = Renderer(screen)
    sound_mgr = SoundManager()

    RIGHT_X      = PANEL_W + 20
    editor_rect  = pygame.Rect(RIGHT_X, 40, PANEL_W - 40, 296)
    btn_rect     = pygame.Rect(RIGHT_X, 350, 130, 34)
    console_rect = pygame.Rect(RIGHT_X, 420, PANEL_W - 40, WIN_H - 438)

    editor  = EditorComponent(editor_rect, renderer.font_mono)
    console = ConsoleComponent(console_rect, renderer.font_mono)


    game_running = True
    while game_running:
        dt        = clock.tick(60) / 1000.0
        mouse_pos = pygame.mouse.get_pos()

        # ── day / night progression ──────────────────────────────────────────
        _prev_days = int(state.total_time / DAY_DURATION)
        state.total_time += dt
        if int(state.total_time / DAY_DURATION) > _prev_days:
            state.day_number += 1
        state.time_of_day = (state.total_time % DAY_DURATION) / DAY_DURATION
        btn_hover = btn_rect.collidepoint(mouse_pos) and not state.running and not state.shop_open

        # ── events ──────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_s,) and not editor.focused:
                    if not state.shop_open:
                        sound_mgr.play('shop_open')
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
                            prev_n = len(state.console_msgs)
                            handle_buy(key, state)
                            if len(state.console_msgs) > prev_n:
                                col = state.console_msgs[-1][1]
                                sound_mgr.play('purchase' if col == C_CON_GRN else 'fail')
                else:
                    if btn_hover:
                        run_player_code(editor.text, state)
                    elif editor_rect.collidepoint(event.pos):
                        editor.focused = True
                    else:
                        editor.focused = False

            elif event.type == pygame.MOUSEWHEEL:
                if state.shop_open and state.shop_tab == 2:
                    state.shop_cmd_scroll = max(
                        0, min(_SHOP_CMD_MAX_SCROLL,
                               state.shop_cmd_scroll - event.y * 20))
                elif state.shop_open and state.shop_tab == 3:
                    max_ch_scroll = max(0, len(state.active_challenges) * 98 - 240)
                    state.shop_ch_scroll = max(
                        0, min(max_ch_scroll,
                               state.shop_ch_scroll - event.y * 20))

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
                action = state.action_queue.popleft()
                state.dispatch(action)
                sound_mgr.play_for_dispatch(action, state.anim_type)
                state.update_challenges()
            else:
                state.running = False
                state.log("Done.", C_CON_GRY)
                state.update_challenges()

        # ── challenge flash timer tick ────────────────────────────────────────
        for i, ch in enumerate(state.active_challenges):
            if ch.flash_timer > 0:
                ch.flash_timer = max(0.0, ch.flash_timer - dt)
                if ch.flash_timer <= 0:
                    state._replace_challenge(i)

        # ── draw ─────────────────────────────────────────────────────────────
        renderer.draw(state, editor, console, btn_rect, btn_hover, mouse_pos)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
