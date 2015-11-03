import libtcodpy as libtcod
import game_builder
import game_deconstructor
import data_transfer_module
import game_builder

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

def handle_keys():
    global playerx, playery
    key = libtcod.console_wait_for_keypress(True)
    
    if key.vk == libtcod.KEY_ENTER and key.lalt:
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
    
    elif key.vk == libtcod.KEY_ESCAPE:
        return True
    
    if libtcod.console_is_key_pressed(libtcod.KEY_UP):
        playery -= 1
    elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
        playery += 1
    elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
        playerx += 1
    elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
        playerx -= 1

playerx = SCREEN_WIDTH/2
playery = SCREEN_HEIGHT/2

libtcod.console_set_custom_font(
    'arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'test_server', False)

while not libtcod.console_is_window_closed():
    libtcod.console_set_default_foreground(0, libtcod.white)
    libtcod.console_put_char(
        0, playerx, playery, '@', libtcod.BKGND_NONE)
    libtcod.console_flush()
    
    libtcod.console_put_char(0, playerx, playery, ' ', libtcod.BKGND_NONE)
    
    exit = handle_keys()
    
    if exit:
        break
    
    data = [SCREEN_WIDTH, SCREEN_HEIGHT, playerx, playery]
    json_data = game_deconstructor.serialize(data)
    data_transfer_module.transfer(json_data)
    print game_builder.SCREEN_WIDTH
    
