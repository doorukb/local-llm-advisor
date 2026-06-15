from __future__ import annotations
import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog
from tkinter import font as tkfont
import customtkinter as ctk
from advisor import STATUS_FETCHING, STATUS_GENERATING
from config import has_api_key, save_api_key

AnalyzeCallback = Callable[[dict[str, str], Callable[[str], None] | None], str]
INFERENCE_ENGINES = ("Ollama", "llama.cpp", "LM Studio")
PRIMARY_USE_CASES = (
    "General chat",
    "Coding assistant",
    "Document Q&A",
    "Creative writing",
    "Summarization",
)
CONTEXT_LENGTH_OPTIONS = (
    "Short (2K-4K)",
    "Medium (8K-16K)",
    "Long (32K+)",
)
PERFORMANCE_PRIORITY_OPTIONS = (
    "Speed (tokens/sec)",
    "Quality (best output at hardware limits)",
    "Balanced",
)

REPORT_PLACEHOLDER = (
    "Your hardware and model recommendations will appear here after you click Analyze."
)

REPORT_FONT: tuple[str, int] = ("Courier New", 13)

_CANDIDATE_MONO_FONTS = (
    "Courier New",
    "Consolas",
    "Menlo",
    "DejaVu Sans Mono",
    "Liberation Mono",
    "Courier",
)

WINDOW_SIZE = (820, 720)
WINDOW_MIN_SIZE = (700, 620)

OUTER_PAD_X = 24
INPUT_PAD_Y = (24, 12)
REPORT_PAD_Y = (8, 24)

LABEL_COL_MINSIZE = 210
LABEL_PAD = (0, 16)
ROW_PAD_Y = 6

COMBO_HEIGHT = 32
BUTTON_WIDTH = 140
REPORT_TEXTBOX_HEIGHT = 320

# get the selections from the dropdown menus and radio buttons
def get_selections(
    engine_combo: ctk.CTkComboBox, # the inference engine dropdown menu
    use_case_combo: ctk.CTkComboBox, # the primary use case dropdown menu
    context_length_var: tk.StringVar, # the context length radio button
    performance_priority_var: tk.StringVar, # the performance priority radio button
) -> dict[str, str]:
    return {
        "inference_engine": engine_combo.get(),
        "primary_use_case": use_case_combo.get(),
        "context_length": context_length_var.get(),
        "performance_priority": performance_priority_var.get(),
    }

def _add_labeled_combobox(parent: ctk.CTkFrame, row: int, label_text: str, values: tuple[str, ...], label_font: ctk.CTkFont) -> ctk.CTkComboBox:
    ctk.CTkLabel(parent, text=label_text, font=label_font, anchor="e").grid(row=row, column=0, sticky="e", padx=LABEL_PAD, pady=ROW_PAD_Y)

    combo = ctk.CTkComboBox(parent, values=list(values), state="readonly", height=COMBO_HEIGHT, font=label_font)
    combo.set(values[0])
    combo.grid(row=row, column=1, sticky="ew", pady=ROW_PAD_Y)
    return combo

# add a radio group to the GUI
def _add_radio_group(parent: ctk.CTkFrame, row: int, label_text: str, options: tuple[str, ...], variable: tk.StringVar, label_font: ctk.CTkFont) -> None:
    ctk.CTkLabel(parent, text=label_text, font=label_font, anchor="e").grid(row=row, column=0, sticky="e", padx=LABEL_PAD, pady=ROW_PAD_Y)
    group_frame = ctk.CTkFrame(parent, fg_color="transparent")
    group_frame.grid(row=row, column=1, sticky="ew", pady=ROW_PAD_Y)
    for col, option in enumerate(options):
        ctk.CTkRadioButton(group_frame, text=option, variable=variable, value=option, font=label_font).grid(row=0, column=col, sticky="w", padx=(0, 20))

def _resolve_report_font(root: tk.Misc, size: int = 13) -> tuple[str, int]:
    families = set(tkfont.families(root))
    for family in _CANDIDATE_MONO_FONTS:
        if family in families:
            return (family, size)
    return ("TkFixedFont", size)

def _create_report_textbox(parent: ctk.CTkFrame, font: tuple[str, int], height: int = REPORT_TEXTBOX_HEIGHT) -> ctk.CTkTextbox:
    report_text = ctk.CTkTextbox(parent, font=font, height=height, wrap="word", activate_scrollbars=True)
    report_text.insert("1.0", REPORT_PLACEHOLDER)
    report_text.configure(state="disabled")
    return report_text

def _set_report_content(report_text: ctk.CTkTextbox, content: str, save_button: ctk.CTkButton | None = None) -> None:
    report_text.configure(state="normal")
    report_text.delete("1.0", "end")
    report_text.insert("1.0", content)
    report_text.configure(state="disabled")
    if save_button is not None:
        save_button.configure(state="normal")

def _set_loading_content(report_text: ctk.CTkTextbox, message: str) -> None:
    report_text.configure(state="normal")
    report_text.delete("1.0", "end")
    report_text.insert("1.0", message)
    report_text.configure(state="disabled")

def _show_loading_ui(report_text: ctk.CTkTextbox, message: str, progress_bar: ctk.CTkProgressBar) -> None:
    _set_loading_content(report_text, message)
    progress_bar.set(0.1)
    progress_bar.grid()

def _hide_loading_ui(progress_bar: ctk.CTkProgressBar) -> None:
    progress_bar.grid_remove()

# first-run modal to collect and persist the Gemini API key
def _prompt_api_key(parent: ctk.CTk) -> None:
    dialog = ctk.CTkToplevel(parent)
    dialog.title("Gemini API Key")
    dialog.geometry("480x220")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    label_font = ctk.CTkFont(size=13)
    dialog.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(dialog, text="Enter your free Gemini API key from Google AI Studio.", font=label_font, wraplength=440).grid(row=0, column=0, padx=24, pady=(24, 8), sticky="w")
    key_entry = ctk.CTkEntry(dialog, show="*", font=label_font, width=420)
    key_entry.grid(row=1, column=0, padx=24, pady=(0, 8), sticky="ew")
    error_label = ctk.CTkLabel(dialog, text="API key cannot be empty.", font=label_font, text_color="#f87171")
    error_label.grid(row=2, column=0, padx=24, pady=(0, 8), sticky="w")
    error_label.grid_remove()

    button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    button_frame.grid(row=3, column=0, padx=24, pady=(0, 24), sticky="e")

    def _close_dialog() -> None:
        dialog.grab_release()
        dialog.destroy()

    def _on_save() -> None:
        if not key_entry.get().strip():
            error_label.grid()
            return
        save_api_key(key_entry.get())
        _close_dialog()

    ctk.CTkButton(button_frame, text="Cancel", width=BUTTON_WIDTH, font=label_font, command=_close_dialog).grid(row=0, column=0, padx=(0, 12))
    ctk.CTkButton(button_frame, text="Save", width=BUTTON_WIDTH, font=label_font, command=_on_save).grid(row=0, column=1)
    key_entry.focus_set()
    dialog.wait_window(dialog)

# opens save dialog and writes textbox content to disk
def _save_report(report_text: ctk.CTkTextbox, parent: ctk.CTk) -> None:
    path = filedialog.asksaveasfilename(parent=parent, title="Save report", defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
    if not path:
        return
    content = report_text.get("1.0", "end-1c")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# open the main window and block until the user closes it; Analyze button and report area
def run_gui(analyze_callback: AnalyzeCallback | None = None) -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    window = ctk.CTk()
    window.title("Local LLM Advisor")
    window.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
    window.minsize(WINDOW_MIN_SIZE[0], WINDOW_MIN_SIZE[1])

    if not has_api_key():
        _prompt_api_key(window)

    label_font = ctk.CTkFont(size=13)
    section_font = ctk.CTkFont(size=14, weight="bold")

    # add the window
    window.grid_columnconfigure(0, weight=1)
    window.grid_rowconfigure(0, weight=0)
    window.grid_rowconfigure(1, weight=1)

    # add the input frame
    input_frame = ctk.CTkFrame(window, fg_color="transparent")
    input_frame.grid(row=0, column=0, sticky="ew", padx=OUTER_PAD_X, pady=INPUT_PAD_Y)
    input_frame.grid_columnconfigure(0, minsize=LABEL_COL_MINSIZE)
    input_frame.grid_columnconfigure(1, weight=1)

    # add the dropdown menus and radio buttons
    engine_combo = _add_labeled_combobox(input_frame, row=0, label_text="Inference engine", values=INFERENCE_ENGINES, label_font=label_font)
    use_case_combo = _add_labeled_combobox(input_frame, row=1, label_text="Primary use case", values=PRIMARY_USE_CASES, label_font=label_font)
    # add the context length radio buttons
    context_length_var = tk.StringVar(value=CONTEXT_LENGTH_OPTIONS[0])
    performance_priority_var = tk.StringVar(value=PERFORMANCE_PRIORITY_OPTIONS[0])

    _add_radio_group(
        input_frame,
        row=2,
        label_text="Context length preference",
        options=CONTEXT_LENGTH_OPTIONS,
        variable=context_length_var,
        label_font=label_font,
    )
    _add_radio_group(
        input_frame,
        row=3,
        label_text="Performance priority",
        options=PERFORMANCE_PRIORITY_OPTIONS,
        variable=performance_priority_var,
        label_font=label_font,
    )
    analyze_button = ctk.CTkButton(
        input_frame,
        text="Analyze",
        width=BUTTON_WIDTH,
        font=label_font,
    )
    analyze_button.grid(row=4, column=1, sticky="w", pady=(16, 0))

    report_frame = ctk.CTkFrame(window, fg_color="transparent")
    report_frame.grid(row=1, column=0, sticky="nsew", padx=OUTER_PAD_X, pady=REPORT_PAD_Y)
    report_frame.grid_columnconfigure(0, weight=1)
    report_frame.grid_rowconfigure(2, weight=1)

    # add the header frame
    header_frame = ctk.CTkFrame(report_frame, fg_color="transparent")
    header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    header_frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(header_frame, text="Report", font=section_font).grid(row=0, column=0, sticky="w")

    # add the progress bar
    progress_bar = ctk.CTkProgressBar(report_frame, height=8)
    progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    progress_bar.grid_remove()

    # add the report textbox
    report_text = _create_report_textbox(report_frame, _resolve_report_font(window))
    report_text.grid(row=2, column=0, sticky="nsew")
    # add the save button
    save_button = ctk.CTkButton(
        header_frame,
        text="Save report",
        width=BUTTON_WIDTH,
        font=label_font,
        state="disabled",
        command=lambda: _save_report(report_text, window),
    )
    save_button.grid(row=0, column=1, sticky="e")

    # add the analyze running flag
    analyze_running = False
    pulse_after_id: str | None = None
    pulse_direction = 1

    def _pulse_progress(step: float = 0.1) -> None:
        nonlocal pulse_after_id, pulse_direction
        if not analyze_running:
            return
        progress_bar.set(step)
        if step >= 0.9:
            pulse_direction = -1
        elif step <= 0.1:
            pulse_direction = 1
        pulse_after_id = window.after(50, lambda: _pulse_progress(step + pulse_direction * 0.08))

    def _stop_pulse() -> None:
        nonlocal pulse_after_id
        if pulse_after_id is not None:
            window.after_cancel(pulse_after_id)
            pulse_after_id = None

    def _finish_analyze(report: str) -> None:
        nonlocal analyze_running
        analyze_running = False
        _stop_pulse()
        _hide_loading_ui(progress_bar)
        analyze_button.configure(state="normal")
        _set_report_content(report_text, report, save_button)

    # handle the analyze button
    def _handle_analyze() -> None:
        nonlocal analyze_running
        selections = get_selections(engine_combo, use_case_combo, context_length_var, performance_priority_var)
        if analyze_callback is None:
            print(selections)
            return
        if analyze_running:
            return

        analyze_running = True
        analyze_button.configure(state="disabled")
        save_button.configure(state="disabled")
        _show_loading_ui(report_text, STATUS_FETCHING, progress_bar)
        _pulse_progress()

        # start the worker thread
        def worker() -> None:
            def status(msg: str) -> None:
                window.after(0, lambda m=msg: _set_loading_content(report_text, m))

            try:
                report = analyze_callback(selections, status)
            except Exception as exc:
                report = str(exc)

            window.after(0, lambda r=report: _finish_analyze(r))

        threading.Thread(target=worker, daemon=True).start()

    analyze_button.configure(command=_handle_analyze)
    window.mainloop()

if __name__ == "__main__":
    run_gui()