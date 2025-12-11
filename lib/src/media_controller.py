"""
Media controller for managing player pause/resume during dictation
"""

import subprocess
from typing import List, Optional


class MediaController:
    """Controls media player pause/resume via playerctl/MPRIS"""

    def __init__(self, config_manager=None):
        """
        Initialize media controller

        Args:
            config_manager: ConfigManager instance for accessing settings
        """
        self.config_manager = config_manager

        # Load configuration
        if self.config_manager:
            self.enabled = self.config_manager.get_setting(
                "media_pause_on_dictation", False
            )
        else:
            self.enabled = False

        # Track which players were paused
        self.paused_players: List[str] = []

        # Check if playerctl is available
        self.playerctl_available = self._check_playerctl_available()

    def _check_playerctl_available(self) -> bool:
        """Check if playerctl command is available on the system"""
        try:
            result = subprocess.run(
                ["which", "playerctl"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _execute_playerctl(self, args: List[str]) -> bool:
        """
        Execute a playerctl command safely

        Args:
            args: List of arguments to pass to playerctl (e.g., ['pause'] or ['play', '-p', 'spotify'])

        Returns:
            True if command succeeded, False otherwise
        """
        try:
            cmd = ["playerctl"] + args
            result = subprocess.run(cmd, capture_output=True, timeout=5, check=False)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def _get_active_players(self) -> List[str]:
        """
        Get list of currently playing media players

        Returns:
            List of player names that are currently playing
        """
        try:
            result = subprocess.run(
                ["playerctl", "--list-all"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode != 0:
                return []

            # Get list of all players
            all_players = result.stdout.strip().split("\n")
            all_players = [p.strip() for p in all_players if p.strip()]

            # Check which players are currently playing (status = "Playing")
            playing_players = []
            for player in all_players:
                try:
                    status_result = subprocess.run(
                        ["playerctl", "-p", player, "status"],
                        capture_output=True,
                        text=True,
                        timeout=2,
                        check=False,
                    )
                    if status_result.returncode == 0:
                        status = status_result.stdout.strip()
                        if status == "Playing":
                            playing_players.append(player)
                except Exception:
                    continue

            return playing_players
        except Exception:
            return []

    def pause_active_players(self) -> bool:
        """
        Pause all currently playing media players

        Tracks which players were paused so they can be resumed later.

        Returns:
            True if at least one player was paused, False if none were playing
        """
        if not self.enabled or not self.playerctl_available:
            self.paused_players = []
            return False

        try:
            # Get list of currently playing players
            self.paused_players = self._get_active_players()

            if not self.paused_players:
                return False

            # Pause all playing players
            for player in self.paused_players:
                self._execute_playerctl(["-p", player, "pause"])

            return True
        except Exception:
            self.paused_players = []
            return False

    def resume_paused_players(self) -> bool:
        """
        Resume media players that were paused during dictation

        Only resumes players that were tracked as paused, ignoring any
        players that may have exited during dictation.

        Returns:
            True if at least one player was resumed, False otherwise
        """
        if not self.enabled:
            self.paused_players = []
            return False

        if not self.paused_players:
            return False

        try:
            resumed_count = 0
            for player in self.paused_players:
                # Try to resume each player; skip if it no longer exists
                if self._execute_playerctl(["-p", player, "play"]):
                    resumed_count += 1

            # Clear the paused players list regardless of resume success
            self.paused_players = []

            return resumed_count > 0
        except Exception:
            self.paused_players = []
            return False

    def is_enabled(self) -> bool:
        """Check if media pause feature is enabled"""
        return self.enabled
