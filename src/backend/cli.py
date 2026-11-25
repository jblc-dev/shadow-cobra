"""Interactive command-line player for testing streaming.

Run with:
    .venv/bin/python -m cobra.cli

Type a track name and press Enter to add it to the queue. Bare commands:

    play            play the next queued track
    pause           pause playback
    resume          resume playback
    skip            skip to the next queued track
    stop            stop playback
    volume <0-100>  set the volume
    status          show what is playing and how many tracks are queued
    help            show this help
    quit            exit
"""

from cobra import MusicPlayer


HELP = """
Type a track name and press Enter to add it to the queue.

  play            play the next queued track
  pause           pause playback
  resume          resume playback
  skip            skip to the next queued track
  stop            stop playback
  volume <0-100>  set the volume
  status          show playback state and queue length
  help            show this help
  quit            exit
""".strip()

NO_ARG_COMMANDS = {
    "play",
    "pause",
    "resume",
    "skip",
    "stop",
    "status",
    "queue",
    "help",
    "quit",
    "exit",
}


def main():
    player = MusicPlayer()
    print("Interactive player. Type a track name, or 'help' for commands.")

    try:
        while True:
            try:
                line = input("cobra> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue

            head, separator, rest = line.partition(" ")
            command = head.lower()

            if not separator and command in NO_ARG_COMMANDS:
                if command in ("quit", "exit"):
                    break
                if command == "help":
                    print(HELP)
                elif command == "play":
                    manager = player.worker_manager
                    if player.mpv.is_running():
                        print("already playing (use 'skip' to advance)")
                    elif (
                        player.queue.qsize()
                        or manager.active.is_running()
                        or manager.standby.is_running()
                    ):
                        manager.start()
                        if player.play():
                            print("playing")
                        else:
                            print("could not start playback")
                    else:
                        print("nothing queued")
                elif command == "pause":
                    if player.mpv.is_running():
                        player.pause()
                        print("paused")
                    else:
                        print("nothing playing")
                elif command == "resume":
                    if player.mpv.is_running():
                        player.resume()
                        print("resumed")
                    else:
                        print("nothing playing")
                elif command == "skip":
                    player.skip()
                    print("skipped")
                elif command == "stop":
                    player.stop()
                    print("stopped")
                elif command in ("status", "queue"):
                    state = "playing" if player.mpv.is_running() else "stopped"
                    print(f"mpv: {state}, queued: {player.queue.qsize()}")
            elif command in ("volume", "vol") and separator:
                try:
                    level = int(rest)
                except ValueError:
                    print("usage: volume <0-100>")
                    continue
                if player.mpv.is_running():
                    player.set_volume(level)
                    print(f"volume set to {max(0, min(100, level))}")
                else:
                    print("nothing playing")
            else:
                player.add_track(line)
                print(f"queued: {line}")
    finally:
        player.stop()


if __name__ == "__main__":
    main()
