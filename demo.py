#!/usr/bin/env python3

import sys

from config import DebateConfig
from debate_app import DebateApp


def main():
    # Check if voting mode is requested
    voting_mode = "--voting" in sys.argv
    classic_mode = "--classic" in sys.argv
    
    # Configure the demo
    config = DebateConfig()
    
    if classic_mode:
        config.classic_mode = True
        config.voting_enabled = False
        print("Running demo in CLASSIC mode (3 fixed rounds)")
    elif voting_mode:
        config.voting_enabled = True
        config.classic_mode = False
        config.consensus_threshold = 0.70  # Lower threshold for demo
        config.min_iterations = 2
        config.max_iterations = 5  # Limit for demo
        print("Running demo in VOTING mode (consensus-based)")
    else:
        # Default to voting mode for demo
        config.voting_enabled = True
        config.classic_mode = False
        config.consensus_threshold = 0.70
        config.min_iterations = 2
        config.max_iterations = 5
        print("Running demo in VOTING mode (use --classic for original format)")
    
    app = DebateApp(config)
    
    # Demo questions based on mode
    if voting_mode or (not classic_mode and not voting_mode):
        # Voting mode - use a question that might reach consensus
        question = "Should companies allow employees to work from home permanently?"
    else:
        # Classic mode - use original demo question
        question = "Should we invest more in renewable energy or nuclear power?"
    
    # Set demo mode flag to skip user input
    app.demo_mode = True
    
    app.display_header()
    print(f"\n[Demo Mode] Automatically debating: {question}\n")
    
    if config.voting_enabled and not config.classic_mode:
        print("[yellow]Note: In interactive mode, you would press Enter between iterations.[/yellow]")
        print("[yellow]This demo will automatically proceed through iterations.[/yellow]\n")
    
    app.run_debate(question)
    
    print("\n[Demo Complete]")
    if config.voting_enabled:
        print("The debate continued until consensus was reached through voting.")
        print("Try running with --classic to see the original 3-round format.")
    else:
        print("The debate ran for exactly 3 rounds as in the original format.")
        print("Try running with --voting to see the consensus-based format.")

if __name__ == "__main__":
    main()