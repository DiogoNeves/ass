#!/usr/bin/env python3

import sys

from rich.console import Console

from config import DebateConfig
from debate_app import DebateApp

console = Console()


def main():
    voting_mode = "--voting" in sys.argv
    classic_mode = "--classic" in sys.argv

    config = DebateConfig()

    if classic_mode:
        config.classic_mode = True
        config.voting_enabled = False
        console.print("Running demo in CLASSIC mode (3 fixed rounds)")
    else:
        config.voting_enabled = True
        config.classic_mode = False
        config.consensus_threshold = 0.70
        config.min_iterations = 2
        config.max_iterations = 5
        if voting_mode:
            console.print("Running demo in VOTING mode (consensus-based)")
        else:
            console.print("Running demo in VOTING mode (use --classic for original format)")

    app = DebateApp(config)

    if classic_mode:
        question = "Should we invest more in renewable energy or nuclear power?"
    else:
        question = "Should companies allow employees to work from home permanently?"

    app.display_header()
    console.print(f"\n[dim]\\[Demo Mode] Automatically debating: {question}[/dim]\n")

    if config.voting_enabled and not config.classic_mode:
        console.print("[yellow]Note: In interactive mode, you would press Enter between iterations.[/yellow]")
        console.print("[yellow]This demo will automatically proceed through iterations.[/yellow]\n")

    app.run_debate(question)

    console.print("\n[dim]\\[Demo Complete][/dim]")
    if config.voting_enabled:
        console.print("The debate continued until consensus was reached through voting.")
        console.print("Try running with --classic to see the original 3-round format.")
    else:
        console.print("The debate ran for exactly 3 rounds as in the original format.")
        console.print("Try running with --voting to see the consensus-based format.")

if __name__ == "__main__":
    main()
