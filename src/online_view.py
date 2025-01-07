import pygame
from cs150241project_networking import CS150241ProjectNetworking, Message

from project_types import (
    GameStatus, PieceKind, ActionType, Location, PlayerNumber,
    GameState, PlayerAction,
    )
from view import *

class DataParser:
    """
    Abstraction that only parses messages to type PlayerAction and vice versa; for SRP compliance
    """
    def parse_to_message(self, server_id, action: PlayerAction) -> Message | None:
        """Convert type PlayerAction to message (if valid; else None)"""
        source_loc = f"{ action.source_location.row }-{ action.source_location.col }" if action.source_location \
            else f""
        
        payload = f"{ action.action_type.value }%{ action.player.value }%{ source_loc }%{ action.target_location.row }-{ action.target_location.col }%{ action.kind }"

        return Message(server_id, payload)
    
    def parse_to_player_action(self, message: Message) -> PlayerAction | None:
        """Convert type message to PlayerAction (if valid; else None)"""
        properties = message.payload.split('%')

        if len(properties) != 5:
            return None

        action_type = ActionType.MOVE if properties[0] == ActionType.MOVE else ActionType.DROP

        return PlayerAction(
            action_type,
            player = PlayerNumber.ONE if properties[1] == PlayerNumber.ONE else PlayerNumber.TWO,
            source_location = \
                None if action_type == ActionType.DROP \
                else Location(int(properties[2][0]), int(properties[2][2])),
            target_location = Location(int(properties[3][0]), int(properties[3][2])),
            kind = PieceKind(properties[4])
            )

class OnlineView(GameView):
    """
    MVC class for online implementation
    """
    def __init__(self, state: GameState):
        super().__init__(state)

        self._networking = CS150241ProjectNetworking.connect('localhost', 15000)
        self._server_id = self._networking.player_id

        self._viewing_player = PlayerNumber.ONE if self._server_id == 1 else PlayerNumber.TWO

    def _is_valid_move(self):
        """Check if move is for own piece and current active player"""
        return self._viewing_player == self._active_player

    def _send_to_server(self, action: PlayerAction):
        """Send player's message to network --- no local actions done"""
        message = DataParser().parse_to_message(self._server_id, action)

        if message:
            self._networking.send(message.payload)

    def _receive_from_server(self, message: Message):
        """Use received message to manipulate client"""
        _received_turn = DataParser().parse_to_player_action(message)

        if _received_turn:
            self._make_turn(_received_turn)
            self._rerender_after_turn()

    def _render_player_number(self):
        """Render viewing player, and if it's their turn (green) or not (white)"""
        _renderable = self._font.render(
            f"P{self._server_id}",
            True,
            'green' if self._active_player == self._viewing_player else 'white'
            )
        _blittable = _renderable.get_rect(centery = SCREEN_HEIGHT//2)

        self._screen.blit(_renderable, _blittable)

    def run(self):
        """Edited to incorporate networking"""
        pygame.init()

        self._screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._clock = pygame.time.Clock()

        _game_is_running = True

        while _game_is_running:
            """Receive input from server"""
            for message in self._networking.recv():
                self._receive_from_server(message)

            "Receive input from client"
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    _game_is_running = False

                elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    self._new_game()
                    self._init_view_state()

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self._is_valid_move():
                    if self._renderable_board.rect.collidepoint(event.pos):
                        _player_turn = self._mouse_press_on_board(event.pos)

                        if _player_turn:
                            self._send_to_server(_player_turn)
                    
                    elif self._is_cursor_on_captures(event.pos):
                        self._mouse_press_on_captures(event.pos, self._active_player)

            self._screen.fill('black')
            self._captures_p1.render_to_screen(self._screen)
            self._captures_p2.render_to_screen(self._screen)
            self._renderable_board.render_to_screen(self._screen)
            self._render_player_number()

            if self._game_status != GameStatus.ONGOING:
                self._evaluate_winner()

            pygame.display.flip()
            self._clock.tick(60)

        pygame.quit()