from __future__ import annotations
from fetch import fetch_all
from gemini import GeminiApiKeyNotFoundError, generate_report
from hardware import detect_hardware
from prompt import HardwareSnapshot, UserSelections, build_prompt

# run the pipeline and return the report
def run_pipeline(hardware: HardwareSnapshot, selections: UserSelections) -> str:
    try:
        fetch_result = fetch_all()
        system_prompt, user_prompt = build_prompt(hardware, selections, fetch_result)
        return generate_report(system_prompt, user_prompt)
    except GeminiApiKeyNotFoundError as exc:
        return str(exc)

def main() -> None:
    hardware = detect_hardware()
    from gui import run_gui

    def analyze(selections: UserSelections) -> str:
        return run_pipeline(hardware, selections)

    run_gui(analyze_callback=analyze)

if __name__ == "__main__":
    main()