#!/usr/bin/env python3

import curses
import json
import time
import re
import random
import sys
from datetime import datetime
from pathlib import Path

class Player:
    def __init__(self, name, email, marketing_consent=False):
        self.name = name
        self.email = email
        self.marketing_consent = marketing_consent
        self.score = 0
        self.total_time = 0
        self.timestamp = datetime.now().isoformat()
        self.question_details = []  # Track each question's result

class Qliz:
    def __init__(self, stdscr, config_file):
        self.stdscr = stdscr
        self.config_file = config_file
        self.quiz_metadata = {}
        self.all_questions = []  # All available questions
        self.questions = []      # Selected questions for current game
        self.scoreboard_file = None  # Will be set from config
        self.stats_file = None  # Will be set from config

        # Setup curses
        curses.curs_set(0)  # Hide cursor
        curses.start_color()
        curses.use_default_colors()

        # Initialize 80s arcade color pairs
        curses.init_pair(1, curses.COLOR_CYAN, -1)      # Cyan text
        curses.init_pair(2, curses.COLOR_YELLOW, -1)    # Yellow text
        curses.init_pair(3, curses.COLOR_MAGENTA, -1)   # Magenta text
        curses.init_pair(4, curses.COLOR_GREEN, -1)     # Green text
        curses.init_pair(5, curses.COLOR_RED, -1)       # Red text
        curses.init_pair(6, curses.COLOR_WHITE, -1)     # White text

        self.load_quiz_config()

    def load_quiz_config(self):
        """Load quiz configuration and questions from external JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            self.quiz_metadata = config.get('quiz_metadata', {})
            questions_data = config.get('questions', [])

            # Set scoreboard file from config or use default
            self.scoreboard_file = self.quiz_metadata.get('scoreboard_file', 'scoreboard.json')
            # Set stats file from config or use default
            self.stats_file = self.quiz_metadata.get('stats_file', 'stats.json')

            # Load all available questions
            self.all_questions = []
            for q in questions_data:
                self.all_questions.append({
                    'id': q.get('id', 0),
                    'question': q['question'],
                    'options': q['options'],
                    'correct': q['correct_answer'],
                    'explanation': q.get('explanation', '')
                })

            if not self.all_questions:
                raise ValueError("No questions found in config file")

        except Exception as e:
            self.show_error(f"Error loading config: {e}")
            raise

    def select_random_questions(self):
        """Select random questions for the game based on configuration."""
        questions_per_game = self.quiz_metadata.get('questions_per_game', 5)

        # If we have fewer questions than requested, use all of them
        if len(self.all_questions) <= questions_per_game:
            self.questions = self.all_questions.copy()
        else:
            self.questions = random.sample(self.all_questions, questions_per_game)

    def show_error(self, message):
        """Display error message and exit."""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        self.stdscr.addstr(h//2, (w - len(message))//2, message, curses.color_pair(5))
        self.stdscr.refresh()
        self.stdscr.getch()

    def draw_box(self, y, x, height, width, title="", color=1):
        """Draw a retro box with optional title."""
        # Top border
        self.stdscr.addstr(y, x, "╔" + "═" * (width - 2) + "╗", curses.color_pair(color))

        # Title if provided
        if title:
            title_text = f" {title} "
            title_x = x + (width - len(title_text)) // 2
            self.stdscr.addstr(y, title_x, title_text, curses.color_pair(color) | curses.A_BOLD)

        # Sides
        for i in range(1, height - 1):
            self.stdscr.addstr(y + i, x, "║", curses.color_pair(color))
            self.stdscr.addstr(y + i, x + width - 1, "║", curses.color_pair(color))

        # Bottom border
        self.stdscr.addstr(y + height - 1, x, "╚" + "═" * (width - 2) + "╝", curses.color_pair(color))

    def center_text(self, y, text, color=6):
        """Display centered text."""
        h, w = self.stdscr.getmaxyx()
        x = (w - len(text)) // 2
        if 0 <= y < h and 0 <= x < w:
            self.stdscr.addstr(y, x, text, curses.color_pair(color))

    def blink_text(self, y, x, text, color=2, times=3):
        """Make text blink."""
        for _ in range(times):
            self.stdscr.addstr(y, x, text, curses.color_pair(color) | curses.A_BOLD)
            self.stdscr.refresh()
            time.sleep(0.3)
            self.stdscr.addstr(y, x, " " * len(text))
            self.stdscr.refresh()
            time.sleep(0.3)
        self.stdscr.addstr(y, x, text, curses.color_pair(color) | curses.A_BOLD)

    def draw_big_title(self, start_y, text, color=2):
        """Draw title with decorative border."""
        h, w = self.stdscr.getmaxyx()

        # Add decorative top border
        top_border = "═" * min(len(text) + 6, w - 4)
        self.center_text(start_y, top_border, color=color)

        # Main title text - large and bold
        self.center_text(start_y + 1, f"╡ {text.upper()} ╞", color=color)

        # Add decorative bottom border
        bottom_border = "═" * min(len(text) + 6, w - 4)
        self.center_text(start_y + 2, bottom_border, color=color)

    def show_title_screen(self):
        """Display 80s arcade title screen with branding from config."""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        # Get quiz info from config
        title = self.quiz_metadata.get('title', 'QUIZ GAME')
        description = self.quiz_metadata.get('description', '')

        start_y = h // 2 - 8

        # Qliz branding with decoration
        qliz_art = [
            "╔═══════════════════════════════╗",
            "║         Q L I Z               ║",
            "╚═══════════════════════════════╝"
        ]
        for i, line in enumerate(qliz_art):
            self.center_text(start_y + i, line, color=1)

        # Game title with big styling
        self.draw_big_title(start_y + 5, title, color=2)

        # Description with decorative brackets
        if description:
            desc_text = f"[ {description} ]"
            self.center_text(start_y + 9, desc_text, color=6)

        # Blinking "INSERT COIN" style prompt
        prompt_y = h - 4
        prompt_text = ">>> PRESS ANY KEY TO START <<<"
        self.blink_text(prompt_y, (w - len(prompt_text)) // 2, prompt_text, color=2, times=2)

        # Footer
        footer_msg = "Made with ❤️  and sleepless nights by @jmlero"
        self.center_text(h - 2, footer_msg, color=6)
        self.stdscr.refresh()

        self.stdscr.getch()

    def get_input(self, y, x, prompt, max_length=30, validator=None):
        """Get user input with validation."""
        curses.echo()
        curses.curs_set(1)

        while True:
            self.stdscr.addstr(y, x, prompt, curses.color_pair(2))
            self.stdscr.addstr(y, x + len(prompt), " " * max_length)
            self.stdscr.refresh()

            try:
                user_input = self.stdscr.getstr(y, x + len(prompt), max_length).decode('utf-8').strip()
            except:
                user_input = ""

            if validator:
                valid, message = validator(user_input)
                if valid:
                    break
                else:
                    self.stdscr.addstr(y + 1, x, " " * 60)
                    self.stdscr.addstr(y + 1, x, message, curses.color_pair(5))
                    self.stdscr.refresh()
                    time.sleep(1.5)
                    self.stdscr.addstr(y + 1, x, " " * 60)
            else:
                if user_input:
                    break

        curses.noecho()
        curses.curs_set(0)
        return user_input

    def validate_email(self, email):
        """Validate email format."""
        if not email:
            return False, "Email cannot be empty"
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return True, ""
        return False, "Invalid email format"

    def validate_name(self, name):
        """Validate name."""
        if len(name) >= 2:
            return True, ""
        return False, "Name must be at least 2 characters"

    def get_consent(self, y, x):
        """Get marketing consent with Yes/No toggle."""
        options = ["NO", "YES"]
        selected = 0  # Default to NO

        consent_text = "Consent to receive marketing emails and store your email address?"

        while True:
            # Display question
            self.stdscr.addstr(y, x, consent_text, curses.color_pair(2))

            # Display options
            option_y = y + 1
            for i, option in enumerate(options):
                option_text = f"  {option}  "
                option_x = x + 10 + (i * 15)

                if i == selected:
                    self.stdscr.addstr(option_y, option_x, option_text,
                                     curses.color_pair(3) | curses.A_REVERSE | curses.A_BOLD)
                else:
                    self.stdscr.addstr(option_y, option_x, option_text, curses.color_pair(6))

            # Instructions
            instruction_text = "(←/→ or Y/N to toggle, ENTER to confirm)"
            self.stdscr.addstr(y + 3, x, instruction_text, curses.color_pair(6))

            self.stdscr.refresh()

            # Handle input
            key = self.stdscr.getch()

            if key == curses.KEY_LEFT:
                selected = 0  # NO
            elif key == curses.KEY_RIGHT:
                selected = 1  # YES
            elif key in [ord('n'), ord('N')]:
                selected = 0  # NO
            elif key in [ord('y'), ord('Y')]:
                selected = 1  # YES
            elif key == ord('\n'):
                # Clear the consent prompt area
                for i in range(4):
                    self.stdscr.addstr(y + i, x, " " * 60)
                return selected == 1  # Return True if YES selected

        return False

    def register_player(self):
        """Player registration screen."""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        # Draw registration box (taller to accommodate consent)
        box_width = 60
        box_height = 14
        box_x = (w - box_width) // 2
        box_y = (h - box_height) // 2

        self.draw_box(box_y, box_x, box_height, box_width, "PLAYER REGISTRATION", color=2)

        # Get player info
        name = self.get_input(box_y + 3, box_x + 3, "NAME: ", validator=self.validate_name)
        email = self.get_input(box_y + 5, box_x + 3, "EMAIL: ", validator=self.validate_email)

        # Get marketing consent
        marketing_consent = self.get_consent(box_y + 7, box_x + 3)

        return Player(name, email, marketing_consent)

    def draw_timer_bar(self, y, x, width, elapsed, timeout):
        """Draw a progress bar for the timer."""
        remaining = max(0, timeout - elapsed)
        percentage = remaining / timeout
        filled = int(width * percentage)

        bar = "█" * filled + "░" * (width - filled)

        # Color based on time remaining
        if percentage > 0.5:
            color = 4  # Green
        elif percentage > 0.25:
            color = 2  # Yellow
        else:
            color = 5  # Red

        self.stdscr.addstr(y, x, bar, curses.color_pair(color) | curses.A_BOLD)
        time_text = f"{int(remaining)}s"
        self.stdscr.addstr(y, x + width + 2, time_text, curses.color_pair(color))

    def display_question(self, question_data, question_num, total_questions, selected_idx, score, elapsed_time, timeout):
        """Display question screen with selection highlighting."""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        # Header
        header = f"QUESTION {question_num}/{total_questions}"
        score_text = f"SCORE: {score}/{total_questions}"

        self.stdscr.addstr(1, 2, header, curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(1, w - len(score_text) - 2, score_text, curses.color_pair(1) | curses.A_BOLD)

        # Timer bar
        timer_width = w - 10
        self.draw_timer_bar(3, 5, timer_width, elapsed_time, timeout)

        # Question box
        question_lines = self.wrap_text(question_data['question'], w - 10)
        box_height = len(question_lines) + len(question_data['options']) + 8
        box_y = 5
        box_x = 3
        box_width = w - 6

        self.draw_box(box_y, box_x, box_height, box_width, color=1)

        # Display question
        current_y = box_y + 2
        for line in question_lines:
            self.stdscr.addstr(current_y, box_x + 3, line, curses.color_pair(6))
            current_y += 1

        current_y += 1

        # Display options
        for i, option in enumerate(question_data['options']):
            option_text = f"[{i+1}] {option}"

            if i == selected_idx:
                # Highlight selected option
                self.stdscr.addstr(current_y, box_x + 3, " " * (box_width - 6), curses.color_pair(3) | curses.A_REVERSE)
                self.stdscr.addstr(current_y, box_x + 3, option_text, curses.color_pair(3) | curses.A_REVERSE | curses.A_BOLD)
            else:
                self.stdscr.addstr(current_y, box_x + 3, option_text, curses.color_pair(6))

            current_y += 1

        # Instructions
        instructions = "↑/↓: Navigate  |  ENTER: Select  |  A-Z/1-4: Quick Select"
        self.center_text(h - 2, instructions, color=2)

        self.stdscr.refresh()

    def wrap_text(self, text, width):
        """Wrap text to fit width."""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + len(current_line) <= width:
                current_line.append(word)
                current_length += len(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def show_result(self, is_correct, correct_answer, explanation=""):
        """Show result animation."""
        h, w = self.stdscr.getmaxyx()

        if is_correct:
            text = "*** CORRECT! ***"
            color = 4
        else:
            text = "*** WRONG! ***"
            color = 5

        # Big result text
        result_y = h // 2
        self.blink_text(result_y, (w - len(text)) // 2, text, color=color, times=2)

        # Show correct answer if wrong
        if not is_correct:
            correct_text = f"Correct answer: {correct_answer}"
            self.center_text(result_y + 2, correct_text, color=2)

        # Show explanation
        if explanation:
            exp_lines = self.wrap_text(explanation, w - 20)
            start_y = result_y + 4
            for i, line in enumerate(exp_lines):
                self.center_text(start_y + i, line, color=6)

        self.stdscr.refresh()
        time.sleep(2)

    def play_game(self, player):
        """Main game loop."""
        # Select random questions for this game
        self.select_random_questions()

        time_per_question = self.quiz_metadata.get('time_per_question', 30)
        total_questions = len(self.questions)

        # Ready screen
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        # Quiz title at the top
        title = self.quiz_metadata.get('title', 'QUIZ GAME')
        self.draw_big_title(2, title, color=2)

        self.center_text(h//2 - 5, f"GET READY, {player.name.upper()}!", color=2)
        self.center_text(h//2 - 3, f"{time_per_question} SECONDS PER QUESTION", color=6)
        self.center_text(h//2 - 2, f"{total_questions} QUESTIONS", color=6)

        # Game instructions
        self.center_text(h//2 + 1, "HOW TO PLAY:", color=2)
        self.center_text(h//2 + 2, "Use ↑/↓ ARROW KEYS to navigate options", color=6)
        self.center_text(h//2 + 3, "And press ENTER to confirm your choice", color=6)
        self.center_text(h//2 + 4, " ", color=6)
        self.center_text(h//2 + 5, "Or press 1-4 to quick select your answer", color=6)

        # Clear instruction for spacebar
        spacebar_msg = ">>> PRESS SPACEBAR TO START THE GAME <<<"
        self.center_text(h//2 + 7, spacebar_msg, color=2)

        # Footer
        footer_msg = "Made with ❤️  and sleepless nights by @jmlero"
        self.center_text(h - 2, footer_msg, color=6)

        self.stdscr.refresh()

        # Wait for spacebar press
        while True:
            key = self.stdscr.getch()
            if key == ord(' '):
                break

        total_time = 0
        correct_answers = 0

        for i, question in enumerate(self.questions, 1):
            selected_idx = 0
            answered = False
            start_time = time.time()
            answer = None

            self.stdscr.nodelay(True)  # Non-blocking input

            while not answered:
                elapsed = time.time() - start_time

                if elapsed >= time_per_question:
                    # Timeout
                    break

                self.display_question(question, i, total_questions, selected_idx, correct_answers, elapsed, time_per_question)

                try:
                    key = self.stdscr.getch()

                    if key == curses.KEY_UP:
                        selected_idx = (selected_idx - 1) % len(question['options'])
                    elif key == curses.KEY_DOWN:
                        selected_idx = (selected_idx + 1) % len(question['options'])
                    elif key == ord('\n') or key == ord(' '):
                        answer = selected_idx
                        answered = True
                    # Letter keys (A-F)
                    elif key in [ord('a'), ord('A')]:
                        if len(question['options']) > 0:
                            answer = 0
                            answered = True
                    elif key in [ord('b'), ord('B')]:
                        if len(question['options']) > 1:
                            answer = 1
                            answered = True
                    elif key in [ord('c'), ord('C')]:
                        if len(question['options']) > 2:
                            answer = 2
                            answered = True
                    elif key in [ord('d'), ord('D')]:
                        if len(question['options']) > 3:
                            answer = 3
                            answered = True
                    elif key in [ord('e'), ord('E')]:
                        if len(question['options']) > 4:
                            answer = 4
                            answered = True
                    elif key in [ord('f'), ord('F')]:
                        if len(question['options']) > 5:
                            answer = 5
                            answered = True
                    # Number keys (1-6)
                    elif key in [ord('1')]:
                        if len(question['options']) > 0:
                            answer = 0
                            answered = True
                    elif key in [ord('2')]:
                        if len(question['options']) > 1:
                            answer = 1
                            answered = True
                    elif key in [ord('3')]:
                        if len(question['options']) > 2:
                            answer = 2
                            answered = True
                    elif key in [ord('4')]:
                        if len(question['options']) > 3:
                            answer = 3
                            answered = True
                    elif key in [ord('5')]:
                        if len(question['options']) > 4:
                            answer = 4
                            answered = True
                    elif key in [ord('6')]:
                        if len(question['options']) > 5:
                            answer = 5
                            answered = True
                except:
                    pass

                time.sleep(0.05)  # Small delay to reduce CPU usage

            self.stdscr.nodelay(False)  # Restore blocking input

            time_taken = time.time() - start_time

            # Determine if the answer was correct
            is_correct = False
            if answer is None:
                # Timeout
                total_time += time_per_question
                self.show_result(False, question['options'][question['correct']], "")
            elif answer == question['correct']:
                is_correct = True
                correct_answers += 1
                total_time += time_taken
                self.show_result(True, question['options'][question['correct']], "")
            else:
                total_time += time_taken
                self.show_result(False, question['options'][question['correct']], "")

            # Record question details for statistics
            question_detail = {
                "question_id": question.get('id', 0),
                "question_text": question['question'],
                "options": question['options'],
                "correct_answer": question['correct'],
                "player_answer": answer,
                "is_correct": is_correct,
                "time_taken": time_taken,
                "timed_out": answer is None
            }
            player.question_details.append(question_detail)

        player.score = correct_answers
        player.total_time = total_time

        self.show_game_over(player, total_questions)
        self.save_score(player)
        self.save_game_stats(player)

    def show_game_over(self, player, total_questions):
        """Game over screen."""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        # GAME OVER text
        game_over1 = "╔═╗╔═╗╔╦╗╔═╗  ╔═╗╦  ╦╔═╗╦═╗"
        game_over2 = "║ ╦╠═╣║║║║╣   ║ ║╚╗╔╝║╣ ╠╦╝"
        game_over3 = "╚═╝╩ ╩╩ ╩╚═╝  ╚═╝ ╚╝ ╚═╝╩╚═"

        self.center_text(3, game_over1, color=5)
        self.center_text(4, game_over2, color=5)
        self.center_text(5, game_over3, color=5)

        # Results box
        box_width = 50
        box_height = 10
        box_x = (w - box_width) // 2
        box_y = 8

        self.draw_box(box_y, box_x, box_height, box_width, "FINAL SCORE", color=2)

        # Display stats
        self.stdscr.addstr(box_y + 3, box_x + 5, f"PLAYER: {player.name}", curses.color_pair(6))
        self.stdscr.addstr(box_y + 5, box_x + 5, f"SCORE: {player.score}/{total_questions}", curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(box_y + 6, box_x + 5, f"TIME: {player.total_time:.1f}s", curses.color_pair(1))

        # Check if high score
        scoreboard_data = self.load_scoreboard()
        scores = scoreboard_data.get('scores', [])
        is_high_score = False

        if not scores:
            # First player always gets high score
            is_high_score = True
        else:
            sorted_scores = sorted(scores, key=lambda x: (-x['score'], x['total_time']))
            best_score = sorted_scores[0]

            # New high score if: better score OR (same score AND faster time)
            if player.score > best_score['score']:
                is_high_score = True
            elif player.score == best_score['score'] and player.total_time < best_score['total_time']:
                is_high_score = True

        if is_high_score:
            hs_text = "*** NEW HIGH SCORE! ***"
            self.blink_text(box_y + 8, box_x + (box_width - len(hs_text)) // 2, hs_text, color=2, times=3)

        self.center_text(h - 3, "Press any key to continue...", color=6)
        self.stdscr.refresh()
        self.stdscr.getch()

    def save_score(self, player):
        """Save player score to scoreboard."""
        scoreboard_data = self.load_scoreboard()

        # Get scores array and metadata
        scores = scoreboard_data.get('scores', []) if isinstance(scoreboard_data, dict) else scoreboard_data

        player_data = {
            "name": player.name,
            "email": player.email,
            "marketing_consent": player.marketing_consent,
            "score": player.score,
            "total_time": player.total_time,
            "timestamp": player.timestamp
        }

        scores.append(player_data)

        # Create scoreboard with metadata
        scoreboard = {
            "quiz_title": self.quiz_metadata.get('title', 'Quiz'),
            "quiz_description": self.quiz_metadata.get('description', ''),
            "last_updated": datetime.now().isoformat(),
            "scores": scores
        }

        with open(self.scoreboard_file, 'w') as f:
            json.dump(scoreboard, f, indent=2)

    def load_scoreboard(self):
        """Load scoreboard from file."""
        try:
            with open(self.scoreboard_file, 'r') as f:
                data = json.load(f)
                # Handle both old format (array) and new format (dict with metadata)
                if isinstance(data, list):
                    return {"scores": data}
                return data
        except FileNotFoundError:
            return {"scores": []}

    def save_game_stats(self, player):
        """Save detailed game statistics to stats file."""
        stats_data = self.load_stats()

        game_stats = {
            "player_name": player.name,
            "player_email": player.email,
            "timestamp": player.timestamp,
            "final_score": player.score,
            "total_time": player.total_time,
            "total_questions": len(self.questions),
            "questions": player.question_details
        }

        stats_data.append(game_stats)

        with open(self.stats_file, 'w') as f:
            json.dump(stats_data, f, indent=2)

    def load_stats(self):
        """Load statistics from file."""
        try:
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def display_top5_with_emails(self):
        """Display top 5 players with email addresses."""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        scoreboard_data = self.load_scoreboard()
        scores = scoreboard_data.get('scores', [])
        quiz_title = scoreboard_data.get('quiz_title', 'Quiz')

        # Title
        title1 = "╔╦╗╔═╗╔═╗  ╔═╗  ╔═╗╦  ╔═╗╦ ╦╔═╗╦═╗╔═╗"
        title2 = " ║ ║ ║╠═╝  ╚═╗  ╠═╝║  ╠═╣╚╦╝║╣ ╠╦╝╚═╗"
        title3 = " ╩ ╚═╝╩    ╚═╝  ╩  ╩═╝╩ ╩ ╩ ╚═╝╩╚═╚═╝"

        self.center_text(2, title1, color=2)
        self.center_text(3, title2, color=2)
        self.center_text(4, title3, color=2)

        # Show quiz title
        self.center_text(6, quiz_title, color=1)

        if not scores:
            self.center_text(h//2, "NO SCORES YET - BE THE FIRST!", color=5)
        else:
            sorted_scores = sorted(scores, key=lambda x: (-x['score'], x['total_time']))[:5]

            # Scoreboard box
            box_width = min(80, w - 10)
            box_height = min(len(sorted_scores) + 5, h - 10)
            box_x = (w - box_width) // 2
            box_y = 8

            self.draw_box(box_y, box_x, box_height, box_width, color=1)

            # Header
            header = f"{'#':<4} {'NAME':<18} {'EMAIL':<30} {'SCORE':<8} {'TIME':<10}"
            self.stdscr.addstr(box_y + 2, box_x + 3, header, curses.color_pair(2) | curses.A_BOLD)

            # Scores
            for i, score in enumerate(sorted_scores, 1):
                rank = str(i) + "."
                name = score['name'][:16]
                email = score.get('email', 'N/A')[:28]
                score_text = f"{score['score']}"
                time_text = f"{score['total_time']:.1f}s"

                # Color based on rank
                if i == 1:
                    color = 2  # Yellow for 1st
                elif i == 2:
                    color = 6  # White for 2nd
                elif i == 3:
                    color = 3  # Magenta for 3rd
                else:
                    color = 1  # Cyan for others

                line = f"{rank:<4} {name:<18} {email:<30} {score_text:<8} {time_text:<10}"
                self.stdscr.addstr(box_y + 3 + i, box_x + 3, line, curses.color_pair(color))

        self.center_text(h - 2, "Press any key to return...", color=6)
        self.stdscr.refresh()
        self.stdscr.getch()

    def display_scoreboard(self):
        """Display arcade-style scoreboard."""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        scoreboard_data = self.load_scoreboard()
        scores = scoreboard_data.get('scores', [])
        quiz_title = scoreboard_data.get('quiz_title', 'Quiz')

        # Title
        title1 = "╦ ╦╦╔═╗╦ ╦  ╔═╗╔═╗╔═╗╦═╗╔═╗╔═╗"
        title2 = "╠═╣║║ ╦╠═╣  ╚═╗║  ║ ║╠╦╝║╣ ╚═╗"
        title3 = "╩ ╩╩╚═╝╩ ╩  ╚═╝╚═╝╚═╝╩╚═╚═╝╚═╝"

        self.center_text(2, title1, color=2)
        self.center_text(3, title2, color=2)
        self.center_text(4, title3, color=2)

        # Show quiz title
        self.center_text(6, quiz_title, color=1)

        if not scores:
            self.center_text(h//2, "NO SCORES YET - BE THE FIRST!", color=5)
        else:
            sorted_scores = sorted(scores, key=lambda x: (-x['score'], x['total_time']))[:10]

            # Scoreboard box
            box_width = min(70, w - 10)
            box_height = min(len(sorted_scores) + 5, h - 10)
            box_x = (w - box_width) // 2
            box_y = 8

            self.draw_box(box_y, box_x, box_height, box_width, color=1)

            # Header
            header = f"{'#':<4} {'NAME':<20} {'SCORE':<10} {'TIME':<10}"
            self.stdscr.addstr(box_y + 2, box_x + 3, header, curses.color_pair(2) | curses.A_BOLD)

            # Scores
            for i, score in enumerate(sorted_scores, 1):
                rank = str(i) + "."
                name = score['name'][:18]
                score_text = f"{score['score']}"
                time_text = f"{score['total_time']:.1f}s"

                # Color based on rank
                if i == 1:
                    color = 2  # Yellow for 1st
                elif i == 2:
                    color = 6  # White for 2nd
                elif i == 3:
                    color = 3  # Magenta for 3rd
                else:
                    color = 1  # Cyan for others

                line = f"{rank:<4} {name:<20} {score_text:<10} {time_text:<10}"
                self.stdscr.addstr(box_y + 3 + i, box_x + 3, line, curses.color_pair(color))

        self.center_text(h - 2, "Press any key to return...", color=6)
        self.stdscr.refresh()
        self.stdscr.getch()

    def random_player_picker(self):
        """Display total players and randomly pick one showing name and email."""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        scoreboard_data = self.load_scoreboard()
        scores = scoreboard_data.get('scores', [])
        quiz_title = scoreboard_data.get('quiz_title', 'Quiz')

        # Title
        title1 = "╦═╗╔═╗╔╗╔╔╦╗╔═╗╔╦╗  ╔═╗╦╔═╗╦╔═╔═╗╦═╗"
        title2 = "╠╦╝╠═╣║║║ ║║║ ║║║║  ╠═╝║║  ╠╩╗║╣ ╠╦╝"
        title3 = "╩╚═╩ ╩╝╚╝═╩╝╚═╝╩ ╩  ╩  ╩╚═╝╩ ╩╚═╝╩╚═"

        self.center_text(2, title1, color=2)
        self.center_text(3, title2, color=2)
        self.center_text(4, title3, color=2)

        # Show quiz title
        self.center_text(6, quiz_title, color=1)

        if not scores:
            self.center_text(h//2, "NO PLAYERS YET - BE THE FIRST!", color=5)
        else:
            # Count total players
            total_players = len(scores)

            # Randomly select one player
            selected_player = random.choice(scores)

            # Display box
            box_width = min(70, w - 10)
            box_height = 10
            box_x = (w - box_width) // 2
            box_y = (h - box_height) // 2

            self.draw_box(box_y, box_x, box_height, box_width, "LUCKY WINNER", color=3)

            # Total players
            total_text = f"TOTAL PLAYERS: {total_players}"
            self.stdscr.addstr(box_y + 2, box_x + (box_width - len(total_text)) // 2,
                             total_text, curses.color_pair(2) | curses.A_BOLD)

            # Separator
            separator = "─" * (box_width - 6)
            self.stdscr.addstr(box_y + 4, box_x + 3, separator, curses.color_pair(1))

            # Selected player info
            name_text = f"NAME: {selected_player['name']}"
            email_text = f"EMAIL: {selected_player.get('email', 'N/A')}"

            self.stdscr.addstr(box_y + 6, box_x + 5, name_text,
                             curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(box_y + 7, box_x + 5, email_text,
                             curses.color_pair(6))

        self.center_text(h - 2, "Press any key to return...", color=6)
        self.stdscr.refresh()
        self.stdscr.getch()

    def main_menu(self):
        """Main menu with branding from config."""
        menu_options = ["PLAY GAME", "HIGH SCORES", "TOP 5 PLAYERS", "RANDOM PLAYER", "EXIT"]
        selected = 0

        while True:
            self.stdscr.clear()
            h, w = self.stdscr.getmaxyx()

            # Qliz branding at top
            self.center_text(2, "━━━ QLIZ ━━━", color=1)

            # Title with big styling
            title = self.quiz_metadata.get('title', 'QUIZ GAME')
            self.draw_big_title(4, title, color=2)

            # Menu box
            box_width = 40
            box_height = len(menu_options) + 4
            box_x = (w - box_width) // 2
            box_y = (h - box_height) // 2 + 1

            self.draw_box(box_y, box_x, box_height, box_width, "MAIN MENU", color=1)

            # Menu options
            for i, option in enumerate(menu_options):
                option_y = box_y + 2 + i
                option_text = f"  {option}  "
                option_x = box_x + (box_width - len(option_text)) // 2

                if i == selected:
                    self.stdscr.addstr(option_y, option_x - 2, ">>", curses.color_pair(2))
                    self.stdscr.addstr(option_y, option_x, option_text, curses.color_pair(3) | curses.A_REVERSE | curses.A_BOLD)
                    self.stdscr.addstr(option_y, option_x + len(option_text), "<<", curses.color_pair(2))
                else:
                    self.stdscr.addstr(option_y, option_x, option_text, curses.color_pair(6))

            # Instructions
            instructions = "↑/↓: Navigate  |  ENTER: Select  |  Q: Quit"
            self.center_text(h - 3, instructions, color=2)

            # Footer
            footer_msg = "Made with ❤️  and sleepless nights by @jmlero"
            self.center_text(h - 2, footer_msg, color=6)

            self.stdscr.refresh()

            # Handle input
            key = self.stdscr.getch()

            if key == curses.KEY_UP:
                selected = (selected - 1) % len(menu_options)
            elif key == curses.KEY_DOWN:
                selected = (selected + 1) % len(menu_options)
            elif key == ord('\n'):
                if selected == 0:  # Play game
                    player = self.register_player()
                    self.play_game(player)
                elif selected == 1:  # High scores
                    self.display_scoreboard()
                elif selected == 2:  # Top 5 players
                    self.display_top5_with_emails()
                elif selected == 3:  # Random player
                    self.random_player_picker()
                elif selected == 4:  # Exit
                    break
            elif key in [ord('q'), ord('Q')]:
                break

    def run(self):
        """Run the quiz game."""
        self.show_title_screen()
        self.main_menu()

def main(stdscr, config_file):
    """Main entry point for curses."""
    game = Qliz(stdscr, config_file)
    game.run()

if __name__ == "__main__":
    # Check if config file is provided as argument
    if len(sys.argv) < 2:
        print("Usage: python3 qliz.py <config_file.json>")
        print("Example: python3 qliz.py quiz_config.json")
        sys.exit(1)

    config_file = sys.argv[1]

    # Check if file exists
    if not Path(config_file).exists():
        print(f"Error: Config file '{config_file}' not found!")
        sys.exit(1)

    curses.wrapper(main, config_file)
