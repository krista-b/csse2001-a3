"""
Simple 2d world where the player can interact with the items in the world.
"""

__author__ = "Krista Bradshaw 45285143"
__date__ = "18/10/19"
__version__ = "1.1.0"
__copyright__ = "The University of Queensland, 2019"

import math
import os
import time
import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog

from typing import Tuple, List

import pymunk

from game.block import Block, MysteryBlock
from game.entity import Entity, BoundaryWall
from game.util import get_collision_direction
from game.mob import Mob, CloudMob, Fireball
from game.item import DroppedItem, Coin
from game.view import GameView, ViewRenderer
from game.world import World

from level import load_world, WorldBuilder
from player import Player

BLOCK_SIZE = 2 ** 4
MAX_WINDOW_SIZE = (1080, math.inf)

GOAL_SIZES = {
    "flag": (0.2, 9),
    "tunnel": (2, 2)
}

BLOCKS = {
    '#': 'brick',
    '%': 'brick_base',
    '?': 'mystery_empty',
    '$': 'mystery_coin',
    '^': 'cube',
    'b': 'bounce_block',
    '=': 'tunnel',
    'I': 'flag',
    'S': 'switch_up'
}

ITEMS = {
    'C': 'coin',
    '*': 'star'
}

MOBS = {
    '&': "cloud",
    '@': "mushroom"
}


def create_block(world: World, block_id: str, x: int, y: int, *args):
    """Create a new block instance and add it to the world based on the block_id.

    Parameters:
        world (World): The world where the block should be added to.
        block_id (str): The block identifier of the block to create.
        x (int): The x coordinate of the block.
        y (int): The y coordinate of the block.
    """
    block_id = BLOCKS[block_id]

    if block_id == "mystery_empty":
        block = MysteryBlock()
    elif block_id == "mystery_coin":
        block = MysteryBlock(drop="coin", drop_range=(3, 6))
    elif block_id == "bounce_block":
        block = BounceBlock()
    elif block_id == "tunnel":
        block = Goal(block_id, GOAL_SIZES["tunnel"])
    elif block_id == "flag":
        block = Goal(block_id, GOAL_SIZES["flag"])
    elif block_id == "switch_up" or block_id == "switch_down":
        block = Switch()
    elif block_id == "empty_block":
        block = Empty()
    else:
        block = Block(block_id)

    world.add_block(block, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_item(world: World, item_id: str, x: int, y: int, *args):
    """Create a new item instance and add it to the world based on the item_id.

    Parameters:
        world (World): The world where the item should be added to.
        item_id (str): The item identifier of the item to create.
        x (int): The x coordinate of the item.
        y (int): The y coordinate of the item.
    """
    item_id = ITEMS[item_id]
    if item_id == "coin":
        item = Coin()
    elif item_id == "star":
        item = Star()
    else:
        item = DroppedItem(item_id)

    world.add_item(item, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_mob(world: World, mob_id: str, x: int, y: int, *args):
    """Create a new mob instance and add it to the world based on the mob_id.

    Parameters:
        world (World): The world where the mob should be added to.
        mob_id (str): The mob identifier of the mob to create.
        x (int): The x coordinate of the mob.
        y (int): The y coordinate of the mob.
    """
    mob_id = MOBS[mob_id]
    if mob_id == "cloud":
        mob = CloudMob()
    elif mob_id == "fireball":
        mob = Fireball()
    elif mob_id == "mushroom":
        mob = MushroomMob()
    else:
        mob = Mob(mob_id, size=(1, 1))

    world.add_mob(mob, x * BLOCK_SIZE, y * BLOCK_SIZE)


def create_unknown(world: World, entity_id: str, x: int, y: int, *args):
    """Create an unknown entity."""
    world.add_thing(Entity(), x * BLOCK_SIZE, y * BLOCK_SIZE,
                    size=(BLOCK_SIZE, BLOCK_SIZE))


BLOCK_IMAGES = {
    "brick": "brick",
    "brick_base": "brick_base",
    "cube": "cube",
    "bounce_block": "bounce_block",
    "tunnel": "tunnel",
    "flag": "flag",
    "empty_block": "empty_block"
}

ITEM_IMAGES = {
    "coin": "coin_item",
    "star": "star"
}

MOB_IMAGES = {
    "cloud": "floaty",
    "fireball": "fireball_down",
    "mushroom": "mushroom"
}


class StatusDisplay(tk.Frame):
    """The status display frame displays the players current health in an animated
                                                        bar and score below that."""

    def __init__(self, root):
        """Constructs the frame and labels to display the health and score"""
        super().__init__(root)
        self._master = root

        self._frame = tk.Frame(root, bg='black')
        self._frame.pack(fill=tk.X)

        self._healthbar = tk.Label(self._frame, bg='medium spring green', width=120)
        self._healthbar.pack(side=tk.TOP, anchor=tk.W)

        self._scorebar = tk.Label(self._frame, text="Score: 0")
        self._scorebar.pack(fill=tk.X)

    def set_scorebar(self, score):
        """Sets the visible score based on the players current score."""
        self._scorebar.config(text=f"Score: {score}")

    def set_healthbar(self, health: float):
        """Sets the visible health based on the players current health.

        The health bar displays various colours based on the percentage
                                            it is of the maximum health."""
        self._full_bar = 120
        self._width = health
        self._healthbar.config(width=self._width)

        if self._width >= self._full_bar * 0.5:
            self._healthbar.config(bg='medium spring green')
        elif self._full_bar * 0.5 > self._width > self._full_bar * 0.25:
            self._healthbar.config(bg='orange')
        elif self._width <= self._full_bar * 0.25:
            self._healthbar.config(bg='red')

    def invincible(self, time_left: float):
        """Changes the health bar to yellow while the player is in an invincible state."""
        self._healthbar.config(text=f'Invincibility lasts: {time_left} seconds', bg='yellow')

    def revert(self):
        """Reverts the health bar back to its original colour after the player
                                                    is no longer invincible."""
        self._healthbar.config(text=' ')


class BounceBlock(Block):
    """A bounce block causes the player to bounce when the player hits its topside."""
    _id = "bounce_block"

    def on_hit(self, event, data):
        """Callback collision with player event handler."""
        world, self._player = data

        if get_collision_direction(self._player, self) == "A":
            velocity = self._player.get_velocity()
            xV = velocity[0]
            yV = velocity[1] - 280
            self._player.set_velocity((xV, yV))


class MushroomMob(Mob):
    """The mushroom mob is a moving entity that reverses its direction on
                                                collision with another entity.

    When colliding with the player it will damage the player, repel the
                                    player away and then reverse its direction.

    When the player jumps on this mob the player will bounce and the
                                                    mob will be destroyed.
    """
    _id = "mushroom"

    def __init__(self):
        super().__init__(self._id, size=(BLOCK_SIZE, BLOCK_SIZE), weight=50, tempo=-20)

    def on_hit(self, event: pymunk.Arbiter, data):
        """Callback collision with player event handler."""
        world, self._player = data

        if self.get_id() == "mushroom":
            if get_collision_direction(self._player, self) == "A":
                self._player.set_velocity((0, -280))
                world.remove_mob(self)
            elif get_collision_direction(self._player, self) == "L":
                self._player.set_velocity((-60, 0))
                self._player.change_health(-1)
                self.reverse()
            elif get_collision_direction(self._player, self) == "R":
                self._player.set_velocity((60, 0))
                self._player.change_health(-1)
                self.reverse()
                self._player.change_health(-1)
            else:
                self._player.change_health(-1)

    def reverse(self):
        """Reverses the mobs direction."""
        vx = -self.get_tempo()
        self.set_tempo(vx)


class Star(DroppedItem):
    """A dropped star item that can be picked up to make the player
                                        invincible/receive no damages for 10s.
    """
    _id = "star"

    def collect(self, player: Player):
        """Collect the star and change the players invincibility status.

        Parameters:
            player (Player): The player which collided with the dropped item.
        """
        player.change_invincibility(True)


class Goal(Block):
    """A goal block transports the player to the associated next level.

    A goal could be either a tunnel block or a flag block."""

    def __init__(self, block_id, size):
        """Construct a new goal block.

        Parameters:
            block_id (str): The unique id of this block.
            size (tuple<int, int>): The cell size of this block,
                                          first element is the x value,
                                          second element is the y value.
        """
        super().__init__(block_id=block_id)
        self._cell_size = size


class Switch(Block):
    """A switch block removes all bricks within range of the switch
                            for 10s whenthe player collides with it from above.

    The active state of a switch block is whether it has been switched on or not.
    """
    _id = "switch"

    def __init__(self):
        super().__init__()
        self._active = False

    def on_hit(self, event, data):
        """Callback collision with player event handler."""
        world, player = data

        if get_collision_direction(player, self) == "A":
            self._active = True
            player.set_on_switch(True)

            self._switch_time = time.time()

    def step(self, time_delta: float, game_data):
        """Determine whether the switch has been active for 10s yet or not."""
        world, player = game_data
        self._current_time = time.time()

        switch_position = self.get_position()
        s_x = switch_position[0]
        s_y = switch_position[1]
        things_in_range = World.get_things_in_range(world, s_x, s_y, 3 * BLOCK_SIZE)

        if player.on_switch():
            if (self._current_time - self._switch_time) < 10:
                for thing in things_in_range:
                    if thing.get_type() == 4 and thing.get_id() == "brick":
                        brick_position = thing.get_position()
                        World.remove_thing(world, thing)
                        World.add_block(world, Empty(), brick_position[0], brick_position[1])
                # Removes the bricks in range and replaces them with empty blocks

            else:
                for thing in things_in_range:
                    if thing.get_type() == 4 and thing.get_id() == "empty_block":
                        brick_position = thing.get_position()
                        World.add_block(world, Block("brick"), brick_position[0], brick_position[1])
                        World.remove_thing(world, thing)
                self._active = False
                player.set_on_switch(False)

    def is_active(self) -> bool:
        """(bool): Returns true if the block has been switched on."""
        return self._active


class Empty(Block):
    """An empty block is an invisible brick which the player cannot collide with."""
    _id = "empty_block"


class MarioViewRenderer(ViewRenderer):
    """A customised view renderer for a game of mario."""

    @ViewRenderer.draw.register(Player)
    def _draw_player(self, instance: Player, shape: pymunk.Shape,
                     view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:

        if instance.get_name() == 'mario':
            if shape.body.velocity.x >= 0:
                image = self.load_image("mario_right")
            else:
                image = self.load_image("mario_left")

        if instance.get_name() == 'luigi':
            if shape.body.velocity.x >= 0:
                image = self.load_image("luigi_right")
            else:
                image = self.load_image("luigi_left")

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="player")]

    @ViewRenderer.draw.register(MysteryBlock)
    def _draw_mystery_block(self, instance: MysteryBlock, shape: pymunk.Shape,
                            view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        if instance.is_active():
            image = self.load_image("coin")
        else:
            image = self.load_image("coin_used")

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="block")]

    @ViewRenderer.draw.register(Switch)
    def _draw_switch_block(self, instance: Switch, shape: pymunk.Shape,
                           view: tk.Canvas, offset: Tuple[int, int]) -> List[int]:
        if instance.is_active():
            image = self.load_image("switch_pressed")
        else:
            image = self.load_image("switch")

        return [view.create_image(shape.bb.center().x + offset[0], shape.bb.center().y,
                                  image=image, tags="block")]


class MarioApp:
    """High-level app class for Mario, a 2d platformer"""

    _world: World

    def __init__(self, master: tk.Tk, settings):
        """Construct a new game of a MarioApp game.

        Parameters:
            master (tk.Tk): tkinter root widget
        """
        self._master = master
        self._settings = settings
        if (
                "World" not in self._settings or "Player" not in self._settings or
                "start" not in get_contents(self._settings, "World") or
                get_value(self._settings, "World", "start") not in self._settings
            ):
            # Checks the configuration file for the minimum requirements
            messagebox.showerror("Error!", "Invalid Config File!", parent=self._master)
            self._master.quit()
            self._master.destroy()

        else:
            if "gravity" not in get_contents(self._settings, "World"):
                self._gravity_y = 300
            else:
                self._gravity_y = int(get_value(self._settings, 'World', 'gravity'))

            world_builder = WorldBuilder(BLOCK_SIZE, gravity=(0, self._gravity_y),
                                         fallback=create_unknown)
            world_builder.register_builders(BLOCKS.keys(), create_block)
            world_builder.register_builders(ITEMS.keys(), create_item)
            world_builder.register_builders(MOBS.keys(), create_mob)
            self._builder = world_builder

            if "character" not in get_contents(self._settings, "Player"):
                name = "mario"
            else:
                name = get_value(self._settings, 'Player', 'character')
            if "health" not in get_contents(self._settings, "Player"):
                max_health = 5
            else:
                max_health = int(get_value(self._settings, 'Player', 'health'))
            self._player = Player(name=name, max_health=max_health)
            self._on_tunnel = False
            self._end = False

            self._renderer = MarioViewRenderer(BLOCK_IMAGES, ITEM_IMAGES, MOB_IMAGES)

            self._current_level = get_value(self._settings, 'World', 'start')
            self.reset_world(self._current_level)

            size = tuple(map(min, zip(MAX_WINDOW_SIZE, self._world.get_pixel_size())))
            self._view = GameView(master, size, self._renderer)
            self._view.pack()

            self.bind()

            menubar = tk.Menu(master)
            filemenu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="File", menu=filemenu)
            filemenu.add_command(label="Load Level", command=self.load_popup)
            filemenu.add_command(label="Reset Level", command=self.reset_popup)
            filemenu.add_command(label="Exit", command=self.exit)

            scoresmenu = tk.Menu(menubar, tearoff=1)
            scoresmenu.add_command(label="High Scores",
                                   command=lambda: high_scores(self._current_level))
            menubar.add_cascade(label="High Scores", menu=scoresmenu)

            master.config(menu=menubar)

            self._StatusDisplay = StatusDisplay(self._master)
            self._StatusDisplay.pack()

            # Wait for window to update before continuing
            master.update_idletasks()
            self.step()

    def exit(self):
        """Called when the user wants to exit the game from the menu."""
        if messagebox.askokcancel("Exit", "Do you want to exit?"):
            self._master.destroy()
        else:
            pass

    def reset_popup(self):
        """Called when the user wants to reset the game from the menu."""
        if messagebox.askyesno("Reset Game", "Do you want to reset the game?"):
            self._player.set_health(self._player.get_max_health())
            self._player.change_score(-self._player.get_score())
            self.reset_world(self._current_level)
        else:
            pass

    def load_popup(self):
        """Called when the user wants to load a new level from the menu."""
        self.input = simpledialog.askstring("Load Level",
                                            "Please enter level:", parent=self._master)
        if self.input is not None:
            self._player.set_health(self._player.get_max_health())
            self._player.change_score(-self._player.get_score())
            self.reset_world(self.input)

    def reset_world(self, new_level):
        """Resets the world to the new_level string name."""
        self._world = load_world(self._builder, new_level)
        self._current_level = new_level
        if 'x' not in get_contents(self._settings, "Player"):
            x = BLOCK_SIZE
        else:
            x = int(get_value(self._settings, 'Player', 'x'))
        if 'y' not in get_contents(self._settings, "Player"):
            y = BLOCK_SIZE
        else:
            y = int(get_value(self._settings, 'Player', 'y'))
        if 'mass' not in get_contents(self._settings, "Player"):
            mass = 80
        else:
            mass = int(get_value(self._settings, 'Player', 'mass'))
        self._world.add_player(self._player, x, y, mass)
        self._master.focus_force()
        self._builder.clear()
        self._setup_collision_handlers()

    def bind(self):
        """Bind all the keyboard events to their event handlers."""
        self._master.bind('<w>', lambda event: self._jump())
        self._master.bind('<Up>', lambda event: self._jump())
        self._master.bind('<space>', lambda event: self._jump())

        self._master.bind('<a>', lambda event: self._move(-1, 0))
        self._master.bind('<Left>', lambda event: self._move(-1, 0))

        self._master.bind('<s>', lambda event: self._duck())
        self._master.bind('<Down>', lambda event: self._duck())

        self._master.bind('<d>', lambda event: self._move(1, 0))
        self._master.bind('<Right>', lambda event: self._move(1, 0))

    def redraw(self):
        """Redraw all the entities in the game canvas."""
        self._view.delete(tk.ALL)

        self._view.draw_entities(self._world.get_all_things())

    def scroll(self):
        """Scroll the view along with the player in the center unless
        they are near the left or right boundaries
        """
        x_position = self._player.get_position()[0]
        half_screen = self._master.winfo_width() / 2
        world_size = self._world.get_pixel_size()[0] - half_screen

        # Left side
        if x_position <= half_screen:
            self._view.set_offset((0, 0))

        # Between left and right sides
        elif half_screen <= x_position <= world_size:
            self._view.set_offset((half_screen - x_position, 0))

        # Right side
        elif x_position >= world_size:
            self._view.set_offset((half_screen - world_size, 0))

    def step(self):
        """Step the world physics and redraw the canvas."""
        data = (self._world, self._player)
        self._world.step(data)

        if self._end == True:
            messagebox.showinfo("Winner!", "You Have Completed All the Levels!")
            quit()
            destroy()

        else:
            self.scroll()
            self.redraw()

            self._current_time = time.time()

            StatusDisplay.set_scorebar(self._StatusDisplay, self._player.get_score())
            # width of health bar = player's health * (length of full bar / player's max_health
            StatusDisplay.set_healthbar(self._StatusDisplay, int(self._player.get_health()
                                                        * (120 / self._player.get_max_health())))

            if self._player.is_dead():
                self._player.change_health(self._player.get_max_health())
                self.no_health()

            if self._player.is_invincible():
                if (self._current_time - self._player.get_time()) > 10:
                    self._player.change_invincibility(False)
                    StatusDisplay.revert(self._StatusDisplay)
                else:
                    self._time_left = 10 - int(self._current_time - self._player.get_time())
                    StatusDisplay.invincible(self._StatusDisplay, self._time_left)

            self._master.after(10, self.step)

    def no_health(self):
        """Creates a popup when the player has no health and ask the user if
                                        they want to reset or exit the game.
        """
        self.popup = tk.Tk()
        self.popup.wm_title("Reset or Exit")
        label = tk.Label(self.popup, text="Would you like to reset or exit the level?")
        label.pack(side="top", fill="x", pady=10)
        B1 = tk.Button(self.popup, text="Reset", command=lambda: [self.reset_popup(),
                                                                  self.popup.destroy()])
        B1.pack()
        B2 = tk.Button(self.popup, text="Exit", command=lambda: [self.exit(),
                                                                 self.popup.destroy()])
        B2.pack()

    def _move(self, dx, dy):
        velocity = self._player.get_velocity()
        if 'max_velocity' not in get_contents(self._settings, "Player"):
            self._max_velocity =  200
        else:
            self._max_velocity = int(get_value(self._settings, 'Player', 'max_velocity'))

        xV = velocity.x + dx * 60
        yV = velocity.y + dy * 60

        if xV > self._max_velocity:
            xV = self._max_velocity
        elif yV > self._max_velocity:
            yV = self._max_velocity

        self._player.set_velocity((xV, yV))

    def _jump(self):
        if not self._player.is_jumping():
            self._player.set_jumping(True)
            velocity = self._player.get_velocity()
            xV = velocity[0]
            yV = velocity[1] - 150
            self._player.set_velocity((xV, yV))

    def _duck(self):
        velocity = self._player.get_velocity()
        xV = velocity[0]
        yV = velocity[1] + 120
        self._player.set_velocity((xV, yV))

        if self._on_tunnel:
            self.tunnel_level = get_value(self._settings, self._current_level, 'tunnel')
            self.reset_world(self.tunnel_level)
            self._on_tunnel = False

    def _setup_collision_handlers(self):
        self._world.add_collision_handler("player", "item", on_begin=self._handle_player_collide_item)
        self._world.add_collision_handler("player", "block", on_begin=self._handle_player_collide_block,
                                          on_separate=self._handle_player_separate_block)
        self._world.add_collision_handler("player", "mob", on_begin=self._handle_player_collide_mob)
        self._world.add_collision_handler("mob", "block", on_begin=self._handle_mob_collide_block)
        self._world.add_collision_handler("mob", "mob", on_begin=self._handle_mob_collide_mob)
        self._world.add_collision_handler("mob", "item", on_begin=self._handle_mob_collide_item)

    def _handle_mob_collide_block(self, mob: Mob, block: Block, data,
                                  arbiter: pymunk.Arbiter) -> bool:

        if mob.get_id() == "fireball":
            if block.get_id() == "brick":
                self._world.remove_block(block)
            self._world.remove_mob(mob)

        elif mob.get_id() == "mushroom":
            if get_collision_direction(block, mob) == "L" or \
                    get_collision_direction(block, mob) == "R":
                mob.reverse()

        if block.get_id() == "empty_block":
            return False
        else:
            return True

    def _handle_mob_collide_item(self, mob: Mob, block: Block, data,
                                 arbiter: pymunk.Arbiter) -> bool:

        if mob.get_id() == "mushroom":
            mob.reverse()

        return False

    def _handle_mob_collide_mob(self, mob1: Mob, mob2: Mob, data,
                                arbiter: pymunk.Arbiter) -> bool:

        if mob1.get_id() == "fireball" or mob2.get_id() == "fireball":
            self._world.remove_mob(mob1)
            self._world.remove_mob(mob2)

        elif mob1.get_id() == "mushroom" or mob2.get_id() == "mushroom":
            mob1.reverse()
            mob2.reverse()

        return False

    def _handle_player_collide_item(self, player: Player, dropped_item: DroppedItem,
                                    data, arbiter: pymunk.Arbiter) -> bool:
        """Callback to handle collision between the player and a (dropped) item. If the player has sufficient space in
        their to pick up the item, the item will be removed from the game world.

        Parameters:
            player (Player): The player that was involved in the collision
            dropped_item (DroppedItem): The (dropped) item that the player collided with
            data (dict): data that was added with this collision handler (see data parameter in
                         World.add_collision_handler)
            arbiter (pymunk.Arbiter): Data about a collision
                                      (see http://www.pymunk.org/en/latest/pymunk.html#pymunk.Arbiter)
                                      NOTE: you probably won't need this
        Return:
             bool: False (always ignore this type of collision)
                   (more generally, collision callbacks return True iff the collision should be considered valid; i.e.
                   returning False makes the world ignore the collision)
        """

        dropped_item.collect(self._player)
        self._world.remove_item(dropped_item)

        return False

    def _handle_block_collide_item(self, block: Block, dropped_item: DroppedItem,
                                   data, arbiter: pymunk.Arbiter) -> bool:

        World.add_collision_handler(world, 2, 4, data, True, True, True, True)
        if block.get_id() == "empty_block":
            return False
        else:
            return True

    def _handle_player_collide_block(self, player: Player, block: Block, data,
                                     arbiter: pymunk.Arbiter) -> bool:

        if get_collision_direction(player, block) == "A":
            player.set_jumping(False)

        if block.get_id() == "flag":
            if get_collision_direction(player, block) == "A":
                player.set_health(player.get_max_health())
            self.flag_level = get_value(self._settings, self._current_level, 'goal')
            name = simpledialog.askstring("Congrats! You finished the level!", "Please enter your name:")
            if name is not None:
                write_high_scores(self._current_level, name, player.get_score())
                if self.flag_level == 'END':
                    self._end = True
                else:
                    self.reset_world(self.flag_level)

        if block.get_id() == "switch" and player.on_switch():
            return False

        if block.get_id() == "tunnel":
            if get_collision_direction(player, block) == "A":
                self._on_tunnel = True

        if block.get_id() == "empty_block":
            return False
        else:
            block.on_hit(arbiter, (self._world, player))
            return True

    def _handle_player_collide_mob(self, player: Player, mob: Mob, data,
                                   arbiter: pymunk.Arbiter) -> bool:

        if not player.is_invincible():
            mob.on_hit(arbiter, (self._world, player))
        else:
            self._world.remove_mob(mob)

        return True

    def _handle_player_separate_block(self, player: Player, block: Block, data,
                                      arbiter: pymunk.Arbiter) -> bool:

        if block.get_id() == "tunnel":
            self._on_tunnel = False

        return True


def read_config(filename):
    """Reads the filename input by the user and returns the contents as a
                                        dictionary of tags, keys and values.
    Parameters:
            filename (str): The name of the text file to be read.

    Returns:
          CONTENTS (dict): Contents of the text file as a dictionary.
    """
    CONTENTS = {}
    tag = None
    if not os.path.isfile(filename):
        messagebox.showerror("Error", "File Does Not Exist!")
        quit()
        destroy()
    else:
        with open(filename, 'r') as file:
            for line in file:
                line = line.strip()
                if line.startswith('==') and line.endswith('=='):
                    tag = line[2:-2]
                    CONTENTS[tag] = {}
                elif ' : ' in line and tag is not None:
                    key, _, value = line.partition(' : ')
                    CONTENTS[tag][key] = value
                elif not line.strip():
                    pass
                else:
                    messagebox.showerror("Error", "Invalid Config File!")
                    quit()
                    destroy()
            return CONTENTS


def get_value(config, tag, key):
    """Returns the value associated with the tag and key within the
                                                configuration dictionary.
    Parameters:
            config (str): The name of the dictionary.
            tag (str): The tag within the dictionary.
            key (str): The key to the tag.

    Returns:
          value (dict): The value to the key.
    """
    return config[tag][key]


def get_contents(config, tag):
    """Returns all the keys and values to the tag string within the configuration
                                                                        dictionary.
    Parameters:
            config (str): The name of the dictionary to be read.
            tag(str): The tag within the dictionary.

    Returns:
          contents (list): A list of all the keys and values within the tag.
    """
    contents = []
    for key in config[tag]:
        contents.append(key)
        contents.append(config[tag][key])
    return contents


def write_high_scores(level_name, name, score):
    """Writes the users name and score to the appropriate text file,
                                            creating if it doesnt exist.

    Parameters:
            level_name (str): The name of the level the scores belong to.
            name (str): The users inputted name.
            score(int): The players current score.
    """
    filename = f'high_scores_{level_name}'
    file = open(filename, 'a+')
    file.write(f'{name} : {score}\n')
    file.close()


def high_scores(level: str = None):
    """Reads the text file and opens a toplevel tkinter to display the top 10 scores.

    Parameters:
            level (str): The name of the text file to be read.
    """
    top = tk.Toplevel(bg='red')
    top.title("High Scores")
    top.minsize(200, 350)
    title = tk.Label(top, text=f"Top 10 Scores For: {level}", bg='yellow', fg = 'red')
    title.pack(side=tk.TOP, fill=tk.X)
    level = f'high_scores_{level}'
    score = tk.Label(top, bg = 'red')
    score.pack(side=tk.TOP, fill=tk.X)

    if not os.path.isfile(level):
        score.config(text="No scores exists yet, go play and make some!")
    else:
        sort = lambda line: int(line.split(None)[2])

        with open(level, 'r') as f:
            # Sorts the scores in descending order and then displays the highest 10.
            sorted_x = sorted(f, key=sort, reverse=True)
        score.config(text="\n".join(sorted_x[:10]))


def main():
    """Asks the user for a configuration file and then loads the appropriate
                                                level within the MarioApp class.
    """
    root = tk.Tk()
    input_level = simpledialog.askstring("Welcome!", "Please Enter Configuration File:", parent=root)
    root.title("Mario!")
    if input_level is not None:
        MarioApp(root, read_config(input_level))
    root.mainloop()


if __name__ == "__main__":
    main()
