from __future__ import annotations
import tkinter as tk
from collections.abc import Callable
import customtkinter as ctk

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

def _create_report_textbox(parent: ctk.CTkFrame, height: int = REPORT_TEXTBOX_HEIGHT) -> ctk.CTkTextbox:
    report_text = ctk.CTkTextbox(parent, font=REPORT_FONT, height=height, wrap="word", activate_scrollbars=True)
    report_text.insert("1.0", REPORT_PLACEHOLDER)
    report_text.configure(state="disabled")
    return report_text

# Phase 7 calls this to populate the report
def _set_report_content(report_text: ctk.CTkTextbox, content: str, save_button: ctk.CTkButton | None = None) -> None:
    report_text.configure(state="normal")
    report_text.delete("1.0", "end")
    report_text.insert("1.0", content)
    report_text.configure(state="disabled")
    if save_button is not None:
        save_button.configure(state="normal")

# opens save dialog and writes textbox content to disk
def _save_report(report_text: ctk.CTkTextbox, parent: ctk.CTk) -> None:
    path = tk.filedialog.asksaveasfilename(parent=parent, title="Save report", defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
    if not path:
        return
    content = report_text.get("1.0", "end-1c")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# open the main window and block until the user closes it; Analyze button and report area
def run_gui(analyze_callback: Callable[[dict[str, str]], str] | None = None) -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    window = ctk.CTk()
    window.title("Local LLM Advisor")
    window.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
    window.minsize(WINDOW_MIN_SIZE[0], WINDOW_MIN_SIZE[1])

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
    report_frame.grid_rowconfigure(1, weight=1)

    header_frame = ctk.CTkFrame(report_frame, fg_color="transparent")
    header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    header_frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(header_frame, text="Report", font=section_font).grid(row=0, column=0, sticky="w")

    report_text = _create_report_textbox(report_frame)
    report_text.grid(row=1, column=0, sticky="nsew")

    save_button = ctk.CTkButton(
        header_frame,
        text="Save report",
        width=BUTTON_WIDTH,
        font=label_font,
        state="disabled",
        command=lambda: _save_report(report_text, window),
    )
    save_button.grid(row=0, column=1, sticky="e")

    # handle the analyze button
    def _handle_analyze() -> None:
        selections = get_selections(engine_combo, use_case_combo, context_length_var, performance_priority_var)
        if analyze_callback is None:
            print(selections)
            return
        report = analyze_callback(selections)
        _set_report_content(report_text, report, save_button)

    analyze_button.configure(command=_handle_analyze)

    window.mainloop()

if __name__ == "__main__":
    run_gui()