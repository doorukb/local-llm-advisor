from __future__ import annotations
import customtkinter as ctk

# GUI for Local-LLM-Advisor
# main window skeleton
# input controls and report area come in later

# open the main window and block until the user closes it
def run_gui() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    window = ctk.CTk()
    window.title("Local LLM Advisor")
    window.geometry("800x700")
    window.minsize(640, 560)

    window.grid_columnconfigure(0, weight=1)
    window.grid_rowconfigure(0, weight=0)
    window.grid_rowconfigure(1, weight=1)

    window.mainloop()


if __name__ == "__main__":
    run_gui()