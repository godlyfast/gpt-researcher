# Human Behavior Simulator for LinkedIn Scraping

import random
import time
import math
import logging
from typing import Optional, Tuple, List
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)


class HumanSimulator:
    """Simulate human-like interactions to avoid detection"""
    
    @staticmethod
    def random_delay(min_seconds: float = 0.5, max_seconds: float = 3.0) -> None:
        """
        Generate random delay with normal distribution to simulate human timing
        
        Args:
            min_seconds: Minimum delay in seconds
            max_seconds: Maximum delay in seconds
        """
        # Use normal distribution for more realistic timing
        mean = (min_seconds + max_seconds) / 2
        std_dev = (max_seconds - min_seconds) / 6  # 99.7% within range
        
        # Generate delay with bounds checking
        delay = random.gauss(mean, std_dev)
        delay = max(min_seconds, min(max_seconds, delay))
        
        # Add micro-variations for realism
        micro_variation = random.uniform(-0.05, 0.05)
        delay = max(0.1, delay + micro_variation)
        
        time.sleep(delay)
        logger.debug(f"Applied human delay: {delay:.2f} seconds")
    
    @staticmethod
    def typing_delay() -> None:
        """Generate realistic typing delay between keystrokes"""
        # Fast typist: 40-60 WPM, Slow: 20-30 WPM
        # Average inter-keystroke interval: 0.1-0.3 seconds
        base_delay = random.gauss(0.15, 0.05)
        
        # Occasional longer pauses (thinking)
        if random.random() < 0.1:  # 10% chance
            base_delay += random.uniform(0.5, 1.5)
        
        time.sleep(max(0.05, base_delay))
    
    @staticmethod
    def human_mouse_movement(driver, target_element: Optional[WebElement] = None) -> None:
        """
        Simulate human-like mouse movement with bezier curves
        
        Args:
            driver: Selenium WebDriver instance
            target_element: Optional target element to move to
        """
        try:
            action = ActionChains(driver)
            
            # Get viewport dimensions
            viewport_width = driver.execute_script("return window.innerWidth;")
            viewport_height = driver.execute_script("return window.innerHeight;")
            
            if target_element:
                # Move to specific element with curve
                HumanSimulator._curved_mouse_movement(driver, target_element)
            else:
                # Random mouse wandering
                num_movements = random.randint(2, 5)
                
                for _ in range(num_movements):
                    # Generate random target position
                    x = random.randint(int(viewport_width * 0.1), int(viewport_width * 0.9))
                    y = random.randint(int(viewport_height * 0.1), int(viewport_height * 0.9))
                    
                    # Move with varying speed
                    duration = random.uniform(0.5, 1.5)
                    steps = random.randint(10, 30)
                    
                    # Execute smooth movement
                    driver.execute_script(f"""
                        var element = document.elementFromPoint({x}, {y});
                        if (element) {{
                            element.dispatchEvent(new MouseEvent('mousemove', {{
                                bubbles: true,
                                cancelable: true,
                                clientX: {x},
                                clientY: {y}
                            }}));
                        }}
                    """)
                    
                    time.sleep(duration / steps)
            
        except Exception as e:
            logger.debug(f"Mouse movement simulation error: {e}")
    
    @staticmethod
    def _curved_mouse_movement(driver, element: WebElement) -> None:
        """Create curved mouse movement to element"""
        try:
            action = ActionChains(driver)
            
            # Get element location
            element_rect = driver.execute_script("""
                var rect = arguments[0].getBoundingClientRect();
                return {x: rect.left + rect.width/2, y: rect.top + rect.height/2};
            """, element)
            
            # Get current mouse position (approximate)
            current_x = driver.execute_script("return window.mouseX || 0;")
            current_y = driver.execute_script("return window.mouseY || 0;")
            
            # Generate control points for bezier curve
            control_x1 = current_x + random.randint(-100, 100)
            control_y1 = current_y + random.randint(-100, 100)
            control_x2 = element_rect['x'] + random.randint(-50, 50)
            control_y2 = element_rect['y'] + random.randint(-50, 50)
            
            # Generate points along bezier curve
            num_points = random.randint(20, 40)
            for i in range(num_points):
                t = i / num_points
                
                # Bezier curve formula
                x = (1-t)**3 * current_x + 3*(1-t)**2*t * control_x1 + 3*(1-t)*t**2 * control_x2 + t**3 * element_rect['x']
                y = (1-t)**3 * current_y + 3*(1-t)**2*t * control_y1 + 3*(1-t)*t**2 * control_y2 + t**3 * element_rect['y']
                
                # Move to point
                action.move_by_offset(int(x - current_x), int(y - current_y))
                current_x, current_y = x, y
                
                # Variable speed
                action.pause(random.uniform(0.01, 0.03))
            
            # Final move to element
            action.move_to_element(element)
            action.perform()
            
        except Exception as e:
            logger.debug(f"Curved mouse movement error: {e}")
            # Fallback to simple movement
            ActionChains(driver).move_to_element(element).perform()
    
    @staticmethod
    def human_typing(element: WebElement, text: str, make_typos: bool = True) -> None:
        """
        Type text with human-like speed and occasional typos
        
        Args:
            element: Input element to type into
            text: Text to type
            make_typos: Whether to simulate typos
        """
        element.clear()
        
        # Sometimes select all and delete instead of clear
        if random.random() < 0.3:
            element.send_keys(Keys.CONTROL + 'a')
            HumanSimulator.typing_delay()
            element.send_keys(Keys.DELETE)
            HumanSimulator.random_delay(0.2, 0.5)
        
        typo_chance = 0.03 if make_typos else 0  # 3% typo chance per character
        
        i = 0
        while i < len(text):
            char = text[i]
            
            # Simulate typo
            if random.random() < typo_chance and i > 0 and i < len(text) - 1:
                # Common typo patterns
                typo_patterns = [
                    lambda: HumanSimulator._adjacent_key_typo(char),  # Adjacent key
                    lambda: char + char,  # Double character
                    lambda: '',  # Skip character
                    lambda: HumanSimulator._transposition_typo(text, i)  # Transposition
                ]
                
                typo = random.choice(typo_patterns)()
                
                if typo:
                    element.send_keys(typo)
                    HumanSimulator.typing_delay()
                    
                    # Realize mistake and correct
                    HumanSimulator.random_delay(0.3, 0.8)
                    
                    # Backspace to correct
                    for _ in range(len(typo)):
                        element.send_keys(Keys.BACKSPACE)
                        HumanSimulator.typing_delay()
                    
                    # Type correct character
                    element.send_keys(char)
                else:
                    element.send_keys(char)
            else:
                element.send_keys(char)
            
            # Variable typing speed
            if char == ' ':
                HumanSimulator.random_delay(0.1, 0.3)
            elif char in '.,!?;:':
                HumanSimulator.random_delay(0.2, 0.5)
            elif char == '\n':
                HumanSimulator.random_delay(0.3, 0.7)
            else:
                HumanSimulator.typing_delay()
            
            # Occasional pause (thinking)
            if random.random() < 0.02:  # 2% chance
                HumanSimulator.random_delay(0.5, 2.0)
            
            i += 1
    
    @staticmethod
    def _adjacent_key_typo(char: str) -> str:
        """Return adjacent key on QWERTY keyboard"""
        keyboard_adjacency = {
            'a': 'qwsz', 'b': 'vghn', 'c': 'xdfv', 'd': 'erfcxs',
            'e': 'wrd', 'f': 'rtgvcd', 'g': 'tyhbvf', 'h': 'yujnbg',
            'i': 'uok', 'j': 'uikmnh', 'k': 'iolmj', 'l': 'opk',
            'm': 'njk', 'n': 'bhjm', 'o': 'ipl', 'p': 'ol',
            'q': 'wa', 'r': 'etf', 's': 'awedxz', 't': 'ryfg',
            'u': 'yihj', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc',
            'y': 'tugh', 'z': 'asx'
        }
        
        if char.lower() in keyboard_adjacency:
            adjacent = keyboard_adjacency[char.lower()]
            return random.choice(adjacent)
        return char
    
    @staticmethod
    def _transposition_typo(text: str, index: int) -> str:
        """Swap current character with next one"""
        if index < len(text) - 1:
            return text[index + 1] + text[index]
        return text[index]
    
    @staticmethod
    def random_scroll(driver, scroll_type: Optional[str] = None) -> None:
        """
        Perform random scrolling patterns
        
        Args:
            driver: Selenium WebDriver instance
            scroll_type: Optional specific scroll pattern
        """
        scroll_patterns = {
            'smooth_down': HumanSimulator._smooth_scroll_down,
            'smooth_up': HumanSimulator._smooth_scroll_up,
            'quick_scan': HumanSimulator._quick_scan_scroll,
            'read_pause': HumanSimulator._read_pause_scroll,
            'back_check': HumanSimulator._back_check_scroll,
            'search_scan': HumanSimulator._search_scan_scroll
        }
        
        if scroll_type and scroll_type in scroll_patterns:
            pattern = scroll_patterns[scroll_type]
        else:
            pattern = random.choice(list(scroll_patterns.values()))
        
        try:
            pattern(driver)
        except Exception as e:
            logger.debug(f"Scroll simulation error: {e}")
    
    @staticmethod
    def _smooth_scroll_down(driver) -> None:
        """Smooth downward scrolling"""
        scroll_count = random.randint(3, 7)
        
        for _ in range(scroll_count):
            scroll_amount = random.randint(100, 400)
            duration = random.uniform(0.5, 1.5)
            
            driver.execute_script(f"""
                window.scrollBy({{
                    top: {scroll_amount},
                    behavior: 'smooth'
                }});
            """)
            
            time.sleep(duration)
    
    @staticmethod
    def _smooth_scroll_up(driver) -> None:
        """Smooth upward scrolling"""
        scroll_count = random.randint(2, 4)
        
        for _ in range(scroll_count):
            scroll_amount = random.randint(-300, -100)
            duration = random.uniform(0.3, 0.8)
            
            driver.execute_script(f"""
                window.scrollBy({{
                    top: {scroll_amount},
                    behavior: 'smooth'
                }});
            """)
            
            time.sleep(duration)
    
    @staticmethod
    def _quick_scan_scroll(driver) -> None:
        """Quick scanning scroll pattern"""
        # Scroll to different sections quickly
        positions = [0.3, 0.5, 0.7, 0.9]
        random.shuffle(positions)
        
        for pos in positions[:random.randint(2, 3)]:
            driver.execute_script(f"""
                window.scrollTo({{
                    top: document.body.scrollHeight * {pos},
                    behavior: 'smooth'
                }});
            """)
            time.sleep(random.uniform(0.8, 1.5))
    
    @staticmethod
    def _read_pause_scroll(driver) -> None:
        """Scroll with reading pauses"""
        current_position = driver.execute_script("return window.pageYOffset;")
        
        for _ in range(random.randint(3, 6)):
            # Scroll a readable chunk
            scroll_amount = random.randint(200, 500)
            current_position += scroll_amount
            
            driver.execute_script(f"""
                window.scrollTo({{
                    top: {current_position},
                    behavior: 'smooth'
                }});
            """)
            
            # Reading pause
            reading_time = random.uniform(2, 5)
            time.sleep(reading_time)
            
            # Occasionally scroll back a bit (re-reading)
            if random.random() < 0.2:
                driver.execute_script(f"""
                    window.scrollBy({{
                        top: {random.randint(-100, -50)},
                        behavior: 'smooth'
                    }});
                """)
                time.sleep(random.uniform(0.5, 1))
    
    @staticmethod
    def _back_check_scroll(driver) -> None:
        """Scroll down then back up (checking something)"""
        # Scroll down
        driver.execute_script("""
            window.scrollBy({
                top: 500,
                behavior: 'smooth'
            });
        """)
        time.sleep(random.uniform(1, 2))
        
        # Scroll back up partially
        driver.execute_script("""
            window.scrollBy({
                top: -200,
                behavior: 'smooth'
            });
        """)
        time.sleep(random.uniform(0.5, 1))
    
    @staticmethod
    def _search_scan_scroll(driver) -> None:
        """Scroll pattern for searching through results"""
        # Initial quick scan
        driver.execute_script("""
            window.scrollTo({
                top: 300,
                behavior: 'smooth'
            });
        """)
        time.sleep(random.uniform(0.5, 1))
        
        # Incremental scrolling through results
        for _ in range(random.randint(3, 5)):
            scroll_amount = random.randint(150, 300)
            driver.execute_script(f"""
                window.scrollBy({{
                    top: {scroll_amount},
                    behavior: 'auto'
                }});
            """)
            
            # Pause to "examine" results
            time.sleep(random.uniform(1, 2.5))
    
    @staticmethod
    def random_hover(driver, elements: List[WebElement]) -> None:
        """
        Randomly hover over elements
        
        Args:
            driver: Selenium WebDriver instance
            elements: List of elements to potentially hover over
        """
        if not elements:
            return
        
        # Select random subset of elements to hover
        num_hovers = min(len(elements), random.randint(1, 3))
        hover_elements = random.sample(elements, num_hovers)
        
        for element in hover_elements:
            try:
                HumanSimulator.human_mouse_movement(driver, element)
                HumanSimulator.random_delay(0.5, 1.5)
            except Exception as e:
                logger.debug(f"Hover simulation error: {e}")
    
    @staticmethod
    def simulate_reading_pattern(driver) -> None:
        """Simulate natural reading pattern on page"""
        # Start from top
        driver.execute_script("window.scrollTo(0, 0);")
        HumanSimulator.random_delay(0.5, 1)
        
        # Read in chunks
        viewport_height = driver.execute_script("return window.innerHeight;")
        total_height = driver.execute_script("return document.body.scrollHeight;")
        
        current_position = 0
        while current_position < total_height - viewport_height:
            # Read current viewport
            reading_time = random.uniform(2, 4)
            time.sleep(reading_time)
            
            # Scroll to next section
            scroll_amount = random.randint(int(viewport_height * 0.6), int(viewport_height * 0.9))
            current_position += scroll_amount
            
            driver.execute_script(f"""
                window.scrollTo({{
                    top: {current_position},
                    behavior: 'smooth'
                }});
            """)
            
            # Occasionally scroll back to re-read
            if random.random() < 0.15:
                HumanSimulator._smooth_scroll_up(driver)
                time.sleep(random.uniform(1, 2))
    
    @staticmethod
    def simulate_page_interaction(driver) -> None:
        """Simulate general page interaction patterns"""
        interactions = [
            lambda: HumanSimulator.random_scroll(driver),
            lambda: HumanSimulator.human_mouse_movement(driver),
            lambda: HumanSimulator.random_delay(1, 3),  # Just wait
            lambda: HumanSimulator.simulate_micro_movements(driver)
        ]
        
        # Perform 2-4 random interactions
        num_interactions = random.randint(2, 4)
        for _ in range(num_interactions):
            interaction = random.choice(interactions)
            interaction()
    
    @staticmethod
    def simulate_micro_movements(driver) -> None:
        """Simulate small mouse movements while reading"""
        for _ in range(random.randint(3, 7)):
            # Small random mouse movements
            offset_x = random.randint(-20, 20)
            offset_y = random.randint(-20, 20)
            
            try:
                ActionChains(driver).move_by_offset(offset_x, offset_y).perform()
            except:
                pass
            
            time.sleep(random.uniform(0.5, 1.5))