from __future__ import annotations
import tkinter as tk
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

# add a radio group to the GUI
def _add_radio_group(
    parent: ctk.CTkFrame, # the parent frame
    row: int, # the row number
    label_text: str, # the label text
    options: tuple[str, ...], # the options
    variable: tk.StringVar, # the variable
) -> None:
    ctk.CTkLabel(parent, text=label_text).grid(
        row=row, column=0, sticky="w", padx=(0, 12), pady=8
    )
    group_frame = ctk.CTkFrame(parent, fg_color="transparent")
    group_frame.grid(row=row, column=1, sticky="ew", pady=8)
    for col, option in enumerate(options):
        ctk.CTkRadioButton(
            group_frame,
            text=option,
            variable=variable,
            value=option,
        ).grid(row=0, column=col, sticky="w", padx=(0, 16))

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

    input_frame = ctk.CTkFrame(window, fg_color="transparent")
    input_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
    input_frame.grid_columnconfigure(1, weight=1)

    engine_label = ctk.CTkLabel(input_frame, text="Inference engine")
    engine_label.grid(row=0, column=0, sticky="w", padx=(0, 12), pady=8)

    engine_combo = ctk.CTkComboBox(input_frame, values=list(INFERENCE_ENGINES), state="readonly")
    engine_combo.set(INFERENCE_ENGINES[0])
    engine_combo.grid(row=0, column=1, sticky="ew", pady=8)

    use_case_label = ctk.CTkLabel(input_frame, text="Primary use case")
    use_case_label.grid(row=1, column=0, sticky="w", padx=(0, 12), pady=8)

    use_case_combo = ctk.CTkComboBox(input_frame, values=list(PRIMARY_USE_CASES), state="readonly")
    use_case_combo.set(PRIMARY_USE_CASES[0])
    use_case_combo.grid(row=1, column=1, sticky="ew", pady=8)

    context_length_var = tk.StringVar(value=CONTEXT_LENGTH_OPTIONS[0])
    performance_priority_var = tk.StringVar(value=PERFORMANCE_PRIORITY_OPTIONS[0])

    _add_radio_group(
        input_frame,
        row=2,
        label_text="Context length preference",
        options=CONTEXT_LENGTH_OPTIONS,
        variable=context_length_var,
    )
    _add_radio_group(
        input_frame,
        row=3,
        label_text="Performance priority",
        options=PERFORMANCE_PRIORITY_OPTIONS,
        variable=performance_priority_var,
    )
    window.mainloop()

if __name__ == "__main__":
    run_gui()