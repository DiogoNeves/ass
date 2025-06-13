#!/usr/bin/env python3

import time
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.columns import Columns
from personality import PersonalityConfig, create_personality

console = Console()

class DebateApp:
    def __init__(self):
        self.personalities = self._create_personalities()
        self.judge = self._create_judge()
        
    def _create_personalities(self):
        personalities = {}
        
        # Claude Big Picture Positive
        personalities["claude_positive"] = create_personality(PersonalityConfig(
            name="Claude Optimist",
            model_provider="claude",
            model_name="claude-sonnet-4-20250514",
            system_prompt="""You are an optimistic, big-picture thinker who focuses on possibilities and opportunities. 
            You tend to see the bright side of situations and think creatively about solutions. You're enthusiastic 
            and forward-thinking, but sometimes might overlook practical constraints or potential problems. 
            In debates, you champion innovative approaches and highlight potential benefits.
            Keep responses concise (2-3 paragraphs max).""",
            traits={"optimism": 9, "creativity": 8, "detail_focus": 3}
        ))
        
        # Claude Detail-Oriented Negative
        personalities["claude_negative"] = create_personality(PersonalityConfig(
            name="Claude Skeptic",
            model_provider="claude",
            model_name="claude-sonnet-4-20250514",
            system_prompt="""You are a detail-oriented, cautious thinker who focuses on potential problems and risks. 
            You're analytical and methodical, often pointing out flaws or limitations in proposed solutions. 
            You tend to be pessimistic and focus on what could go wrong. While sometimes seen as negative, 
            your critical thinking helps prevent costly mistakes.
            Keep responses concise (2-3 paragraphs max).""",
            traits={"pessimism": 8, "analytical": 9, "risk_focus": 9}
        ))
        
        # OpenAI Big Picture Positive
        personalities["openai_positive"] = create_personality(PersonalityConfig(
            name="GPT Visionary",
            model_provider="openai",
            model_name="gpt-4.1-2025-04-14",
            system_prompt="""You are an optimistic, big-picture thinker who focuses on possibilities and opportunities. 
            You tend to see the bright side of situations and think creatively about solutions. You're enthusiastic 
            and forward-thinking, but sometimes might overlook practical constraints or potential problems. 
            In debates, you champion innovative approaches and highlight potential benefits.
            Keep responses concise (2-3 paragraphs max).""",
            traits={"optimism": 9, "creativity": 8, "detail_focus": 3}
        ))
        
        # OpenAI Detail-Oriented Negative
        personalities["openai_negative"] = create_personality(PersonalityConfig(
            name="GPT Critic",
            model_provider="openai",
            model_name="gpt-4.1-2025-04-14",
            system_prompt="""You are a detail-oriented, cautious thinker who focuses on potential problems and risks. 
            You're analytical and methodical, often pointing out flaws or limitations in proposed solutions. 
            You tend to be pessimistic and focus on what could go wrong. While sometimes seen as negative, 
            your critical thinking helps prevent costly mistakes.
            Keep responses concise (2-3 paragraphs max).""",
            traits={"pessimism": 8, "analytical": 9, "risk_focus": 9}
        ))
        
        return personalities
    
    def _create_judge(self):
        return create_personality(PersonalityConfig(
            name="Judge",
            model_provider="claude",
            model_name="claude-sonnet-4-20250514",
            system_prompt="""You are an impartial judge tasked with synthesizing different perspectives into a final decision. 
            You carefully consider all arguments presented, weighing their merits and identifying the strongest points 
            from each side. You aim to find balanced solutions that acknowledge both opportunities and risks. 
            Your final judgment should be well-reasoned and practical.
            Provide a clear final answer with reasoning.""",
            traits={"impartiality": 10, "synthesis": 9, "balance": 9}
        ))
    
    def display_header(self):
        header = Text("🏛️  ASS - ARGUMENTATIVE SYSTEM SERVICE  🏛️", style="bold blue")
        console.print(Panel(header, style="blue"))
        console.print()
    
    def get_question(self):
        console.print("[bold cyan]Welcome to ASS![/bold cyan]")
        console.print("Four AI personalities will debate your question, then a judge will make the final decision.\n")
        
        question = Prompt.ask("[bold yellow]What question would you like them to debate?[/bold yellow]")
        return question
    
    def run_debate(self, question: str):
        console.print(f"\n[bold magenta]🎯 DEBATE TOPIC:[/bold magenta] {question}\n")
        
        debate_context = ""
        debate_order = ["claude_positive", "openai_negative", "openai_positive", "claude_negative"]
        
        for round_num in range(1, 4):  # 3 rounds max
            console.print(f"[bold white]═══ ROUND {round_num} ═══[/bold white]\n")
            
            for personality_key in debate_order:
                personality = self.personalities[personality_key]
                
                # Show thinking animation
                with Progress(
                    SpinnerColumn(),
                    TextColumn(f"[bold]{personality.config.name} is thinking..."),
                    transient=True,
                    console=console
                ) as progress:
                    task = progress.add_task("thinking", total=None)
                    time.sleep(1)
                    
                    response = personality.generate_response(question, debate_context)
                
                # Display response in styled panel
                style_map = {
                    "claude_positive": "green",
                    "claude_negative": "red", 
                    "openai_positive": "blue",
                    "openai_negative": "yellow"
                }
                
                console.print(Panel(
                    response,
                    title=f"💭 {personality.config.name}",
                    style=style_map[personality_key],
                    padding=(1, 2)
                ))
                console.print()
                
                # Add to context for next participants
                debate_context += f"\n{personality.config.name}: {response}\n"
        
        # Judge's final decision
        console.print("[bold white]═══ FINAL JUDGMENT ═══[/bold white]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold]The Judge is deliberating..."),
            transient=True,
            console=console
        ) as progress:
            task = progress.add_task("judging", total=None)
            time.sleep(2)
            
            final_decision = self.judge.generate_response(
                question, 
                f"Here are the arguments from the debate:\n{debate_context}\n\nPlease provide your final judgment."
            )
        
        console.print(Panel(
            final_decision,
            title="⚖️  FINAL DECISION",
            style="bold white",
            padding=(1, 2)
        ))
    
    def run(self):
        self.display_header()
        question = self.get_question()
        self.run_debate(question)
        
        console.print("\n[bold green]Thank you for using ASS![/bold green]")

def main():
    app = DebateApp()
    app.run()

if __name__ == "__main__":
    main()