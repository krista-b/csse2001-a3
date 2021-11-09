"""Class for representing a Player entity within the game."""

__version__ = "1.1.0"

from game.entity import DynamicEntity
import time


class Player(DynamicEntity):
    """A player in the game"""
    _type = 3

    def __init__(self, name, max_health: float = 20):
        """Construct a new instance of the player.

        Parameters:
            name (str): The player's name
            max_health (float): The player's maximum & starting health
        """
        super().__init__(max_health=max_health)

        self._name = name
        self._score = 0
        self._health = self._max_health
        self._invincible = False
        self._pass = False
        self._ducking = False
        self._switch = False

    def get_name(self) -> str:
        """(str): Returns the name of the player."""
        return self._name

    def get_score(self) -> int:
        """(int): Returns the players current score."""
        return self._score

    def change_score(self, change: float = 1):
        """Increase the players score by the given change value."""
        self._score += change

    def set_health(self, health: float = 1):
        """Set the players current health to the given float value."""
        self._health = health
    
    def change_health(self, change: float = 1):
        """Increase the players health by the given float value."""
        if not self.is_invincible():
            self._health += change
        else:
            pass

    def is_invincible(self) -> bool:
        """(bool): Returns true if the player is invincible."""
        return self._invincible

    def change_invincibility(self, invincible: bool):
        """Set the players invincibility status to the given boolean value."""
        self._invincible = self._pass = invincible

    def get_time(self) -> float:
        """(float): Returns the time at which the player becomes invincible."""
        if self._pass:
            self._pass = not self._pass
            self._start_time = time.time()
        return self._start_time

    def is_ducking(self) -> bool:
        """(bool): Returns true if the player is ducking currently."""
        return self._ducking

    def set_ducking(self, ducking: bool):
        """Set the players ducking status to the given boolean value."""
        self._ducking = ducking

    def on_switch(self):
        """(bool): Returns true if the player is currently on the switch block."""
        return self._switch

    def set_on_switch(self, on_switch):
        """Set the players on switch status to the given boolean value."""
        self._switch = on_switch

    def __repr__(self):
        """Returns the players string representation."""
        return f"Player({self._name!r})"
