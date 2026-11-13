import logging
import subprocess
import json
import socket
import os
class MPVPlayerController:

    def __init__(self):
        self.process =None
        self.socket_path = "/tmp/mpv-socket"
    def start_player(self,stream_stdout):
        try:
            self.process = subprocess.Popen(
                [
                    "mpv",
                    "--no-video",       
                    "--really-quiet",      
                    f"--input-ipc-server={self.socket_path}",
                    "-",                   
                ],
                stdin=stream_stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            logging.error(f"Failed to start MPV: {e}")
            self.process = None

    def is_running(self):
        if self.process is None:
            return False
        
        return self.process.poll() is None
    
    def clean_up(self):
        self.process = None
    
    def pause_song(self):
        self._send_mpv_command({"command": ["set_property", "pause", True]})
    
    def start_song(self):
        self._send_mpv_command({"command": ["set_property", "pause", False]})
    
    def set_volume(self, level: int):
        level = max(0, min(100, level))
        self._send_command({"command": ["set_property", "volume", level]})
    
    def _send_mpv_command(self,command_dict):
        if os.path.exists(self.socket_path):
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(self.socket_path)
            client.sendall((json.dumps(command_dict) + "\n").encode("utf-8"))
            client.close()

    

