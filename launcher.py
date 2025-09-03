#!/usr/bin/env python3
"""
Ollama Controller with System Tray
Control Ollama and Open-WebUI with system icon and startup waiting
"""

import tkinter as tk
from tkinter import messagebox
import tkinter.ttk as ttk
import subprocess
import threading
import webbrowser
import time
import requests
import sys
import os

# Try to import system tray
try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import Gtk, AyatanaAppIndicator3, GObject
    SYSTRAY_AVAILABLE = True
except ImportError:
    SYSTRAY_AVAILABLE = False
    print("System tray not available - Window mode only")

class OllamaController:
    def __init__(self):
        self.root = None
        self.indicator = None
        self.window_visible = False
        
        # Variables for tkinter
        self.status_var = None
        self.progress_var = None
        self.start_btn = None
        self.stop_btn = None
        self.open_btn = None
        self.progress = None
        
        if SYSTRAY_AVAILABLE:
            self.setup_systray()
            # Create window but hide it
            self.setup_window(show=False)
        else:
            # Classic window mode
            self.setup_window(show=True)
        
    def create_custom_icon(self):
        """Use a simple system icon"""
        # Use a standard system icon that should be available
        self.icon_path = "applications-internet"

    def setup_systray(self):
        """Setup system tray icon"""
        self.create_custom_icon()
        
        # Create system indicator
        self.indicator = AyatanaAppIndicator3.Indicator.new(
            "ollama-controller",
            self.icon_path,
            AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_systray_menu())
        
    def build_systray_menu(self):
        """Build system tray menu"""
        menu = Gtk.Menu()
        
        # Show/Hide window (main action)
        self.window_item = Gtk.MenuItem(label="📱 Show Window")
        self.window_item.connect('activate', self.toggle_window)
        menu.append(self.window_item)
        
        # Quick actions
        menu.append(Gtk.SeparatorMenuItem())
        
        start_item = Gtk.MenuItem(label="🚀 Start Services")
        start_item.connect('activate', lambda w: self.systray_start_services())
        menu.append(start_item)
        
        stop_item = Gtk.MenuItem(label="⏹️ Stop Services")
        stop_item.connect('activate', lambda w: self.systray_stop_services())
        menu.append(stop_item)
        
        open_item = Gtk.MenuItem(label="🌐 Open WebUI")
        open_item.connect('activate', lambda w: webbrowser.open('http://localhost:8080'))
        menu.append(open_item)
        
        # Quit
        menu.append(Gtk.SeparatorMenuItem())
        
        quit_item = Gtk.MenuItem(label="❌ Quit")
        quit_item.connect('activate', self.quit_app)
        menu.append(quit_item)
        
        menu.show_all()
        return menu
        
    def setup_window(self, show=True):
        """Setup tkinter window"""
        self.root = tk.Tk()
        self.root.title("🤖 OpenUI Controller")
        self.root.geometry("400x260")
        self.root.resizable(True, True)
        
        # Variables
        self.status_var = tk.StringVar(value="Services stopped")
        self.progress_var = tk.DoubleVar()
        
        self.setup_ui()
        
        if SYSTRAY_AVAILABLE:
            # Hide window at start if system tray available
            if not show:
                self.root.withdraw()
                self.window_visible = False
            else:
                self.window_visible = True
                
            # Handle closing (minimize to tray instead of quit)
            self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        else:
            # Classic mode - really quit on close
            self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
            self.window_visible = True
        
        # Check initial status
        self.check_status()
        
    def setup_ui(self):
        """Setup user interface"""
        # Main frame with more padding
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, font=("Arial", 9))
        self.status_label.pack()
        
        # Progress bar
        self.progress = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress.pack(fill=tk.X, pady=(10, 0))
        self.progress.pack_forget()  # Hide at start
        
        # Main buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 12))
        
        self.start_btn = ttk.Button(
            button_frame, 
            text="🚀 Start Ollama + WebUI", 
            command=self.start_services,
            width=32
        )
        self.start_btn.pack(pady=4)
        
        self.stop_btn = ttk.Button(
            button_frame, 
            text="⏹️ Stop All", 
            command=self.stop_services,
            width=32
        )
        self.stop_btn.pack(pady=4)
        
        self.open_btn = ttk.Button(
            button_frame, 
            text="🌐 Open WebUI", 
            command=self.open_webui,
            width=32
        )
        self.open_btn.pack(pady=4)
        
        # Visual separator
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=(8, 8))
    
    def toggle_window(self, widget=None):
        """Show/hide window"""
        if self.window_visible:
            self.hide_window()
        else:
            self.show_window()
    
    def show_window(self):
        """Show window"""
        if self.root:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.window_visible = True
            if SYSTRAY_AVAILABLE:
                self.window_item.set_label("🔽 Hide Window")
    
    def hide_window(self):
        """Hide window to system tray"""
        if SYSTRAY_AVAILABLE and self.root:
            self.root.withdraw()
            self.window_visible = False
            self.window_item.set_label("📱 Show Window")
        else:
            # If no system tray, really quit
            self.quit_app()
    
    def systray_start_services(self):
        """Start services from system tray"""
        if not self.window_visible:
            self.show_window()
        self.start_services()
    
    def systray_stop_services(self):
        """Stop services from system tray"""
        # Can be done without showing window
        def run():
            try:
                subprocess.run(['pkill', 'ollama'], stderr=subprocess.DEVNULL)
                subprocess.run(['pkill', '-f', 'open-webui'], stderr=subprocess.DEVNULL)
                print("Services stopped from system tray")
            except Exception as e:
                print(f"Stop error: {e}")
        
        threading.Thread(target=run, daemon=True).start()
    
    def check_status(self):
        """Check services status"""
        def check():
            if not self.status_var:
                return
                
            ollama_running = subprocess.run(['pgrep', 'ollama'], capture_output=True).returncode == 0
            webui_running = subprocess.run(['pgrep', '-f', 'open-webui'], capture_output=True).returncode == 0
            
            if ollama_running and webui_running:
                status = "✅ Services active"
            elif ollama_running:
                status = "🟡 Ollama only active"
            elif webui_running:
                status = "🟠 WebUI only active"
            else:
                status = "● Services stopped"
            
            try:
                self.status_var.set(status)
                self.enable_buttons()
            except:
                pass  # Window closed
        
        threading.Thread(target=check, daemon=True).start()
    
    def wait_for_ollama(self):
        """Wait for Ollama to be ready"""
        max_attempts = 30
        for i in range(max_attempts):
            try:
                response = requests.get('http://localhost:11434/api/tags', timeout=2)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(1)
        return False
    
    def wait_for_webui(self):
        """Wait for WebUI to be ready"""
        max_attempts = 30
        for i in range(max_attempts):
            try:
                response = requests.get('http://localhost:8080', timeout=2)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(1)
        return False
    
    def update_progress(self, value, text):
        """Update progress"""
        try:
            self.progress_var.set(value)
            self.status_var.set(text)
            self.root.update()
        except:
            pass
    
    def show_progress(self, show=True):
        """Show/hide progress bar"""
        try:
            if show:
                self.progress.pack(fill=tk.X, pady=(10, 0))
            else:
                self.progress.pack_forget()
            self.root.update()
        except:
            pass
    
    def disable_buttons(self):
        """Disable buttons"""
        try:
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='disabled')
            self.open_btn.config(state='disabled')
        except:
            pass
    
    def enable_buttons(self):
        """Enable buttons"""
        try:
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='normal')
            self.open_btn.config(state='normal')
        except:
            pass
    
    def start_services(self):
        """Start all services with waiting"""
        def run():
            try:
                self.disable_buttons()
                self.show_progress(True)
                
                self.update_progress(10, "🔄 Starting Ollama...")
                
                if subprocess.run(['pgrep', 'ollama'], capture_output=True).returncode != 0:
                    subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                self.update_progress(30, "⏳ Waiting for Ollama...")
                
                if not self.wait_for_ollama():
                    raise Exception("Ollama could not start")
                
                self.update_progress(50, "🔄 Starting WebUI...")
                
                if subprocess.run(['pgrep', '-f', 'open-webui'], capture_output=True).returncode != 0:
                    subprocess.Popen(['open-webui', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                self.update_progress(70, "⏳ Waiting for WebUI...")
                
                if not self.wait_for_webui():
                    raise Exception("WebUI could not start")
                
                self.update_progress(100, "✅ Services ready!")
                time.sleep(1)
                
                webbrowser.open('http://localhost:8080')
                
                self.status_var.set("✅ Services active")
                # No messagebox - just visual confirmation
                
            except Exception as e:
                self.status_var.set("❌ Start error")
                if self.window_visible:
                    messagebox.showerror("Error", f"Startup error:\n{e}")
                print(f"Startup error: {e}")
            
            finally:
                self.show_progress(False)
                self.enable_buttons()
        
        threading.Thread(target=run, daemon=True).start()
    
    def stop_services(self):
        """Stop all services"""
        def run():
            try:
                self.disable_buttons()
                if self.status_var:
                    self.status_var.set("🔄 Stopping services...")
                
                subprocess.run(['pkill', 'ollama'], stderr=subprocess.DEVNULL)
                subprocess.run(['pkill', '-f', 'open-webui'], stderr=subprocess.DEVNULL)
                
                time.sleep(2)
                
                if self.status_var:
                    self.status_var.set("● Services stopped")
                # No messagebox - just visual confirmation
                
            except Exception as e:
                if self.window_visible:
                    messagebox.showerror("Error", f"Stop error:\n{e}")
                print(f"Stop error: {e}")
            
            finally:
                self.enable_buttons()
        
        threading.Thread(target=run, daemon=True).start()
    
    def open_webui(self):
        """Open WebUI in browser"""
        webbrowser.open('http://localhost:8080')
    
    def quit_app(self, widget=None):
        """Quit application completely"""
        print("Closing application...")

        # Stop services
        try:
            subprocess.run(['pkill', 'ollama'], stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'open-webui'], stderr=subprocess.DEVNULL)
        except:
            pass
        
        # Close tkinter
        if self.root:
            self.root.quit()
            self.root.destroy()
        
        # Close GTK if used
        if SYSTRAY_AVAILABLE:
            Gtk.main_quit()
        
        sys.exit(0)
    
    def run(self):
        """Run application"""
        print("🤖 Ollama Controller started")
        if SYSTRAY_AVAILABLE:
            print("📍 System tray active - Right click for menu")
            if not self.window_visible:
                print("💡 Window hidden - Left click on icon to show")
            
            # Run GTK and tkinter together
            def run_gtk():
                Gtk.main()
            
            def run_tkinter():
                self.root.mainloop()
            
            # GTK in separate thread
            gtk_thread = threading.Thread(target=run_gtk, daemon=True)
            gtk_thread.start()
            
            # tkinter in main thread
            try:
                run_tkinter()
            except KeyboardInterrupt:
                self.quit_app()
        else:
            # Classic window mode
            try:
                self.root.mainloop()
            except KeyboardInterrupt:
                self.quit_app()

def main():
    # Install requests if needed
    try:
        import requests
    except ImportError:
        print("Installing requests...")
        subprocess.check_call(['pip3', 'install', '--user', 'requests'])
        import requests
    
    app = OllamaController()
    app.run()

if __name__ == "__main__":
    main()