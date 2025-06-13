#!/usr/bin/env python3

from debate_app import DebateApp

def main():
    app = DebateApp()
    
    # Demo question
    question = "Should we invest more in renewable energy or nuclear power?"
    
    app.display_header()
    print(f"Demo question: {question}\n")
    app.run_debate(question)

if __name__ == "__main__":
    main()