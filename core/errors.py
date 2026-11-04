"""Exceptions raised by the core."""


class InvalidMoveError(ValueError):
    """The requested move is not allowed (outside the board, game over...)."""
