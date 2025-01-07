from typing import Self

from project_types import GameState, Movement, PieceKind, Location, PlayerNumber, MovePossibilities, PiecePositions, LivePiece, PlayerAction, ActionType, GameStatus, BOARD_ROWS, BOARD_COLS

class EeveeMovement:
    def get_movement_range(self, row: int, col: int, valid_locations: dict[tuple[int, int], bool]) -> list[Location]:
        
        return [
            Location(row + dr, col + dc)
            for dr, dc in MovePossibilities.FORWARD.value
            if 0 <= row + dr < BOARD_ROWS and 0 <= col + dc < BOARD_COLS and (row + dr, col + dc) in valid_locations
        ]

class EeveeShinyMovement:
    def get_movement_range(self, row: int, col: int, valid_locations: dict[tuple[int, int], bool]) -> list[Location]:
        
        return [
            Location(row + dr, col + dc)
            for dr, dc in MovePossibilities.FORWARD_OPPOSITE.value
            if 0 <= row + dr < BOARD_ROWS and 0 <= col + dc < BOARD_COLS and (row + dr, col + dc) in valid_locations
        ]

class PikachuMovement:
    def get_movement_range(self, row: int, col: int, valid_locations: dict[tuple[int, int], bool]) -> list[Location]:
        diagonals: list[Location] = []
        
        for dr, dc in MovePossibilities.DIAGONALS.value:

            temp_row, temp_col = row, col
            while 0 <= temp_row + dr < BOARD_ROWS and 0 <= temp_col + dc < BOARD_COLS and (temp_row + dr, temp_col + dc) in valid_locations:
                temp_row += dr
                temp_col += dc
                if not valid_locations[(temp_row,temp_col)]: # if encounters a location with opponent piece (False), block the range
                    diagonals.append(Location(temp_row, temp_col))
                    break
                diagonals.append(Location(temp_row, temp_col))
        
        return diagonals

class TurtwigMovement:
    def get_movement_range(self, row: int, col: int, valid_locations: dict[tuple[int, int], bool]) -> list[Location]:
        orthogonals: list[Location] = []
        
        for dr, dc in MovePossibilities.ORTHOGONALS.value:

            temp_row, temp_col = row, col
            while 0 <= temp_row + dr < BOARD_ROWS and 0 <= temp_col + dc < BOARD_COLS and (temp_row + dr, temp_col + dc) in valid_locations:
                temp_row += dr
                temp_col += dc
                if not valid_locations[(temp_row,temp_col)]: # if encounters a location with opponent piece (False), block the range
                    orthogonals.append(Location(temp_row, temp_col))
                    break
                orthogonals.append(Location(temp_row, temp_col))
        
        return orthogonals

class LatiosMovement:
    def get_movement_range(self, row: int, col: int, valid_locations: dict[tuple[int, int], bool]) -> list[Location]:
        return [
            Location(row + dr, col + dc)
            for dr, dc in MovePossibilities.ORTHOGONALS.value
            if 0 <= row + dr < BOARD_ROWS and 0 <= col + dc < BOARD_COLS and (row + dr, col + dc) in valid_locations and valid_locations[(row + dr, col + dc)] # Latios cannot capture hence only locations with True values are considered
        ]
    
class LatiasMovement:
    def get_movement_range(self, row: int, col: int, valid_locations: dict[tuple[int, int], bool]) -> list[Location]:
         return [
            Location(row + dr, col + dc)
            for dr, dc in MovePossibilities.DIAGONALS.value
            if 0 <= row + dr < BOARD_ROWS and 0 <= col + dc < BOARD_COLS and (row + dr, col + dc) in valid_locations and valid_locations[(row + dr, col + dc)]
            # Latias cannot capture hence only locations with True values are considered
        ]

class BasePiece:
    def __init__(self, kind: PieceKind, location: Location, movement: Movement, owner: PlayerNumber):
        self._kind = kind
        self.location = location
        self._movement = movement
        self._owner = owner

    @property
    def kind(self) -> PieceKind:
        return self._kind
    
    @property
    def row(self) -> int:
        return self.location.row
    
    @property
    def col(self) -> int:
        return self.location.col
    
    @property
    def owner(self) -> PlayerNumber:
        return self._owner
    
    def get_movement_range(self, grid: dict[tuple[int, int], bool]) -> list[Location]:
        return self._movement.get_movement_range(self.row, self.col, grid)
    
class Piece(BasePiece):
    def __init__(self, kind: PieceKind, location: Location, movement: Movement, owner: PlayerNumber):
        super().__init__(kind, location, movement, owner)

    def switch_ownership(self):
        self._owner = PlayerNumber.ONE if self._owner == PlayerNumber.TWO else PlayerNumber.TWO

        if self._kind == PieceKind.EEVEE:
            self._kind = PieceKind.EEVEE_SHINY
            self._movement = EeveeShinyMovement()

        elif self._kind == PieceKind.EEVEE_SHINY:
            self._kind = PieceKind.EEVEE
            self._movement = EeveeMovement()

class ProtectedPiece(BasePiece):
    def __init__(self, kind: PieceKind, location: Location, movement: Movement, owner: PlayerNumber):
        super().__init__(kind, location, movement, owner)
        self.is_immobile = False
    

class Board:
    def __init__(self, height: int, width: int):
        self._height: int = height
        self._width: int = width
        self._protected_pieces: dict[PlayerNumber, list[ProtectedPiece]] = {PlayerNumber.ONE: [], PlayerNumber.TWO: []}
        self._live_pieces: dict[PlayerNumber, list[Piece]] = {PlayerNumber.ONE: [], PlayerNumber.TWO: []}
        self._captured_pieces: dict[PlayerNumber, list[Piece]] = {PlayerNumber.ONE: [], PlayerNumber.TWO: []}
        self._grid: list[list[Piece | ProtectedPiece | None]] = [[ None for _ in range(width)] for _ in range(height)]
        ...

    def get_live_pieces(self) -> list[LivePiece]:
        """
        For GameState
        """
        return [

                LivePiece(piece.kind, piece.owner, self.get_piece_movable_locations(piece), Location(piece.row, piece.col)) 
                for piece in (self._live_pieces[PlayerNumber.ONE] + self._protected_pieces[PlayerNumber.ONE])

            ] + [

                LivePiece(piece.kind, piece.owner, self.get_piece_movable_locations(piece), Location(piece.row, piece.col)) 
                for piece in (self._live_pieces[PlayerNumber.TWO] + self._protected_pieces[PlayerNumber.TWO])
                
            ]

    def get_captured_pieces(self) -> list[LivePiece]:
        """
        For GameState
        """
        return [
            
                LivePiece(piece.kind, piece.owner, self.get_piece_droppable_locations(piece), None) 
                for piece in self._captured_pieces[PlayerNumber.ONE]

            ] + [

                LivePiece(piece.kind, piece.owner, self.get_piece_droppable_locations(piece), None) 
                for piece in self._captured_pieces[PlayerNumber.TWO]
                
            ]


    def get_live_piece(self, location: Location) -> Piece | ProtectedPiece | None:
        return self._grid[location.row][location.col]
            
    def get_captured_piece(self, kind: PieceKind, player: PlayerNumber) -> Piece | None:
        for piece in self._captured_pieces[player]:
            if piece.kind == kind:
                return piece
    
    def _live_to_captured(self, piece: Piece, captured_player: PlayerNumber, capturing_player: PlayerNumber):
        self._live_pieces[captured_player].remove(piece)
        self._captured_pieces[capturing_player].append(piece)

    def _captured_to_live(self, piece: Piece, player: PlayerNumber):
        self._captured_pieces[player].remove(piece)
        self._live_pieces[player].append(piece)

    def put(self, row: int, col: int, piece: Piece | ProtectedPiece, player: PlayerNumber):
        live_pieces = self._live_pieces[player]
        protected_pieces = self._protected_pieces[player]
        if type(piece) == Piece:
            live_pieces.append(piece)
        elif type(piece) == ProtectedPiece:
            protected_pieces.append(piece)
        self._grid[row][col] = piece

    def take(self, location: Location):
        self._grid[location.row][location.col] = None
        
    def move(self, location: Location, piece: Piece | ProtectedPiece):
        piece.location = Location(location.row, location.col)
        self._grid[location.row][location.col] = piece
    
    def capture(self, target: Location, capturing_piece: Piece):
        captured_player = PlayerNumber.TWO if capturing_piece.owner == PlayerNumber.ONE else PlayerNumber.ONE

        captured_piece = self._grid[target.row][target.col]
        self.move(target, capturing_piece)

        if captured_piece and type(captured_piece) == Piece:
            captured_piece.switch_ownership()
            self._live_to_captured(captured_piece, captured_player, captured_piece.owner)
            

    def drop(self, target: Location, piece: Piece, player: PlayerNumber):
        self.move(target, piece)
        self._captured_to_live(piece, player)

    def can_capture(self, location: Location) -> bool:
        piece = self._grid[location.row][location.col]
        if piece and type(piece) == Piece:
            return True
        
        return False
    
    def get_movable_locations_mapping(self, owner: PlayerNumber) -> dict[tuple[int, int], bool]:

        grid = self._grid
        locations: dict[tuple[int, int], bool] = {}
        """
        Location will be true if empty 
        Location will be false if opponent piece
        """

        for row in range(self._height):
            for col in range(self._width):
                piece = grid[row][col]

                if not piece:
                    locations[(row, col)] = True
                elif piece.owner != owner:
                    locations[(row, col)] = False

        return locations
    
    def get_all_movable_locations(self, player: PlayerNumber) -> list[Location]:
        locations: list[Location] = []

        for piece in self._live_pieces[player] + self._protected_pieces[player]:
            
            locations.extend(piece.get_movement_range(self.get_movable_locations_mapping(player)))

        return locations
    
    def get_piece_movable_locations(self, piece: Piece | ProtectedPiece) -> list[Location]:

        locations: list[Location] = piece.get_movement_range(self.get_movable_locations_mapping(piece.owner))

        if type(piece) == Piece:
            return [ location for location in locations if not type(self._grid[location.row][location.col]) == ProtectedPiece]
        
        return locations
    
    def get_piece_droppable_locations(self, piece: Piece) -> list[Location]:

        locations: list[Location] = []

        for row in range(self._height):
            for col in range(self._width):
                loc = Location(row, col)
                if self.is_valid_location(loc, piece.owner):
                    locations.append(loc)
        
        return locations
    
    def is_valid_location(self, location: Location, owner: PlayerNumber) -> bool:
        loc = self._grid[location.row][location.col]
        opponent: PlayerNumber = PlayerNumber.ONE if owner == PlayerNumber.TWO else PlayerNumber.TWO

        for piece in self._protected_pieces[opponent] + self._protected_pieces[owner]:
            if location in piece.get_movement_range(self.get_movable_locations_mapping(opponent)):
                return False
            
        return not loc

    def is_safe_location(self, target: Location, curr_player: PlayerNumber) -> bool:
        opponent = PlayerNumber.TWO if curr_player == PlayerNumber.ONE else PlayerNumber.ONE

        unsafe_locations = self.get_all_movable_locations(opponent)

        if target in unsafe_locations:
            return False
            
        return True

    def opponent_immobile(self, curr_player: PlayerNumber) -> bool:
        opponent = PlayerNumber.TWO if curr_player == PlayerNumber.ONE else PlayerNumber.ONE
        """
        Checks if Latias and Latios of each player can still move
        """
        # unsafe_locations = self.get_all_movable_locations(curr_player) # wrong implementation

        for protected in self._protected_pieces[opponent]:
            possible_moves = protected.get_movement_range(self.get_movable_locations_mapping(opponent))
            blocked: list[bool] = []

            # for loc in possible_moves:  wrong implementation
            #     if loc in unsafe_locations:
            #         danger.append(True)
            #     else:
            #         danger.append(False)
            for loc in possible_moves:
                if self._grid[loc.row][loc.col]:
                    blocked.append(True)
                else:
                    blocked.append(False)

            protected.is_immobile = True  if all(blocked) else False
            
        return all([piece.is_immobile for piece in self._protected_pieces[opponent]])
    
class PieceFactory:

    @classmethod
    def make(cls, piece_kind: PieceKind,
             location: Location, owner: PlayerNumber) -> Piece | ProtectedPiece:

        match piece_kind:
            case PieceKind.EEVEE:
                movement = EeveeMovement()
                return Piece(piece_kind, location, movement, owner)

            case PieceKind.EEVEE_SHINY:
                movement = EeveeShinyMovement()
                return Piece(piece_kind, location, movement, owner)

            case PieceKind.PIKACHU:
                movement = PikachuMovement()
                return Piece(piece_kind, location, movement, owner)
 
            case PieceKind.TURTWIG:
                movement = TurtwigMovement()
                return Piece(piece_kind, location, movement, owner)
 
            case PieceKind.LATIOS:
                movement = LatiosMovement()
                return ProtectedPiece(piece_kind, location, movement, owner)
 
            case PieceKind.LATIAS:
                movement = LatiasMovement()
                return ProtectedPiece(piece_kind, location, movement, owner)

class DefaultPositions:
    def get_positions(self) -> list[tuple[PlayerNumber, PieceKind, Location]]:

        # Player Two
        positions = [
            (PlayerNumber.TWO, PieceKind.TURTWIG, Location(0, 0)),
            (PlayerNumber.TWO, PieceKind.PIKACHU, Location(0, 1)),
            (PlayerNumber.TWO, PieceKind.LATIOS, Location(0, 3)),
            (PlayerNumber.TWO, PieceKind.LATIAS, Location(0, 4)),
            (PlayerNumber.TWO, PieceKind.PIKACHU, Location(0, 6)),
            (PlayerNumber.TWO, PieceKind.TURTWIG, Location(0, 7)),
        ]

        positions += [
            (PlayerNumber.TWO, PieceKind.EEVEE_SHINY, Location(1, n)) for n in range(BOARD_COLS)
        ]

        # Player One
        positions += [
            (PlayerNumber.ONE, PieceKind.TURTWIG, Location(7, 0)),
            (PlayerNumber.ONE, PieceKind.PIKACHU, Location(7, 1)),
            (PlayerNumber.ONE, PieceKind.LATIOS, Location(7, 3)),
            (PlayerNumber.ONE, PieceKind.LATIAS, Location(7, 4)),
            (PlayerNumber.ONE, PieceKind.PIKACHU, Location(7, 6)),
            (PlayerNumber.ONE, PieceKind.TURTWIG, Location(7, 7)),
        ]

        positions += [
            (PlayerNumber.ONE, PieceKind.EEVEE, Location(6, n)) for n in range(BOARD_COLS)
        ]

        return positions

# If we need to add game pieces, we create another PiecePosition Class

class BoardSetter:
    def __init__(self, positions: PiecePositions):
        self._positions = positions.get_positions()
    
    def set_board(self, board: Board):


        for player, kind, location in self._positions:
            piece = PieceFactory.make(kind, location, player)
            board.put(location.row, location.col, piece, player)

class GameModel:
    @classmethod
    def default(cls) -> Self:

        board = Board(BOARD_ROWS, BOARD_COLS)

        setter = BoardSetter(DefaultPositions())
        setter.set_board(board)


        state = GameState(
            active_player = PlayerNumber.ONE,
            captured_pieces= board.get_captured_pieces(),
            live_pieces=board.get_live_pieces(),
            action_count=3,
            game_status=GameStatus.ONGOING
        )

        return cls(state, board, PlayerNumber.ONE, 3)


    def __init__(self, state: GameState, board: Board, player: PlayerNumber, action_count: int):
        self._state = state
        self._board = board
        self._active_player = player
        self._action_count = action_count
        self._game_status: GameStatus = GameStatus.ONGOING
    
    @property
    def state(self) -> GameState:
        return self._state
    
    def _update_turn_status(self):
        if self._action_count == 0 and GameStatus.ONGOING:
            self._active_player = PlayerNumber.ONE if self._active_player == PlayerNumber.TWO else PlayerNumber.TWO
            self._action_count = 3
    
    def _update_state(self):

        self._state = GameState(
            active_player = self._active_player,
            captured_pieces= self._board.get_captured_pieces(),
            live_pieces=self._board.get_live_pieces(),
            action_count=self._action_count,
            game_status=self._game_status
        )

    def _check_if_game_over(self) -> PlayerNumber | None:
        board = self._board
        winner = None
        if board.opponent_immobile(self._active_player):
           winner = self._active_player
           self._game_status= GameStatus.PLAYER_WIN if winner == PlayerNumber.ONE else GameStatus.PLAYER_LOSE

    def make_action(self, action: PlayerAction):
        board = self._board
        target = action.target_location
        source = action.source_location
        kind = action.kind
        player = action.player

        print(target, source, kind, player)
        match action.action_type:

            case ActionType.MOVE:
                if source:
                    print("I am moving!")
                    piece_to_move = board.get_live_piece(source)

                    # Narrow type down
                    if piece_to_move:
                        
                        # If regular piece, capture or move
                        if type(piece_to_move) == Piece:
                            board.take(source)

                            # Check if can capture
                            if board.can_capture(target):
                                
                                board.capture(target, piece_to_move)

                            # Move piece simply  
                            else:
                                board.move(target, piece_to_move)

                        # If protected piece, check if target location is valid
                        elif type(piece_to_move) == ProtectedPiece:
                            board.take(source)
                            board.move(target, piece_to_move)


            case ActionType.DROP:
                piece_to_drop = board.get_captured_piece(kind, player)

                if piece_to_drop and board.is_valid_location(target, player):
                    board.drop(target, piece_to_drop, player)

        self._action_count -= 1
        self._check_if_game_over()
        self._update_turn_status()
        self._update_state()
        
    def new_game(self):
        self._board = Board(BOARD_ROWS, BOARD_COLS)
        setter = BoardSetter(DefaultPositions())
        setter.set_board(self._board)

        self._state = GameState(
            active_player = PlayerNumber.ONE,
            captured_pieces= self._board.get_captured_pieces(),
            live_pieces=self._board.get_live_pieces(),
            action_count=3,
            game_status=GameStatus.ONGOING
        )

        self._active_player = PlayerNumber.ONE
        self._action_count = 3
        self._game_status: GameStatus = GameStatus.ONGOING
