"""
Interactive manual testing script for MediaController.
Allows testing pause and resume functionality with real media players.
Run with: python3 test_media_controller.py
"""

import subprocess
import sys
import os
import time

# Add the lib directory to the path so we can import media_controller
lib_path = os.path.join(os.path.dirname(__file__), "lib")
src_path = os.path.join(lib_path, "src")
sys.path.insert(0, src_path)
sys.path.insert(0, lib_path)

from media_controller import MediaController


def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title):
    """Print a section header"""
    print(f"\n--- {title} ---")


def print_result(test_name, status, details=""):
    """Print test result with status"""
    status_str = "✓ PASS" if status else "✗ FAIL"
    print(f"[{status_str}] {test_name}")
    if details:
        print(f"      {details}")


def get_active_players():
    """Get list of currently active players"""
    try:
        result = subprocess.run(
            ["playerctl", "--list-all"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            players = [
                p.strip() for p in result.stdout.strip().split("\n") if p.strip()
            ]
            return players
    except Exception as e:
        print(f"Error getting players: {e}")
    return []


def get_player_status(player):
    """Get status of a specific player"""
    try:
        result = subprocess.run(
            ["playerctl", "-p", player, "status"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "Unknown"


def check_playerctl_available():
    """Check if playerctl is installed"""
    try:
        result = subprocess.run(["which", "playerctl"], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def test_initialization():
    """Test MediaController initialization"""
    print_section("Test 1: Initialization")

    # Test without config manager
    controller = MediaController(config_manager=None)
    print_result(
        "Initialize without config manager",
        not controller.enabled,
        f"enabled={controller.enabled}",
    )

    # Test playerctl availability
    available = check_playerctl_available()
    print_result(
        "Check playerctl availability", available, f"playerctl available={available}"
    )

    if not available:
        print(
            "\nWARNING: playerctl not found. Install it to test pause/resume functionality."
        )
        print("  Ubuntu/Debian: sudo apt install playerctl")
        print("  Arch: sudo pacman -S playerctl")
        print("  Fedora: sudo dnf install playerctl")

    return controller, available


def test_get_active_players(controller):
    """Test getting active players"""
    print_section("Test 2: Get Active Players")

    players = get_active_players()
    print(f"Active players found: {players if players else 'None'}")
    print_result(
        "Get active players",
        True,
        f"Found {len(players)} player(s): {', '.join(players) if players else 'none'}",
    )

    if players:
        for player in players:
            status = get_player_status(player)
            print(f"  - {player}: {status}")

    return players


def test_pause_functionality(controller):
    """Test pausing functionality"""
    print_section("Test 3: Pause Functionality")

    print("\nStarting pause test...")
    print("Make sure you have music playing before continuing!")
    input("Press Enter when music is playing...")

    # Check what's playing
    players_before = get_active_players()
    print(f"\nPlayers before pause: {players_before}")

    statuses_before = {}
    for player in players_before:
        statuses_before[player] = get_player_status(player)
        print(f"  {player}: {statuses_before[player]}")

    # Pause
    print("\n>>> Calling pause_active_players()...")
    result = controller.pause_active_players()
    print_result(
        "pause_active_players() call",
        result,
        f"Returned: {result}, Paused players tracked: {controller.paused_players}",
    )

    # Check status after pause
    print("\nChecking player statuses after pause...")
    time.sleep(0.5)  # Give players a moment to pause

    statuses_after = {}
    for player in players_before:
        statuses_after[player] = get_player_status(player)
        print(f"  {player}: {statuses_after[player]}")

        # Verify it's paused
        if statuses_after[player] == "Paused":
            print_result(f"    {player} is paused", True)
        else:
            print_result(
                f"    {player} is paused", False, f"Status: {statuses_after[player]}"
            )

    return controller, statuses_before, statuses_after


def test_resume_functionality(controller):
    """Test resume functionality"""
    print_section("Test 4: Resume Functionality")

    print(f"\nPaused players tracked: {controller.paused_players}")

    if not controller.paused_players:
        print("No paused players to resume. Skipping resume test.")
        print_result("Resume test", False, "No paused players")
        return

    input("Press Enter to resume the paused players...")

    print("\n>>> Calling resume_paused_players()...")
    result = controller.resume_paused_players()
    print_result("resume_paused_players() call", result, f"Returned: {result}")

    # Check status after resume
    print("\nChecking player statuses after resume...")
    time.sleep(0.5)  # Give players a moment to resume

    # Note: we need to check all players since paused_players list is cleared
    all_players = get_active_players()
    for player in all_players:
        status = get_player_status(player)
        print(f"  {player}: {status}")
        if status == "Playing":
            print_result(f"    {player} is playing", True)


def test_pause_resume_cycle(controller):
    """Test a complete pause-resume cycle"""
    print_section("Test 5: Complete Pause-Resume Cycle")

    print("\nThis test will:")
    print("1. Check current players")
    print("2. Pause them")
    print("3. Wait (simulating dictation)")
    print("4. Resume them")

    input("\nPress Enter to start (make sure music is playing)...")

    # Get baseline
    players = get_active_players()
    if not players:
        print("No active players found. Cannot run cycle test.")
        print_result("Pause-resume cycle", False, "No active players")
        return

    print(f"\nStep 1: Initial state")
    print(f"  Active players: {players}")
    for player in players:
        print(f"  {player}: {get_player_status(player)}")

    print(f"\nStep 2: Pausing...")
    pause_result = controller.pause_active_players()
    print_result("Pause call", pause_result)
    time.sleep(0.5)

    print(f"  Players after pause:")
    for player in players:
        print(f"  {player}: {get_player_status(player)}")

    print(f"\nStep 3: Simulating dictation (waiting 3 seconds)...")
    for i in range(3):
        time.sleep(1)
        print(f"  [{i + 1}/3] Dictating...")

    print(f"\nStep 4: Resuming...")
    resume_result = controller.resume_paused_players()
    print_result("Resume call", resume_result)
    time.sleep(0.5)

    print(f"  Players after resume:")
    for player in players:
        print(f"  {player}: {get_player_status(player)}")

    print_result(
        "Complete pause-resume cycle",
        pause_result and resume_result,
        "Both pause and resume succeeded",
    )


def test_disabled_feature():
    """Test behavior when feature is disabled"""
    print_section("Test 6: Disabled Feature")

    # Create controller with feature disabled
    controller = MediaController(config_manager=None)
    controller.enabled = False

    print("Feature disabled, attempting pause...")
    result = controller.pause_active_players()
    print_result("Pause with feature disabled", not result, f"Correctly returned False")

    print("Feature disabled, attempting resume...")
    controller.paused_players = ["test_player"]  # Manually set some paused players
    result = controller.resume_paused_players()
    print_result(
        "Resume with feature disabled", not result, f"Correctly returned False"
    )


def test_edge_cases():
    """Test edge cases"""
    print_section("Test 7: Edge Cases")

    controller = MediaController(config_manager=None)
    controller.enabled = True

    # Test resume with no paused players
    print("Testing resume with no paused players...")
    controller.paused_players = []
    result = controller.resume_paused_players()
    print_result(
        "Resume with empty paused_players", not result, f"Correctly returned False"
    )

    # Test is_enabled
    print("\nTesting is_enabled() method...")
    controller.enabled = True
    result1 = controller.is_enabled()
    print_result("is_enabled() when enabled=True", result1)

    controller.enabled = False
    result2 = controller.is_enabled()
    print_result("is_enabled() when enabled=False", not result2)


def interactive_menu():
    """Show interactive menu for manual testing"""
    print_header("MediaController Interactive Testing")

    print("\nOptions:")
    print("1. Run all tests")
    print("2. Test initialization only")
    print("3. Test get active players")
    print("4. Test pause functionality")
    print("5. Test resume functionality (uses paused players from option 4)")
    print("6. Test complete pause-resume cycle")
    print("7. Test disabled feature")
    print("8. Test edge cases")
    print("9. Clear paused players")
    print("10. Exit")

    choice = input("\nSelect option (1-10): ").strip()
    return choice


def main():
    """Main test runner"""
    print_header("MediaController Manual Testing Script")

    print("\nThis script tests the MediaController with REAL media players.")
    print("You can interact with it manually and see actual pause/resume behavior.")
    print("\nIMPORTANT: Use options 4 and 5 sequentially for proper testing.")
    print("The same controller instance is used to preserve paused_players state.")

    # Check playerctl first
    if not check_playerctl_available():
        print("\n⚠️  WARNING: playerctl is not installed!")
        print("Install it first:")
        print("  Ubuntu/Debian: sudo apt install playerctl")
        print("  Arch: sudo pacman -S playerctl")
        print("  Fedora: sudo dnf install playerctl")
        return

    # Create a persistent controller for options 4 and 5
    persistent_controller = None

    while True:
        choice = interactive_menu()

        if choice == "1":
            # Run all tests
            controller, available = test_initialization()
            if not available:
                break

            players = test_get_active_players(controller)

            if players:
                test_pause_functionality(controller)
                if controller.paused_players:
                    test_resume_functionality(controller)
                test_pause_resume_cycle(controller)

            test_disabled_feature()
            test_edge_cases()

            print_header("All Tests Complete")
            persistent_controller = None

        elif choice == "2":
            controller, _ = test_initialization()

        elif choice == "3":
            controller = MediaController(config_manager=None)
            test_get_active_players(controller)

        elif choice == "4":
            # Create persistent controller for pause/resume testing
            persistent_controller = MediaController(config_manager=None)
            persistent_controller.enabled = True
            test_pause_functionality(persistent_controller)
            print(f"\n→ Paused players tracked: {persistent_controller.paused_players}")
            print("→ Run option 5 next to resume these players")

        elif choice == "5":
            if persistent_controller is None:
                print(
                    "❌ No persistent controller. Run option 4 first to pause players."
                )
            else:
                print(
                    f"Using controller with paused players: {persistent_controller.paused_players}"
                )
                test_resume_functionality(persistent_controller)

        elif choice == "6":
            controller = MediaController(config_manager=None)
            controller.enabled = True
            test_pause_resume_cycle(controller)
            persistent_controller = None

        elif choice == "7":
            test_disabled_feature()

        elif choice == "8":
            test_edge_cases()

        elif choice == "9":
            if persistent_controller:
                persistent_controller.paused_players = []
                print("✓ Cleared paused players list")
            else:
                print("No persistent controller to clear")

        elif choice == "10":
            print("\nExiting...")
            break

        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()
