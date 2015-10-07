#!/usr/bin/env python

import libtcodpy as libtcod
import math
import textwrap

# Window size
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

# Limit the FPS
LIMIT_FPS = 20

# GUI size
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

# Map size
MAP_WIDTH = 80
MAP_HEIGHT = 43

# Room properties
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30
MAX_ROOM_MONSTERS = 3
MAX_ROOM_ITEMS = 2

# FOV properties
FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

# Item properties
HEAL_AMOUNT = 4
LIGHTNING_DAMAGE = 20
LIGHTNING_RANGE = 5
CONFUSE_NUM_TURNS = 10
CONFUSE_RANGE = 8
FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 12

# Inventory properties
INVENTORY_WIDHT = 50

color_dark_wall = libtcod.Color(31, 31, 20)
color_light_wall = libtcod.Color(102, 102, 0)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)

class Tile:
    # A tile on the map and its properties
    def __init__(self, blocked, block_sight = None):
        self.blocked = blocked
        self.explored = False

        # By default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight

class Rect:
    # A rectangle on the map, used to characterize a room
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        """ Returns True if this rectangle intersects with another one """
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)

class Object:
    # This is a generic object: the player, a monster, an item, the stairs etc.
    # It is always represented by a character on screen.
    def __init__(self, x, y, char, name, color, blocks=False,
            fighter=None, ai=None, item=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.fighter = fighter
        if self.fighter:
            self.fighter.owner = self # Let the fighter component know who owns it

        self.ai = ai
        if self.ai:
            self.ai.owner = self # Let the AI component know who owns it

        self.item = item
        if self.item:
            self.item.owner = self # Let the item component know who owns it

    def move(self, dx, dy):
        """ Move by the given amount """
        if not is_blocked(self.x +dx, self.y + dy):
            self.x += dx
            self.y += dy

    def draw(self):
        """ Set the color and then draw the character that represents this object
        at its position """
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            libtcod.console_set_default_foreground(con, self.color)
            libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self):
        """ Erase the character that represents this object """
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

    def move_towards(self, target_x, target_y):
        # Vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        # Normalize it to length 1 (preserving direction), then round it and
        # convert to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(dx, dy)

    def distance_to(self, other):
        # Returns the distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def send_to_back(self):
        """ Draw this object first so all other are drawn above this """
        global objects
        objects.remove(self)
        objects.insert(0, self)

    def distance(self, x, y):
        """ Return the distance to some coordinate """
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

class Fighter:
    # Combat-related properties and methods
    def __init__(self, hp, defense, power, death_function=None):
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
        self.death_function = death_function

    def heal(self, amount):
        # Heal by the given amount
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def take_damage(self, damage):
        if damage > 0:
            self.hp -= damage
            # Check for death.
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)

    def attack(self, target):
        damage = self.power - target.fighter.defense

        if damage > 0:
            print self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.'
            target.fighter.take_damage(damage)
        else:
            print self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!'

class BasicMonster:
    # AI for basic monster
    def take_turn(self):
        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
            # Move towards player if far away
            if monster.distance_to(player) >= 2:
                monster.move_towards(player.x, player.y)
            # Attack if close
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)

class Item:
    # An item that can be picked up and used
    def __init__(self, use_function=None):
        self.use_function = use_function

    def use(self):
        if self.use_function is None:
            message('The ' + self.owner.name + ' cannot be used.')
        else:
            if self.use_function() != 'cancelled':
                inventory.remove(self.owner) # Destroy after use

    def pick_up(self):
        """ Add to the player's inventory and remove from the map """
        if len(inventory) >= 26:
            message('Your inventory is full, cannot pick up ' + self.owner.name + '.',
                    libtcod.red)
        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            message('You picked up a ' + self.owner.name + '!', libtcod.green)

class ConfusedMonster:
    # AI for a confused monster
    def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
        self.old_ai = old_ai
        self.num_turns = num_turns

    def take_turn(self):
        if self.num_turns > 0: # Still confused
            # Move in a random direction
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
            # Decrease the number of turns confused
            self.num_turns -= 1
        else:
            # Restore the previous AI
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' is no longer confused', libtcod.red)


def create_room(room):
    global map
    # Go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].blocked = False
            map[x][y].block_sight = False

def create_h_tunnel(x1, x2, y):
    global map
    """ Creates a horizontal tunnel on the map """
    # min() and max() are used in case x1 > x2
    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

def create_v_tunnel(y1, y2, x):
    global map
    """ Creates a vertical tunnel on the map """
    # min() and max() are used in case y1 > y2
    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

def make_map():
    global map

    rooms = []
    num_rooms = 0

    # Fill map with "unblocked" tiles
    map = [[ Tile(True)
        for y in range(MAP_HEIGHT) ]
            for x in range(MAP_WIDTH) ]

    for r in range(MAX_ROOMS):
        # Random width and height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        # Random position within the boundaries of the map
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

        new_room = Rect(x, y, w, h)

        # See if other rooms intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed:
            create_room(new_room)
            place_objects(new_room)

            # Center coordinates of new room
            (new_x, new_y) = new_room.center()

            # Print a "room number" to see how the map drawing works
            #room_no = Object(new_x, new_y, chr(65+num_rooms), 'room number',
                    #libtcod.white)
            #objects.insert(0, room_no)

            if num_rooms == 0:
                # The first room, where the player starts
                player.x = new_x
                player.y = new_y
            else:
                # Connect to the previous room with a tunnel
                (prev_x, prev_y) = rooms[num_rooms-1].center()

                if libtcod.random_get_int(0, 0, 1) == 1:
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)

            rooms.append(new_room)
            num_rooms += 1

def render_all():
    global color_dark_wall, color_light_wall
    global color_dark_ground, color_light_ground
    global fov_recompute

    if fov_recompute:
        # Recompute FOV if needed
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                visible = libtcod.map_is_in_fov(fov_map, x, y)
                wall = map[x][y].block_sight
                if not visible:
                    if map[x][y].explored:
                        if wall:
                            libtcod.console_put_char_ex(con, x, y, '#', color_dark_wall, libtcod.BKGND_SET)
                            #libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
                        else:
                            libtcod.console_put_char_ex(con, x, y, '.', color_dark_ground, libtcod.BKGND_SET)
                            #libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
                else:
                    if wall:
                        libtcod.console_put_char_ex(con, x, y, '#', color_light_wall, libtcod.BKGND_SET)
                    else:
                        libtcod.console_put_char_ex(con, x, y, '.', color_light_ground, libtcod.BKGND_SET)

                    map[x][y].explored = True

    # Draw all objects in the list
    for object in objects:
        if object != player:
            object.draw()
    player.draw()

    # Blit the contents of "con" to the root console
    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)

    # Prepare to render the GUI panel
    libtcod.console_set_default_background(panel, libtcod.black)
    libtcod.console_clear(panel)

    # Print the game messages
    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(panel, color)
        libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
        y += 1

    # Show the player's stats
    render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp,
            libtcod.light_red, libtcod.darker_red)

    # Display names of objects under the mouse
    libtcod.console_set_default_foreground(panel, libtcod.light_gray)
    libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())

    # Blit the contents of "panel" to the root console
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

def handle_keys():
    global fov_recompute, keys

    if key.vk == libtcod.KEY_ENTER and key.lctrl:
        # Fullscreen
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
    elif key.vk == libtcod.KEY_ESCAPE:
        # Exit game
        return 'exit'

    if game_state == 'playing':
        # Movement keys
        if key.vk == libtcod.KEY_UP:
            player_move_or_attack(0, -1)

        elif key.vk == libtcod.KEY_DOWN:
            player_move_or_attack(0, 1)

        elif key.vk == libtcod.KEY_LEFT:
            player_move_or_attack(-1, 0)

        elif key.vk == libtcod.KEY_RIGHT:
            player_move_or_attack(1, 0)

        else:
            # Test for other keys
            key_char = chr(key.c)
            if key_char == ',':
                # Pick up an item
                for object in objects: # Look for an item in the player's tile
                    if object.x == player.x and object.y == player.y and object.item:
                        object.item.pick_up()
                        break
            if key_char == 'i':
                # Show the inventory
                chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
                if chosen_item is not None:
                    chosen_item.use()

            return 'didnt-take-turn'

def place_objects(room):
    num_monsters = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)

    for i in range(num_monsters):
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

        if not is_blocked(x, y):
            choice = libtcod.random_get_int(0, 0, 100)
            if choice < 80:
                fighter_component = Fighter(hp=10, defense=0, power=3, death_function=monster_death)
                ai_component = BasicMonster()

                monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green,
                        blocks=True, fighter=fighter_component, ai=ai_component)
            else:
                fighter_component = Fighter(hp=16, defense=1, power=4, death_function=monster_death)
                ai_component = BasicMonster()

                monster = Object(x, y, 'T', 'troll', libtcod.darker_green,
                        blocks=True, fighter=fighter_component, ai=ai_component)

            objects.append(monster)

    # Choose random number of items
    num_items = libtcod.random_get_int(0, 0, MAX_ROOM_ITEMS)

    for i in range(num_items):
        choice = libtcod.random_get_int(0, 0, 100)
        # Choose a random spot
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

        if not is_blocked(x, y):
            if choice < 70:
                item_component = Item(use_function=cast_heal)
                item = Object(x, y, '!', 'Healing potion', libtcod.violet, item=item_component)
            elif choice < 70 + 15:
                item_component = Item(use_function=cast_lightning)
                item = Object(x, y, '?', 'Scroll of lightning bolt', libtcod.light_yellow,
                        item=item_component)
            elif choice < 70 + 10 + 10:
                item_component = Item(use_function=cast_fireball)
                item = Object(x, y, '?', 'Scroll of fireball', libtcod.light_yellow,
                        item=item_component)
            else:
                item_component = Item(use_function=cast_confuse)
                item = Object(x, y, '?', 'Scroll of confusion', libtcod.light_yellow,
                        item=item_component)
            objects.append(item)
            item.send_to_back()

def is_blocked(x, y):
    if map[x][y].blocked:
        return True

    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True

    return False

def player_move_or_attack(dx, dy):
    global fov_recompute

    x = player.x + dx
    y = player.y + dy

    # Try to find attackable object
    target = None
    for object in objects:
        if object.fighter and object.x == x and object.y == y:
            target = object
            break

    # Attack if target is found
    if target is not None:
        player.fighter.attack(target)
    else:
        player.move(dx, dy)
        fov_recompute = True

def player_death(player):
    # The game ended
    global game_state
    print 'You died!'
    game_state = 'dead'

    # Leave behind a corpse
    player.char = '%'
    player.color = libtcod.dark_red

def monster_death(monster):
    print monster.name.capitalize() + ' is dead!'
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'Remains of ' + monster.name
    monster.send_to_back()

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    """ Calculate the width of the bar and render it """
    bar_width = int(float(value) / maximum * total_width)

    # Render the background
    libtcod.console_set_default_background(panel, back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

    # Render the bar
    libtcod.console_set_default_background(panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

    # Centered text with values
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
            name + ': ' + str(value) + '/' + str(maximum))

def message(new_msg, color = libtcod.white):
    """ Prints a message in the message panel """
    # Split the message if necessary
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

    for line in new_msg_lines:
        # If the buffer is full, remove the first line
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]

        # Add the new line as a tuple
        game_msgs.append( (line, color) )

def get_names_under_mouse():
    """ Return a string with the names of all objects under the mouse """
    global mouse
    (x, y) = (mouse.cx, mouse.cy)

    # Create a list with the names of all objects at the mouse's coordinates
    # and in FOV
    names = [obj.name for obj in objects
            if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]
    # Join the names
    names = ', '.join(names)
    return names.capitalize()

def menu(header, options, width):
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')
    # Calculate total height for the header
    header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    height = len(options) + header_height
    # Create an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)
    # Print the header, with auto-wrap
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE,
            libtcod.LEFT, header)
    # Print all the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT,
                text)
        y += 1
        letter_index += 1
    # Blit the contents of "window" to the root console
    x = SCREEN_WIDTH/2 - width/2
    y = SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)
    # Present the root console to the player and wait for a key-press
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)
    # Convert the ASCII code to an index and return it
    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None

def inventory_menu(header):
    """ Show a menu with each item of the inventory """
    if len(inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = [item.name for item in inventory]

    index = menu(header, options, INVENTORY_WIDHT)
    if index is None or len(inventory) == 0: return None
    return inventory[index].item

def cast_heal():
    """ Heals the player """
    if player.fighter.hp == player.fighter.max_hp:
        message('You are already at full health.', libtcod.red)
        return 'cancelled'

    message('Your wounds start to feel better!', libtcod.light_violet)
    player.fighter.heal(HEAL_AMOUNT)

def cast_lightning():
    """ Find the closest target inside a maximum range and damage it """
    monster = closest_target(LIGHTNING_RANGE)
    if monster is None:
        message('No enemy is close enough to strike.', libtcod.red)
        return 'cancelled'

    message('A lightning bolt strikes the ' + monster.name + ' with a loud thunder! '
            + 'the damage is ' + str(LIGHTNING_DAMAGE) + ' hit points.', libtcod.light_blue)
    monster.fighter.take_damage(LIGHTNING_DAMAGE)

def closest_target(max_range):
    """ Find closest target within range and in FOV """
    closest_target = None
    closest_dist = max_range + 1 # Start with slightly more than maximum range

    for object in objects:
        if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map,
                object.x, object.y):
            # Calculate the distance between target and player
            dist = player.distance_to(object)
            if dist < closest_dist:
                closest_target = object
                closest_dist = dist
    return closest_target

def cast_confuse():
    monster = closest_target(CONFUSE_RANGE)
    if monster is None:
        message('No enemy is close enough to confuse.', libtcod.red)
        return 'cancelled'
    # Replace the target's AI with confused AI
    old_ai = monster.ai
    monster.ai = ConfusedMonster(old_ai)
    monster.ai.owner = monster # Let the component know who owns it
    message('The eyes of the ' + monster.name + ' look vacant, as it starts to '
            + 'stumble around!', libtcod.light_green)

def target_tile(max_range=None):
    """ Return the position of a tile left-clicked in the player's FOV or None
    if right-clicked """
    global key, mouse
    while True:
        libtcod.console_flush()
        libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE, key, mouse)
        render_all()

        (x, y) = (mouse.cx, mouse.cy)
        if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and
                (max_range is None or player.distance(x, y) <= max_range)):
            return (x, y)
        # Cancel if right-click or ESC
        if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
            return (None, None)

def cast_fireball():
    """ Ask the player for a target tile to throw a fireball at """
    message('Left-click a target tile for the fireball, or right-click to cancel.',
            libtcod.light_cyan)
    (x, y) = target_tile()
    if x is None: return 'cancelled'
    message('The fireball explodes burning everything within ' + str(FIREBALL_RADIUS)
            + ' tiles!', libtcod.orange)

    for obj in objects: # Damage every fighter in range
        if obj.distance(x, y) <= FIREBALL_RADIUS and obj.fighter:
            message('The ' + obj.name + ' gets burned for ' + str(FIREBALL_DAMAGE)
                    + ' hit points.', libtcod.orange)
            obj.fighter.take_damage(FIREBALL_DAMAGE)


################################
# Initialization and main loop #
################################
libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GRAYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/libtcod tutorial', False)
con = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)
mouse = libtcod.Mouse()
key = libtcod.Key()

# Create object representing the player
fighter_component = Fighter(hp=30, defense=2, power=5, death_function=player_death)
player = Object(0, 0, '@', 'player', libtcod.white, blocks=True, fighter=fighter_component)

objects = [player]
game_msgs = []
inventory = []

make_map()

fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
    for x in range(MAP_WIDTH):
        libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

fov_recompute = True
game_state = 'playing'
player_action = None

# A welcoming message!
message('Welcome stranger! Prepare to perish in the DeathCave(tm).', libtcod.red)

libtcod.sys_set_fps(LIMIT_FPS)

while not libtcod.console_is_window_closed():

    libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE, key, mouse)

    render_all()

    libtcod.console_flush()

    # Erase all objects in the list
    for object in objects:
        object.clear()

    player_action = handle_keys()
    if player_action == 'exit':
        break
    if game_state == 'playing' and player_action != 'didnt-take-turn':
        for object in objects:
            if object.ai:
                object.ai.take_turn()
