import os
import re
import requests
import threading
import asyncio
import aiofiles
import httpx
import ujson as json
import vdf
import base64
import zlib
import struct
import pygob
import collections
from typing import Any
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import customtkinter as ctk
from tkinter import messagebox
import time
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

APP_FONT = ("Segoe UI", 11)
TITLE_FONT = ("Segoe UI", 20, "bold")
SMALL_FONT = ("Segoe UI", 9)

COVER_SIZE = 100

lock = asyncio.Lock()
client = httpx.AsyncClient(trust_env=True, verify=False, timeout=httpx.Timeout(30.0, connect=10.0))

DEPOTDOWNLOADER = "DepotDownloadermod.exe"
DEPOTDOWNLOADER_ARGS = "-max-downloads 256 -verify-all"

REPOS = [
    'ikun0014/ManifestHub',
    'Auiowu/ManifestAutoUpdate',
    'tymolu233/ManifestAutoUpdate',
    'SteamAutoCracks/ManifestHub',
    'PrintedWaste',
    'steambox.gdata.fun',
    'cysaw.top',
    'sean-who/ManifestAutoUpdate',
    'luckygametools/steam-cfg',
    'Steam tools .lua/.st script (Local file)'
]

CONFIG_FILE = "manifest_config.json"


class APIKeyDialog(ctk.CTkToplevel):
    """Dialog for entering ManifestHub API Key"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("ManifestHub API Configuration")
        self.geometry("500x300")
        self.resizable(False, False)
        
        self.api_key = None
        
        # Center on parent
        self.transient(parent)
        self.grab_set()
        
        # Content
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(frame, text="ManifestHub API Key", font=TITLE_FONT, text_color="#2ecc71")
        title.pack(anchor="w", pady=(0, 10))
        
        info = ctk.CTkLabel(
            frame,
            text="Get your API key from:\nhttps://manifesthub1.filegear-sg.me/",
            font=SMALL_FONT,
            text_color="gray70",
            justify="left"
        )
        info.pack(anchor="w", pady=(0, 15))
        
        ctk.CTkLabel(frame, text="API Key:", font=APP_FONT).pack(anchor="w", pady=(0, 5))
        
        self.api_key_entry = ctk.CTkEntry(frame, width=400, height=40, font=APP_FONT, show="*")
        self.api_key_entry.pack(anchor="w", pady=(0, 15))
        
        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(20, 0))
        
        save_btn = ctk.CTkButton(
            button_frame,
            text="Save & Test",
            width=120,
            height=36,
            fg_color="#4CAF50",
            command=self.save_api_key
        )
        save_btn.pack(side="left", padx=(0, 10))
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=120,
            height=36,
            fg_color="#e67e22",
            command=self.cancel
        )
        cancel_btn.pack(side="left")
        
        self.result_label = ctk.CTkLabel(frame, text="", font=SMALL_FONT, text_color="gray70")
        self.result_label.pack(anchor="w", pady=(15, 0))
    
    def save_api_key(self):
        """Save and test API key"""
        key = self.api_key_entry.get().strip()
        if not key:
            messagebox.showwarning("Error", "Please enter an API key")
            return
        
        # Test the API key
        self.result_label.configure(text="Testing API key...", text_color="yellow")
        self.update()
        
        threading.Thread(target=self._test_api_key, args=(key,), daemon=True).start()
    
    def _test_api_key(self, key):
        """Test API key connection"""
        try:
            # Test with a simple request
            url = "https://api.manifesthub1.filegear-sg.me/manifest"
            params = {
                "apikey": key,
                "depotid": "1391110",  # Test depot
                "manifestid": "1"
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                self.api_key = key
                self.after(0, lambda: messagebox.showinfo("Success", "API key is valid!"))
                self.after(0, self.destroy)
            elif response.status_code == 401:
                self.after(0, lambda: self.result_label.configure(text="❌ Invalid API key", text_color="red"))
                self.after(0, lambda: messagebox.showerror("Error", "Invalid API key"))
            else:
                self.after(0, lambda: self.result_label.configure(text=f"❌ Error: {response.status_code}", text_color="red"))
                self.after(0, lambda: messagebox.showerror("Error", f"API Error: {response.status_code}"))
        except Exception as e:
            self.after(0, lambda: self.result_label.configure(text="❌ Connection failed", text_color="red"))
            self.after(0, lambda: messagebox.showerror("Error", f"Connection failed: {str(e)}"))
    
    def cancel(self):
        """Cancel dialog"""
        self.destroy()


class DepotDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Depot Downloader - Script Generator")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        self.cache_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), ".cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.selected_app_id = None
        self.selected_game_name = None
        self._image_refs = {}
        self.search_thread = None
        self.last_search_query = ""
        self.manifest_hub_api_key = None
        
        self.load_config()
        self.setup_ui()
    
    def load_config(self):
        """Load configuration"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.loads(f.read())
                    self.manifest_hub_api_key = config.get("manifest_hub_api_key")
        except:
            pass
    
    def save_config(self):
        """Save configuration"""
        try:
            config = {
                "manifest_hub_api_key": self.manifest_hub_api_key
            }
            with open(CONFIG_FILE, 'w') as f:
                f.write(json.dumps(config, indent=2))
        except:
            pass
    
    def setup_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 6))
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", anchor="w")
        
        self.title_lbl = ctk.CTkLabel(title_frame, text="Depot Downloader", font=TITLE_FONT, text_color="#2ecc71")
        self.title_lbl.pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Download Steam Game Manifests Automatically", font=APP_FONT, text_color="gray70").pack(anchor="w", pady=(2, 0))
        
        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.pack(side="right", anchor="e")
        
        self.api_btn = ctk.CTkButton(controls, text="🔑 API Key", width=120, fg_color="#9b59b6", command=self.configure_api_key)
        self.api_btn.pack(side="left", padx=6)
        
        self.clear_btn = ctk.CTkButton(controls, text="Clear Selection", width=140, fg_color="#e67e22", command=self.clear_selection)
        self.clear_btn.pack(side="left", padx=6)
        
        # Main content
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=12, pady=(6, 12))
        
        # Left sidebar - Game selection
        sidebar = ctk.CTkFrame(main, width=300, fg_color="#111")
        sidebar.pack(side="left", fill="y", padx=(0, 12), pady=4)
        sidebar.pack_propagate(False)
        
        ctk.CTkLabel(sidebar, text="Search & Select Game", font=("Segoe UI", 13, "bold")).pack(anchor="nw", pady=(10, 8), padx=10)
        
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            sidebar,
            placeholder_text="Type game name...",
            width=280,
            height=44,
            textvariable=self.search_var,
            font=APP_FONT
        )
        self.search_entry.pack(anchor="nw", padx=10, pady=(0, 8))
        self.search_entry.bind("<KeyRelease>", self.on_search_key_release)
        
        ctk.CTkLabel(sidebar, text="Search Results", font=("Segoe UI", 12, "bold")).pack(anchor="nw", pady=(8, 4), padx=10)
        
        self.results_frame = ctk.CTkScrollableFrame(sidebar, width=280, height=400, fg_color="#0f0f0f")
        self.results_frame.pack(padx=10, pady=(4, 10), fill="both", expand=True)
        
        # Status
        status_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        status_frame.pack(fill="x", padx=10, pady=(8, 10))
        
        self.status_label = ctk.CTkLabel(status_frame, text="Ready", text_color="gray", font=SMALL_FONT, wraplength=260)
        self.status_label.pack(anchor="w")
        
        # Right content - Selected game info and download
        content = ctk.CTkFrame(main)
        content.pack(side="left", fill="both", expand=True)
        
        # Selected game display
        game_group = ctk.CTkFrame(content, fg_color="#111", corner_radius=10)
        game_group.pack(fill="x", padx=10, pady=(0, 12))
        
        ctk.CTkLabel(game_group, text="Selected Game", font=("Segoe UI", 13, "bold")).pack(anchor="nw", pady=(10, 6), padx=10)
        
        game_info_frame = ctk.CTkFrame(game_group, fg_color="transparent")
        game_info_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Game cover
        self.game_cover = ctk.CTkLabel(
            game_info_frame,
            text="?",
            width=COVER_SIZE,
            height=COVER_SIZE,
            corner_radius=8,
            fg_color="#2b2b2b",
            font=("Segoe UI", int(COVER_SIZE/5), "bold")
        )
        self.game_cover.pack(side="left", padx=(0, 12), pady=6)
        
        # Game details
        details_frame = ctk.CTkFrame(game_info_frame, fg_color="transparent")
        details_frame.pack(side="left", fill="both", expand=True, pady=6)
        
        self.game_name_label = ctk.CTkLabel(
            details_frame,
            text="No game selected",
            font=("Segoe UI", 14, "bold"),
            text_color="gray70"
        )
        self.game_name_label.pack(anchor="w", pady=(0, 6))
        
        self.game_id_label = ctk.CTkLabel(
            details_frame,
            text="App ID: -",
            font=SMALL_FONT,
            text_color="gray60"
        )
        self.game_id_label.pack(anchor="w", pady=(0, 6))
        
        # API Key status
        self.api_status_label = ctk.CTkLabel(
            details_frame,
            text="ManifestHub API: Not configured",
            font=SMALL_FONT,
            text_color="orange"
        )
        self.api_status_label.pack(anchor="w", pady=(0, 0))
        
        self.update_api_status()
        
        # Download button
        self.download_btn = ctk.CTkButton(
            game_group,
            text="▶ Generate & Download Script",
            width=280,
            height=44,
            font=("Segoe UI", 12, "bold"),
            fg_color="#4CAF50",
            command=self.start_download
        )
        self.download_btn.pack(pady=(0, 10), padx=10)
        self.download_btn.configure(state="disabled")
        
        # Progress
        progress_frame = ctk.CTkFrame(content, fg_color="transparent")
        progress_frame.pack(fill="x", padx=10, pady=(0, 12))
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame, width=500)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(side="left", padx=(0, 10))
        
        self.progress_label = ctk.CTkLabel(progress_frame, text="Idle", text_color="gray", font=SMALL_FONT)
        self.progress_label.pack(side="left")
        
        # Log output
        log_group = ctk.CTkFrame(content, fg_color="#0f0f0f", corner_radius=10)
        log_group.pack(fill="both", expand=True, padx=10, pady=(0, 0))
        
        ctk.CTkLabel(log_group, text="Log Output", font=("Segoe UI", 12, "bold")).pack(anchor="nw", pady=(10, 6), padx=10)
        
        self.log_text = ctk.CTkTextbox(log_group, height=350, font=("Courier New", 9))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_text.configure(state="disabled")
        
        clear_log_btn = ctk.CTkButton(log_group, text="Clear Log", width=100, height=32, command=self.clear_log)
        clear_log_btn.pack(padx=10, pady=(0, 10))
    
    def configure_api_key(self):
        """Open API key configuration dialog"""
        dialog = APIKeyDialog(self)
        self.wait_window(dialog)
        
        if dialog.api_key:
            self.manifest_hub_api_key = dialog.api_key
            self.save_config()
            self.update_api_status()
            self.log_message("✓ ManifestHub API key configured successfully")
    
    def update_api_status(self):
        """Update API status label"""
        if self.manifest_hub_api_key:
            masked_key = self.manifest_hub_api_key[:8] + "..." if len(self.manifest_hub_api_key) > 8 else "***"
            self.api_status_label.configure(
                text=f"ManifestHub API: ✓ Configured ({masked_key})",
                text_color="#2ecc71"
            )
        else:
            self.api_status_label.configure(
                text="ManifestHub API: Not configured",
                text_color="orange"
            )
    
    def on_search_key_release(self, event):
        """Real-time search as user types"""
        query = self.search_var.get().strip()
        
        if len(query) < 2:
            self.clear_results()
            if len(query) == 0:
                self.status_label.configure(text="Start typing to search...")
            else:
                self.status_label.configure(text="Enter at least 2 characters...")
            return
        
        # Avoid duplicate searches
        if query == self.last_search_query:
            return
        
        self.last_search_query = query
        
        # Search in thread
        if self.search_thread and self.search_thread.is_alive():
            return
        
        self.status_label.configure(text=f"Searching: {query}", text_color="yellow")
        self.search_thread = threading.Thread(target=self.search_games, args=(query,), daemon=True)
        self.search_thread.start()
    
    def search_games(self, query):
        """Search Steam Community for games"""
        try:
            url = f"https://steamcommunity.com/actions/SearchApps/{query}"
            response = requests.get(url, timeout=10)
            games = response.json()
            
            if games:
                self.after(0, self.display_results, games[:10])
                self.after(0, lambda: self.status_label.configure(text=f"Found {len(games[:10])} results", text_color="#2ecc71"))
            else:
                self.after(0, self.clear_results)
                self.after(0, lambda: self.status_label.configure(text="No results found", text_color="gray70"))
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text="Search error", text_color="red"))
    
    def display_results(self, games):
        """Display search results"""
        self.clear_results()
        
        for game in games:
            try:
                app_id = game.get('appid')
                name = game.get('name', 'Unknown')
                icon = game.get('icon', '')
                
                # Result item
                result_frame = ctk.CTkFrame(self.results_frame, corner_radius=8, fg_color="#151515")
                result_frame.pack(fill="x", padx=6, pady=6)
                
                # Icon container
                icon_container = ctk.CTkFrame(result_frame, width=60, height=60, fg_color="transparent")
                icon_container.pack(side="left", padx=8, pady=8)
                icon_container.pack_propagate(False)
                
                initial = (name[0] if name else "?").upper()
                icon_label = ctk.CTkLabel(
                    icon_container,
                    text=initial,
                    width=60,
                    height=60,
                    corner_radius=6,
                    fg_color="#2b2b2b",
                    font=("Segoe UI", 14, "bold")
                )
                icon_label.pack(expand=True)
                
                # Load icon in thread
                if icon:
                    threading.Thread(
                        target=self._load_steam_icon,
                        args=(app_id, icon, icon_label),
                        daemon=True
                    ).start()
                
                # Info
                info_frame = ctk.CTkFrame(result_frame, fg_color="transparent")
                info_frame.pack(side="left", fill="both", expand=True, padx=6, pady=8)
                
                name_label = ctk.CTkLabel(info_frame, text=name, anchor="w", font=("Segoe UI", 10, "bold"))
                name_label.pack(fill="x")
                
                id_label = ctk.CTkLabel(info_frame, text=f"ID: {app_id}", anchor="w", font=SMALL_FONT, text_color="gray70")
                id_label.pack(fill="x", pady=(2, 0))
                
                # Select button
                select_btn = ctk.CTkButton(
                    result_frame,
                    text="Select",
                    width=80,
                    height=36,
                    fg_color="#2196F3",
                    command=lambda aid=app_id, nm=name: self.select_game(aid, nm)
                )
                select_btn.pack(side="right", padx=8, pady=8)
            
            except Exception as e:
                continue
    
    def _load_steam_icon(self, appid, icon_code, label):
        """Load game icon from Steam"""
        try:
            cache_path = os.path.join(self.cache_dir, f"{appid}_icon.jpg")
            
            if not os.path.exists(cache_path):
                url = f"https://media.steampowered.com/steamcommunity/public/images/apps/{appid}/{icon_code}.jpg"
                try:
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        with open(cache_path, "wb") as f:
                            f.write(resp.content)
                except:
                    pass
            
            if os.path.exists(cache_path):
                try:
                    from PIL import Image, ImageOps
                    img = Image.open(cache_path).convert("RGBA")
                    img.thumbnail((60, 60), Image.LANCZOS)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(60, 60))
                    self.after(0, lambda: label.configure(image=ctk_img, text=""))
                except:
                    pass
        except:
            pass
    
    def clear_results(self):
        """Clear search results"""
        for w in self.results_frame.winfo_children():
            w.destroy()
    
    def select_game(self, app_id, name):
        """Select a game"""
        self.selected_app_id = app_id
        self.selected_game_name = name
        
        self.game_name_label.configure(text=name, text_color="white")
        self.game_id_label.configure(text=f"App ID: {app_id}")
        self.download_btn.configure(state="normal")
        
        # Load game cover
        threading.Thread(target=self._load_game_cover, args=(app_id,), daemon=True).start()
        
        self.log_message(f"Selected: {name} (ID: {app_id})")
    
    def _load_game_cover(self, appid):
        """Load and display game cover"""
        try:
            cache_path = os.path.join(self.cache_dir, f"{appid}_cover.jpg")
            
            if not os.path.exists(cache_path):
                url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l=english"
                try:
                    resp = requests.get(url, timeout=6)
                    data = resp.json() if resp.ok else None
                    
                    if data and str(appid) in data:
                        appdata = data.get(str(appid), {})
                        if appdata.get("success"):
                            header = appdata.get("data", {}).get("header_image")
                            if header:
                                img_resp = requests.get(header, timeout=8)
                                if img_resp.status_code == 200:
                                    with open(cache_path, "wb") as f:
                                        f.write(img_resp.content)
                except:
                    pass
            
            if os.path.exists(cache_path):
                try:
                    from PIL import Image, ImageOps
                    img = Image.open(cache_path).convert("RGBA")
                    img = ImageOps.contain(img, (COVER_SIZE, COVER_SIZE), Image.LANCZOS)
                    
                    bg = Image.new("RGBA", (COVER_SIZE, COVER_SIZE), (0, 0, 0, 0))
                    x = (COVER_SIZE - img.width) // 2
                    y = (COVER_SIZE - img.height) // 2
                    bg.paste(img, (x, y), img)
                    
                    ctk_img = ctk.CTkImage(light_image=bg, dark_image=bg, size=(COVER_SIZE, COVER_SIZE))
                    self.after(0, lambda: self.game_cover.configure(image=ctk_img, text=""))
                except:
                    pass
        except:
            pass
    
    def clear_selection(self):
        """Clear selected game"""
        self.selected_app_id = None
        self.selected_game_name = None
        self.search_var.set("")
        self.last_search_query = ""
        
        self.game_name_label.configure(text="No game selected", text_color="gray70")
        self.game_id_label.configure(text="App ID: -")
        self.game_cover.configure(image=None, text="?")
        self.download_btn.configure(state="disabled")
        self.clear_results()
        
        self.log_message("Selection cleared")
    
    def start_download(self):
        """Start download process"""
        if not self.selected_app_id:
            messagebox.showwarning("Error", "Please select a game first")
            return
        
        self.download_btn.configure(state="disabled")
        self.progress_bar.set(0.0)
        self.progress_label.configure(text="Starting...", text_color="yellow")
        
        self.log_message(f"\n{'='*60}")
        self.log_message(f"Starting download for: {self.selected_game_name}")
        self.log_message(f"App ID: {self.selected_app_id}")
        self.log_message(f"Repositories: All available (auto)")
        if self.manifest_hub_api_key:
            self.log_message(f"ManifestHub API: Enabled")
        self.log_message(f"{'='*60}\n")
        
        threading.Thread(
            target=self._download_thread,
            args=(self.selected_app_id, self.selected_game_name),
            daemon=True
        ).start()
    
    def _download_thread(self, app_id, game_name):
        """Run download in thread"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(main(
                app_id,
                REPOS,
                self.log_message,
                self.manifest_hub_api_key
            ))
            loop.close()
            
            if result:
                self.after(0, lambda: messagebox.showinfo("Success", f"Script generated for {game_name}"))
                self.after(0, lambda: self.progress_label.configure(text="✓ Complete", text_color="#2ecc71"))
            else:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to download manifest for {app_id}"))
                self.after(0, lambda: self.progress_label.configure(text="✗ Failed", text_color="red"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.after(0, lambda: self.progress_label.configure(text="✗ Error", text_color="red"))
        finally:
            self.after(0, lambda: self.download_btn.configure(state="normal"))
            self.after(0, lambda: self.progress_bar.set(0.0))
    
    def log_message(self, message):
        """Add message to log"""
        self.log_text.configure(state="normal")
        timestamp = time.strftime('%H:%M:%S')
        
        if message.startswith('='):
            log_line = f"{message}\n"
        else:
            log_line = f"[{timestamp}] {message}\n"
        
        self.log_text.insert("end", log_line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
    
    def clear_log(self):
        """Clear log output"""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


# Async functions
async def check_cn() -> bool:
    try:
        req = await client.get('https://mips.kugou.com/check/iscn?&format=json')
        body = req.json()
        scn = bool(body['flag'])
        os.environ['IS_CN'] = 'yes' if scn else 'no'
        return scn
    except:
        os.environ['IS_CN'] = 'yes'
        return True


async def get(sha: str, path: str, repo: str, log_func=None):
    """Download file from repository"""
    if os.environ.get('IS_CN') == 'yes':
        url_list = [
            f'https://jsdelivr.pai233.top/gh/{repo}@{sha}/{path}',
            f'https://cdn.jsdmirror.com/gh/{repo}@{sha}/{path}',
            f'https://raw.gitmirror.com/{repo}/{sha}/{path}',
            f'https://raw.dgithub.xyz/{repo}/{sha}/{path}',
        ]
    else:
        url_list = [f'https://raw.githubusercontent.com/{repo}/{sha}/{path}']
    
    retry = 3
    while retry > 0:
        for url in url_list:
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    return r.read()
            except:
                pass
        retry -= 1
        if log_func and retry > 0:
            log_func(f'Retrying... ({retry} attempts left)')
    
    raise Exception(f'Could not download: {path}')


async def get_manifest(app_id: str, sha: str, path: str, repo: str, log_func=None):
    """Download manifest files"""
    collected_depots = []
    manifest_dir = Path(os.getcwd()) / f"{app_id}_Manifests"
    os.makedirs(manifest_dir, exist_ok=True)
    
    try:
        if path.endswith('.manifest'):
            save_path = manifest_dir / path
            if save_path.exists():
                return collected_depots
            content = await get(sha, path, repo, log_func)
            if log_func:
                log_func(f'Downloaded: {path}')
            async with aiofiles.open(save_path, 'wb') as f:
                await f.write(content)
        elif path.lower() == 'key.vdf':
            content = await get(sha, path, repo, log_func)
            depots_config = vdf.loads(content.decode('utf-8'))
            if depots_config:
                async with aiofiles.open(manifest_dir / f"{app_id}.key", 'w', encoding="utf-8") as f:
                    for depot_id, depot_info in depots_config['depots'].items():
                        await f.write(f'{depot_id};{depot_info["DecryptionKey"]}\n')
    except Exception as e:
        if log_func:
            log_func(f'Error: {path}')
        raise
    return collected_depots


async def get_data(app_id: str, path: str, repo: str, log_func=None):
    """Get data from encrypted manifest"""
    AppInfo = collections.namedtuple('AppInfo', ['Appid', 'Licenses', 'App', 'Depots', 'EncryptedAppTicket', 'AppOwnershipTicket'])
    collected_depots = []
    manifest_dir = Path(os.getcwd()) / f"{app_id}_Manifests"
    os.makedirs(manifest_dir, exist_ok=True)
    
    try:
        content = await get('main', path, repo, log_func)
        content_dec = await symmetric_decrypt(b" s  t  e  a  m  ", content)
        content_dec = await xor_decrypt(b"hail", content_dec)
        content_gob = pygob.load_all(bytes(content_dec))
        app_info = AppInfo._make(*content_gob)
        
        async with aiofiles.open(manifest_dir / f"{app_id}.key", 'w', encoding="utf-8") as keyfile:
            for depot in app_info.Depots:
                filename = f"{depot.Id}_{depot.Manifests.Id}.manifest"
                save_path = manifest_dir / filename
                if not save_path.exists():
                    async with aiofiles.open(save_path, 'wb') as f:
                        await f.write(depot.Manifests.Data)
                await keyfile.write(f'{depot.Id};{depot.Decryptkey.hex()}\n')
                collected_depots.append(filename)
    except Exception as e:
        raise
    return collected_depots


async def get_data_local(app_id: str, log_func=None):
    """Parse local lua/st files"""
    collected_depots = []
    depot_cache_path = Path(os.getcwd())
    manifest_dir = Path(os.getcwd()) / f"{app_id}_Manifests"
    os.makedirs(manifest_dir, exist_ok=True)
    
    try:
        lua_file_path = depot_cache_path / f"{app_id}.lua"
        st_file_path = depot_cache_path / f"{app_id}.st"
        
        if not lua_file_path.exists() and not st_file_path.exists():
            raise FileNotFoundError
        
        content = ""
        if lua_file_path.exists():
            async with aiofiles.open(lua_file_path, 'r', encoding="utf-8") as f:
                content = await f.read()
        
        if st_file_path.exists():
            async with aiofiles.open(st_file_path, 'rb') as f:
                content = await f.read()
            header = content[:12]
            xorkey, size, _ = struct.unpack('III', header)
            xorkey ^= 0xFFFEA4C8
            xorkey &= 0xFF
            data = bytearray(content[12:12+size])
            for i in range(len(data)):
                data[i] = data[i] ^ xorkey
            decompressed_data = zlib.decompress(data)
            content = decompressed_data[512:].decode('utf-8')
        
        async with aiofiles.open(manifest_dir / f"{app_id}.key", 'w', encoding="utf-8") as keyfile:
            addappid_pattern = re.compile(r'addappid\(\s*(\d+)\s*(?:,\s*\d+\s*,\s*"([0-9a-f]+)"\s*)?\)')
            setmanifestid_pattern = re.compile(r'setManifestid\(\s*(\d+)\s*,\s*"(\d+)"\s*(?:,\s*\d+\s*)?\)')
            
            for match in addappid_pattern.finditer(content):
                depot_id = match.group(1)
                decrypt_key = match.group(2)
                if decrypt_key:
                    await keyfile.write(f'{depot_id};{decrypt_key}\n')
            
            for match in setmanifestid_pattern.finditer(content):
                depot_id = match.group(1)
                manifest_id = match.group(2)
                filename = f"{depot_id}_{manifest_id}.manifest"
                if (manifest_dir / filename).exists():
                    collected_depots.append(filename)
    except:
        raise
    return collected_depots


async def depotdownloadermod_add(app_id: str, manifests: list, log_func=None):
    """Generate formatted batch script with proper headers and colors"""
    try:
        # Count total depots
        total_depots = len(manifests)
        manifest_dir = f"{app_id}_Manifests"
        
        async with aiofiles.open(f'{app_id}.bat', mode="w", encoding="utf-8") as bat_file:
            # Header
            await bat_file.write("@echo off\n")
            await bat_file.write("chcp 65001 > nul\n")
            await bat_file.write("color 0F\n")
            await bat_file.write(f"title Depot Downloader - App {app_id}\n")
            await bat_file.write("cls\n\n")
            
            # Initial info
            await bat_file.write("echo " + "-" * 78 + "\n")
            await bat_file.write("echo                           DOWNLOADING GAME MANIFESTS\n")
            await bat_file.write("echo " + "-" * 78 + "\n")
            await bat_file.write("echo.\n\n")
            
            # Initialize counter
            await bat_file.write("setlocal enabledelayedexpansion\n")
            await bat_file.write(f"set total_depots={total_depots}\n")
            await bat_file.write("set current_depot=0\n")
            await bat_file.write("cls\n\n")
            
            # Download commands
            await bat_file.write("echo " + "-" * 78 + "\n")
            await bat_file.write("echo                           DOWNLOADING BASE GAME\n")
            await bat_file.write("echo " + "-" * 78 + "\n")
            await bat_file.write("echo.\n\n")
            
            for i, manifest in enumerate(manifests, 1):
                depot_id = manifest[0:manifest.find('_')]
                manifest_id = manifest[manifest.find('_') + 1:manifest.find('.')]
                
                await bat_file.write(f"set /a current_depot+=1\n")
                await bat_file.write(f"echo [!current_depot!/!total_depots!] Downloading depot {depot_id}...\n")
                await bat_file.write(f".\\DepotDownloaderMod\\DepotDownloadermod.exe -app {app_id} -depot {depot_id} -manifest {manifest_id} -manifestfile \"{manifest_dir}\\{manifest}\" -depotkeys \"{manifest_dir}\\{app_id}.key\" -dir \"game_{app_id}\" {DEPOTDOWNLOADER_ARGS}\n")
                await bat_file.write("if errorlevel 1 (\n")
                await bat_file.write(f"    echo ERROR: Failed to download depot {depot_id}\n")
                await bat_file.write("    pause\n")
                await bat_file.write("    exit /b 1\n")
                await bat_file.write(")\n")
                await bat_file.write("echo =============================== COMPLETE ==================================\n")
                await bat_file.write("echo.\n\n")
            
            # Completion message
            await bat_file.write("echo " + "=" * 78 + "\n")
            await bat_file.write("echo                           DOWNLOAD COMPLETED!\n")
            await bat_file.write("echo " + "=" * 78 + "\n")
            await bat_file.write("echo.\n")
            await bat_file.write(f"echo All files downloaded to: \"game_{app_id}\" folder\n")
            await bat_file.write("echo Total depots processed: !total_depots!\n")
            await bat_file.write("echo.\n")
            await bat_file.write("echo " + "-" * 78 + "\n")
            await bat_file.write("echo.\n")
            await bat_file.write("pause\n")
            await bat_file.write("endlocal\n")
        
        if log_func:
            log_func(f'✓ Batch script generated: {app_id}.bat')
            log_func(f'✓ Manifest files stored in: {manifest_dir}')
        return True
    except Exception as e:
        if log_func:
            log_func(f'Error generating batch script: {str(e)}')
        return False


async def fetch_info(url):
    """Fetch JSON"""
    try:
        r = await client.get(url)
        return r.json()
    except:
        return None


async def symmetric_decrypt(key, ciphertext):
    """Decrypt AES"""
    try:
        iv = ciphertext[:AES.block_size]
        data = ciphertext[AES.block_size:]
        cipher_ecb = AES.new(key, AES.MODE_ECB)
        iv = cipher_ecb.decrypt(iv)
        cipher_cbc = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher_cbc.decrypt(data)
        return unpad(decrypted, AES.block_size)
    except:
        return None


async def xor_decrypt(key, ciphertext):
    """XOR decrypt"""
    try:
        decrypted = bytearray(len(ciphertext))
        for i in range(len(ciphertext)):
            decrypted[i] = ciphertext[i] ^ key[i % len(key)]
        return bytes(decrypted)
    except:
        return None


async def manifesthub_download(app_id: str, api_key: str, log_func=None):
    """Download from ManifestHub API"""
    try:
        if log_func:
            log_func("Trying ManifestHub API...")
        
        manifest_dir = Path(os.getcwd()) / f"{app_id}_Manifests"
        os.makedirs(manifest_dir, exist_ok=True)
        
        # Get depot list from GitHub or another source
        url = f"https://api.github.com/repos/ikun0014/ManifestHub/branches/{app_id}"
        r_json = await fetch_info(url)
        
        if not r_json or 'commit' not in r_json:
            if log_func:
                log_func("App ID not found in ManifestHub")
            return False
        
        sha = r_json['commit']['sha']
        tree_url = r_json['commit']['commit']['tree']['url']
        r2_json = await fetch_info(tree_url)
        
        if not r2_json or 'tree' not in r2_json:
            return False
        
        # Extract depot and manifest IDs from file names
        async with aiofiles.open(manifest_dir / f"{app_id}.key", 'w', encoding="utf-8") as keyfile:
            for item in r2_json['tree']:
                path = item['path']
                if path.endswith('.manifest'):
                    # Parse depot_id_manifest_id.manifest
                    match = re.match(r'(\d+)_(\d+)\.manifest', path)
                    if match:
                        depot_id = match.group(1)
                        manifest_id = match.group(2)
                        
                        # Download from ManifestHub API
                        api_url = "https://api.manifesthub1.filegear-sg.me/manifest"
                        params = {
                            "apikey": api_key,
                            "depotid": depot_id,
                            "manifestid": manifest_id
                        }
                        
                        try:
                            r = await client.get(api_url, params=params)
                            if r.status_code == 200:
                                manifest_path = manifest_dir / path
                                async with aiofiles.open(manifest_path, 'wb') as f:
                                    await f.write(r.content)
                                
                                if log_func:
                                    log_func(f"Downloaded manifest: {path}")
                                
                                await keyfile.write(f'{depot_id};{manifest_id}\n')
                        except Exception as e:
                            if log_func:
                                log_func(f"Error downloading {path}: {str(e)}")
        
        return True
    except Exception as e:
        if log_func:
            log_func(f"ManifestHub error: {str(e)}")
        return False


async def printedwaste_download(app_id: str, log_func=None):
    """Download from PrintedWaste"""
    try:
        manifest_dir = Path(os.getcwd()) / f"{app_id}_Manifests"
        os.makedirs(manifest_dir, exist_ok=True)
        
        url = f"https://api.printedwaste.com/gfk/download/{app_id}"
        r = await client.get(url, headers={"Authorization": "Bearer dGhpc19pcyBhX3JhbmRvbV90b2tlbg=="})
        r.raise_for_status()
        content = await r.aread()
        
        import io, zipfile
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for file in zf.namelist():
                if file.endswith(('.st', '.lua', '.manifest', '.key')):
                    async with aiofiles.open(manifest_dir / Path(file).name, 'wb') as f:
                        await f.write(zf.read(file))
        return True
    except:
        return False


async def gdata_download(app_id: str, log_func=None):
    """Download from gdata"""
    try:
        manifest_dir = Path(os.getcwd()) / f"{app_id}_Manifests"
        os.makedirs(manifest_dir, exist_ok=True)
        
        url = f"https://steambox.gdata.fun/cnhz/qingdan/{app_id}.zip"
        r = await client.get(url)
        r.raise_for_status()
        content = await r.aread()
        
        import io, zipfile
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for file in zf.namelist():
                if file.endswith(('.st', '.lua', '.manifest', '.key')):
                    async with aiofiles.open(manifest_dir / Path(file).name, 'wb') as f:
                        await f.write(zf.read(file))
        return True
    except:
        return False


async def cysaw_download(app_id: str, log_func=None):
    """Download from cysaw"""
    try:
        manifest_dir = Path(os.getcwd()) / f"{app_id}_Manifests"
        os.makedirs(manifest_dir, exist_ok=True)
        
        url = f"https://cysaw.top/uploads/{app_id}.zip"
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        content = await r.aread()
        
        import io, zipfile
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for file in zf.namelist():
                if file.endswith(('.st', '.lua', '.manifest', '.key')):
                    async with aiofiles.open(manifest_dir / Path(file).name, 'wb') as f:
                        await f.write(zf.read(file))
        return True
    except:
        return False


async def main(app_id: str, repos: list, log_func=None, api_key=None):
    """Main async function"""
    def log_msg(msg):
        if log_func:
            log_func(msg)
    
    app_id = str(app_id).strip()
    if not app_id.isdigit():
        log_msg('Invalid App ID')
        return False
    
    await check_cn()
    
    # Try ManifestHub API first if configured
    if api_key:
        try:
            if await manifesthub_download(app_id, api_key, log_msg):
                manifests = await get_data_local(app_id, log_msg)
                if manifests:
                    await depotdownloadermod_add(app_id, manifests, log_msg)
                    return True
        except:
            pass
    
    for selected_repo in repos:
        try:
            log_msg(f'Trying: {selected_repo}')
            
            if selected_repo == 'Steam tools .lua/.st script (Local file)':
                manifests = await get_data_local(app_id, log_msg)
                if manifests:
                    await depotdownloadermod_add(app_id, manifests, log_msg)
                    return True
            elif selected_repo == 'PrintedWaste':
                if await printedwaste_download(app_id, log_msg):
                    manifests = await get_data_local(app_id, log_msg)
                    if manifests:
                        await depotdownloadermod_add(app_id, manifests, log_msg)
                        return True
            elif selected_repo == 'steambox.gdata.fun':
                if await gdata_download(app_id, log_msg):
                    manifests = await get_data_local(app_id, log_msg)
                    if manifests:
                        await depotdownloadermod_add(app_id, manifests, log_msg)
                        return True
            elif selected_repo == 'cysaw.top':
                if await cysaw_download(app_id, log_msg):
                    manifests = await get_data_local(app_id, log_msg)
                    if manifests:
                        await depotdownloadermod_add(app_id, manifests, log_msg)
                        return True
            elif selected_repo == 'luckygametools/steam-cfg':
                url = f'https://api.github.com/repos/{selected_repo}/contents/steamdb2/{app_id}'
                r_json = await fetch_info(url)
                if r_json and isinstance(r_json, list):
                    try:
                        path = [item['path'] for item in r_json if item['name'] == '00000encrypt.dat'][0]
                        manifests = await get_data(app_id, path, selected_repo, log_msg)
                        if manifests:
                            await depotdownloadermod_add(app_id, manifests, log_msg)
                            return True
                    except:
                        continue
            else:
                url = f'https://api.github.com/repos/{selected_repo}/branches/{app_id}'
                r_json = await fetch_info(url)
                if r_json and 'commit' in r_json:
                    sha = r_json['commit']['sha']
                    tree_url = r_json['commit']['commit']['tree']['url']
                    r2_json = await fetch_info(tree_url)
                    if r2_json and 'tree' in r2_json:
                        manifests = [item['path'] for item in r2_json['tree'] if item['path'].endswith('.manifest')]
                        if manifests:
                            for item in r2_json['tree']:
                                await get_manifest(app_id, sha, item['path'], selected_repo, log_msg)
                            await depotdownloadermod_add(app_id, manifests, log_msg)
                            return True
        except Exception as e:
            continue
    
    log_msg('Failed: No sources found the app ID')
    return False


if __name__ == "__main__":
    app = DepotDownloaderApp()
    app.mainloop()