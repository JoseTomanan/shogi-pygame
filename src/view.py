"""
Offline implementation of the game (pass and play);
Implemented first before online version in online_view, i.e. GameView superclasses OnlineView.
"""
import pygame

from project_types import (
    TILE_PIXELS, BOARD_ROWS, BOARD_COLS,
    GameStatus, PieceKind, ActionType, Location, PlayerNumber,
    LivePiece, GameState, PlayerAction,
    MakeTurnObserver, NewGameObserver,
    )

SCREEN_WIDTH = 768
SCREEN_HEIGHT = 720
BOARD_WIDTH = TILE_PIXELS*BOARD_ROWS
BOARD_HEIGHT = TILE_PIXELS*BOARD_COLS


def get_blittable(piece: LivePiece) -> pygame.Surface:
    """Return surface from piece, for use with blit"""
    if piece.kind == PieceKind.EEVEE_SHINY:
        _path = "./img/eevee-shiny.png"

    elif piece.owner == PlayerNumber.TWO:
        _path = "./img/" + piece.kind.value + "-shiny.png"

    else:
        _path = "./img/" + piece.kind.value + ".png"

    _transformable = pygame.image.load(_path).convert_alpha()
    returnable = pygame.transform.scale(_transformable, (64, 64))

    return returnable


class Captures:
    """Renderable class for player captures (top and bottom of game screen)"""
    def __init__(self, number: PlayerNumber):
        self._captures: list[LivePiece] = []
        self._owner = number

        self._actual_row = pygame.Surface((TILE_PIXELS*12, TILE_PIXELS*2))

        pygame.font.init()
        self._font = pygame.font.SysFont('Arial', 25)

    @property
    def owner(self) -> PlayerNumber:
        return self._owner
    
    @property
    def len(self) -> int:
        return len(self._captures)
    
    @property
    def rect(self) -> pygame.Rect:
        """Return surface rect with appropriate location; For calculating mouse collision"""
        match self._owner:
            case PlayerNumber.ONE:
                return self._actual_row.get_rect(centerx=SCREEN_WIDTH//2, bottom=SCREEN_HEIGHT)

            case PlayerNumber.TWO:
                return self._actual_row.get_rect(centerx=SCREEN_WIDTH//2, top=0)
            
    def set_captures(self, captures: list[LivePiece]):
        self._captures = captures
    
    def get_chosen_capture(self, col: int) -> LivePiece:
        """Get clicked capture"""
        return self._captures[col]

    def render_to_screen(self, screen: pygame.Surface):
        actual_captures = self._render_row()
        screen.blit(actual_captures, self.rect)

    def _render_row(self) -> pygame.Surface:
        """Render captured pieces in respective row"""
        pygame.Surface.fill(self._actual_row, 'black')
        
        order_in_screen = 0
        
        for piece in self._captures:
            _blittable = get_blittable(piece)
            
            match self._owner:
                case PlayerNumber.ONE:
                    _top: int = TILE_PIXELS if order_in_screen < 11 else 0
                case PlayerNumber.TWO:
                    _top: int = 0 if order_in_screen < 11 else TILE_PIXELS

            self._actual_row.blit(_blittable, (TILE_PIXELS * (order_in_screen%11), _top))
        
            order_in_screen += 1

        return self._actual_row

class Tile:
    """Renderable class for each tile inside board"""
    def __init__(self, location: Location):
        """Infer implicit info from occupier: type LivePiece => occupied, type None => unoccupied"""
        self._location = location
        self._topleft = location.pixels
        self._occupier: LivePiece | None = None
        self._is_targetable = False

        self._actual_tile = pygame.Surface((TILE_PIXELS, TILE_PIXELS))

    @property
    def rect(self) -> pygame.Rect:
        """Return surface rect with appropriate location; For calculating mouse collision"""
        return self._actual_tile.get_rect(topleft=self._topleft)

    @property
    def occupier(self) -> LivePiece | None:
        return self._occupier
    
    @property
    def is_targetable(self) -> bool:
        return self._is_targetable

    def mark_occupied(self, piece: LivePiece):
        self._occupier = piece

    def mark_empty(self):
        self._occupier = None

    def mark_targetable(self):
        self._is_targetable = True

    def unmark_targetable(self):
        self._is_targetable = False

    def render_to_board(self, board: pygame.Surface):
        pygame.Surface.fill(self._actual_tile, 'white')
        pygame.draw.rect(self._actual_tile, "black", pygame.Rect(0, 0, TILE_PIXELS, TILE_PIXELS), width=1)
        
        if self._occupier is not None:
            _blittable = get_blittable(self._occupier)
            self._actual_tile.blit(_blittable, (0,0))

        if self._is_targetable:
            pygame.draw.circle(self._actual_tile, 'blue', (TILE_PIXELS//2, TILE_PIXELS//2), 16.0)

        board.blit(self._actual_tile, self.rect)

class RenderableBoard:
    """Renderable class for board; contains all tiles"""
    def __init__(self, live_pieces: list[LivePiece]):
        self._location_to_tile: dict[Location, Tile] = {
            Location(i, j) : Tile(Location(i, j))
            for i in range(BOARD_ROWS)
            for j in range(BOARD_COLS)
        }
        self._all_locations = [Location(i, j) for i in range(BOARD_ROWS) for j in range(BOARD_COLS)]
        self._actual_board = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))

        self.set_board_state(live_pieces)

    @property
    def rect(self) -> pygame.Rect:
        """Return surface rect with appropriate location; For calculating mouse collision"""
        return self._actual_board.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
    
    def get_tile(self, location: Location) -> Tile:
        return self._location_to_tile[location]

    def set_board_state(self, live_pieces: list[LivePiece]):
        """Set board according to current live pieces (preferably take from game state instance)"""
        spaces = self._all_locations + []

        for piece in live_pieces:
            if piece.location is not None:
                spaces.remove(piece.location)
                self._location_to_tile[piece.location].mark_occupied(piece)

        for space in spaces:
            self._location_to_tile[space].mark_empty()

    def mark_nearby_targetable(self, location: Location):
        selected_piece = self._location_to_tile[location].occupier

        if selected_piece is not None:
            self.unmark_all()

            for loc in selected_piece.moves:
                self._location_to_tile[loc].mark_targetable()

    def mark_droppable(self, list_loc: list[Location]):
        for loc in list_loc:
            self._location_to_tile[loc].mark_targetable()

    def unmark_all(self):
        for loc in self._location_to_tile:
            self._location_to_tile[loc].unmark_targetable()

    def render_to_screen(self, screen: pygame.Surface):
        pygame.Surface.fill(self._actual_board, 'black')

        for k in self._location_to_tile:
            self._location_to_tile[k].render_to_board(self._actual_board)
        
        screen.blit(self._actual_board, self.rect)

class GameView:
    """Actual MVC view class"""
    def __init__(self, state: GameState):
        self.on_state_change(state)

        self._make_turn_observers: list[MakeTurnObserver] = []
        self._new_game_observers: list[NewGameObserver] = []

        pygame.font.init()
        self._font = pygame.font.SysFont('Arial', 25)

        self._init_view_state()

    def _init_view_state(self):
        """
        Infer implicit player move status (if current_hovered_piece is not None):
        If current_hovered_location == None, then a capture is currently selected.
        Else, piece on board is selected.
        """
        self._renderable_board = RenderableBoard(self._live_pieces)
        self._captures_p1 = Captures(PlayerNumber.ONE)
        self._captures_p2 = Captures(PlayerNumber.TWO)

        self._current_hovered_location: Location | None = None
        self._current_hovered_piece: LivePiece | None = None

    def on_state_change(self, state: GameState):
        """Update view state based on passed GameState"""
        self._active_player = state.active_player

        self._all_captures: dict[PlayerNumber, list[LivePiece]] = {PlayerNumber.ONE: [], PlayerNumber.TWO: []}

        for piece in state.captured_pieces:
            self._all_captures[piece.owner].append(piece)

        self._live_pieces = state.live_pieces
        self._action_count = state.action_count
        self._game_status = state.game_status

    def _rerender_after_turn(self):
        """For showing state of board every after turn; works with properties established by on_state_change"""
        self._renderable_board.unmark_all()
        self._renderable_board.set_board_state(self._live_pieces)

        self._captures_p1.set_captures(self._all_captures[PlayerNumber.ONE])
        self._captures_p2.set_captures(self._all_captures[PlayerNumber.TWO])

        self._current_hovered_location = None
        self._current_hovered_piece = None

    def register_make_turn_observer(self, observer: MakeTurnObserver):
        "For registering controller as observer"
        self._make_turn_observers.append(observer)

    def register_new_game_observer(self, observer: NewGameObserver):
        "For registering controller as observer"
        self._new_game_observers.append(observer)

    def _evaluate_winner(self):
        """Evaluate game-end on-screen render"""
        if self._game_status == GameStatus.PLAYER_WIN:
            self._render_text("Game Verdict: Player 1 won!")

        elif self._game_status == GameStatus.PLAYER_LOSE:
            self._render_text("Game Verdict: Player 2 won!")
            
        elif self._game_status == GameStatus.GAME_DRAW:
            self._render_text("Game Verdict: Draw")

    def _make_turn(self, action: PlayerAction):
        "For interaction with controller"
        for observer in self._make_turn_observers:
            observer.on_make_turn(action)

    def _new_game(self):
        "For interaction with controller"
        for observer in self._new_game_observers:
            observer.on_new_game()

    def _render_text(self, text: str):
        """Print text on screen using Pygame"""
        result_text = self._font.render(text, True, 'black')
        _blittable = result_text.get_rect(center = (SCREEN_WIDTH//2, SCREEN_HEIGHT//2))

        self._screen.blit(result_text, _blittable)

    def _mouse_press_on_board(self, abs_pos: tuple[int, int]) -> PlayerAction | None:
        """When mouse is clicked inside RenderableBoard rect"""
        if self._game_status == GameStatus.ONGOING:
            _row = (abs_pos[1] - 105) // TILE_PIXELS
            _col = (abs_pos[0] - 129) // TILE_PIXELS

            tile = self._renderable_board.get_tile(Location(_row,_col))

            if tile.occupier is not None and tile.occupier.owner == self._active_player:
                self._start_move_turn(Location(_row,_col))
                return None

            elif tile.is_targetable and self._current_hovered_piece is not None:
                _player_turn = self._finish_turn(Location(_row, _col))
                return _player_turn

    def _start_move_turn(self, loc: Location):
        """Hover piece (to see possible moves)"""
        self._current_hovered_location = loc
        self._current_hovered_piece = self._renderable_board.get_tile(loc).occupier

        self._renderable_board.mark_nearby_targetable(loc)

    def _finish_turn(self, loc: Location) -> PlayerAction:
        "Finish either move turn or drop turn"
        assert self._current_hovered_piece is not None

        if self._current_hovered_location is not None:
            """Finish move turn"""
            return PlayerAction(
                ActionType.MOVE,
                self._active_player,
                self._current_hovered_location,
                loc,
                self._current_hovered_piece.kind
                )
        
        "Finish drop turn"
        return PlayerAction(
            ActionType.DROP,
            self._active_player,
            None,
            loc,
            self._current_hovered_piece.kind
            )

    def _mouse_press_on_captures(self, abs_pos: tuple[int, int], player: PlayerNumber):
        """When mouse is clicked inside Captures rect"""
        if self._game_status == GameStatus.ONGOING:
            _col = abs_pos[0] // TILE_PIXELS
            self._current_hovered_location = None

            match player:
                case PlayerNumber.ONE:
                    if _col <= self._captures_p1.len:
                        self._current_hovered_piece = self._captures_p1.get_chosen_capture(_col)
                    else: return
                    
                case PlayerNumber.TWO:
                    if _col <= self._captures_p2.len:
                        self._current_hovered_piece = self._captures_p2.get_chosen_capture(_col)
                    else: return

            self._renderable_board.mark_droppable(self._current_hovered_piece.moves)

    def _is_cursor_on_captures(self, pos: tuple[int, int]):
        return (self._active_player == PlayerNumber.ONE and self._captures_p1.rect.collidepoint(pos)) \
                    or (self._active_player == PlayerNumber.TWO and self._captures_p2.rect.collidepoint(pos))

    def run(self):
        """Main game running logic; Equivalent to main()"""
        pygame.init()

        self._screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._clock = pygame.time.Clock()

        _game_is_running = True

        while _game_is_running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    _game_is_running = False

                elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    self._new_game()
                    self._init_view_state()

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._renderable_board.rect.collidepoint(event.pos):
                        _player_turn = self._mouse_press_on_board(event.pos)

                        if _player_turn is not None:
                            self._make_turn(_player_turn)
                            self._rerender_after_turn()
                    
                    elif self._is_cursor_on_captures(event.pos):
                        self._mouse_press_on_captures(event.pos, self._active_player)

            self._screen.fill('black')
            self._captures_p1.render_to_screen(self._screen)
            self._captures_p2.render_to_screen(self._screen)
            self._renderable_board.render_to_screen(self._screen)

            if self._game_status != GameStatus.ONGOING:
                self._evaluate_winner()

            pygame.display.flip()

            self._clock.tick(60)

        pygame.quit()