# Rate Limiter for LinkedIn Scraping

import json
import time
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Implement LinkedIn-specific rate limiting to avoid detection and account suspension
    """
    
    def __init__(self, config_file: str = "linkedin_rate_limit.json"):
        """
        Initialize rate limiter with conservative defaults
        
        Args:
            config_file: Path to JSON file for persistent state storage
        """
        self.config_file = Path(config_file)
        
        # Conservative limits based on LinkedIn's known restrictions
        self.limits = {
            # Daily limits
            "searches_per_day": 15,  # Very conservative for Sales Navigator
            "profiles_per_day": 30,  # LinkedIn typically allows 80-100, but we're being safe
            "connection_requests_per_day": 20,
            
            # Hourly limits
            "searches_per_hour": 3,
            "profiles_per_hour": 10,
            
            # Timing constraints
            "min_delay_between_searches": 45,  # seconds
            "max_delay_between_searches": 180,  # seconds
            "min_delay_between_profiles": 5,   # seconds
            "max_delay_between_profiles": 30,   # seconds
            
            # Backoff configuration
            "backoff_multiplier": 2.0,
            "max_backoff": 3600,  # 1 hour maximum backoff
            "jitter_range": 0.2,  # 20% jitter
            
            # Session limits
            "max_continuous_searches": 5,  # Force break after 5 continuous searches
            "break_duration_min": 300,  # 5 minutes minimum break
            "break_duration_max": 900,  # 15 minutes maximum break
        }
        
        # Load or initialize state
        self.state = self.load_state()
        
        # Track session information
        self.session_start = time.time()
        self.continuous_actions = 0
    
    def load_state(self) -> dict:
        """Load rate limiting state from persistent storage"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    state = json.load(f)
                    logger.info(f"Loaded rate limiter state: {state['daily_searches']} searches today")
                    return state
            except Exception as e:
                logger.error(f"Error loading rate limiter state: {e}")
        
        # Default state
        return {
            "daily_searches": 0,
            "daily_profiles": 0,
            "daily_connections": 0,
            "hourly_searches": 0,
            "hourly_profiles": 0,
            "last_search_time": 0,
            "last_profile_time": 0,
            "last_reset_date": str(datetime.now().date()),
            "last_hour_reset": datetime.now().hour,
            "consecutive_failures": 0,
            "total_failures_today": 0,
            "last_break_time": 0,
            "continuous_searches": 0,
            "blocked_until": 0,  # Timestamp when blocking expires
        }
    
    def save_state(self) -> None:
        """Save rate limiting state to persistent storage"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug("Rate limiter state saved")
        except Exception as e:
            logger.error(f"Error saving rate limiter state: {e}")
    
    def reset_if_needed(self) -> None:
        """Reset counters if new day or hour"""
        now = datetime.now()
        
        # Daily reset (LinkedIn resets at midnight PST)
        if str(now.date()) != self.state["last_reset_date"]:
            logger.info("Daily limit reset - new day started")
            self.state["daily_searches"] = 0
            self.state["daily_profiles"] = 0
            self.state["daily_connections"] = 0
            self.state["total_failures_today"] = 0
            self.state["last_reset_date"] = str(now.date())
            self.state["consecutive_failures"] = max(0, self.state["consecutive_failures"] - 1)
            self.continuous_actions = 0
        
        # Hourly reset
        if now.hour != self.state["last_hour_reset"]:
            logger.debug("Hourly limit reset")
            self.state["hourly_searches"] = 0
            self.state["hourly_profiles"] = 0
            self.state["last_hour_reset"] = now.hour
        
        self.save_state()
    
    def can_search(self) -> Tuple[bool, str]:
        """
        Check if we can perform a search
        
        Returns:
            Tuple of (can_search: bool, reason: str)
        """
        self.reset_if_needed()
        
        # Check if we're temporarily blocked
        if self.state["blocked_until"] > time.time():
            wait_time = self.state["blocked_until"] - time.time()
            return False, f"Temporarily blocked for {wait_time:.0f} seconds due to failures"
        
        # Check daily limit
        if self.state["daily_searches"] >= self.limits["searches_per_day"]:
            return False, f"Daily search limit reached ({self.limits['searches_per_day']} searches)"
        
        # Check hourly limit
        if self.state["hourly_searches"] >= self.limits["searches_per_hour"]:
            return False, f"Hourly search limit reached ({self.limits['searches_per_hour']} searches)"
        
        # Check if we need a break
        if self.state["continuous_searches"] >= self.limits["max_continuous_searches"]:
            time_since_break = time.time() - self.state["last_break_time"]
            required_break = random.uniform(
                self.limits["break_duration_min"],
                self.limits["break_duration_max"]
            )
            
            if time_since_break < required_break:
                wait_time = required_break - time_since_break
                return False, f"Break required. Please wait {wait_time:.0f} seconds"
            else:
                # Break completed, reset counter
                self.state["continuous_searches"] = 0
                self.state["last_break_time"] = time.time()
        
        # Check minimum delay between searches
        time_since_last = time.time() - self.state["last_search_time"]
        min_delay = self.limits["min_delay_between_searches"]
        
        # Apply exponential backoff if we have failures
        if self.state["consecutive_failures"] > 0:
            backoff_factor = self.limits["backoff_multiplier"] ** self.state["consecutive_failures"]
            min_delay = min(min_delay * backoff_factor, self.limits["max_backoff"])
        
        if time_since_last < min_delay:
            wait_time = min_delay - time_since_last
            return False, f"Please wait {wait_time:.0f} seconds before next search"
        
        # Check if we have too many failures
        if self.state["total_failures_today"] >= 10:
            return False, "Too many failures today. Please try again tomorrow"
        
        return True, "OK"
    
    def can_view_profile(self) -> Tuple[bool, str]:
        """
        Check if we can view a profile
        
        Returns:
            Tuple of (can_view: bool, reason: str)
        """
        self.reset_if_needed()
        
        # Check daily limit
        if self.state["daily_profiles"] >= self.limits["profiles_per_day"]:
            return False, f"Daily profile view limit reached ({self.limits['profiles_per_day']} profiles)"
        
        # Check hourly limit
        if self.state["hourly_profiles"] >= self.limits["profiles_per_hour"]:
            return False, f"Hourly profile view limit reached ({self.limits['profiles_per_hour']} profiles)"
        
        # Check minimum delay
        time_since_last = time.time() - self.state["last_profile_time"]
        min_delay = self.limits["min_delay_between_profiles"]
        
        if time_since_last < min_delay:
            wait_time = min_delay - time_since_last
            return False, f"Please wait {wait_time:.0f} seconds before next profile view"
        
        return True, "OK"
    
    def record_search(self, success: bool = True) -> None:
        """
        Record a search attempt
        
        Args:
            success: Whether the search was successful
        """
        self.state["daily_searches"] += 1
        self.state["hourly_searches"] += 1
        self.state["last_search_time"] = time.time()
        self.state["continuous_searches"] += 1
        
        if success:
            self.state["consecutive_failures"] = 0
            logger.info(f"Search recorded: {self.state['daily_searches']}/{self.limits['searches_per_day']} daily")
        else:
            self.state["consecutive_failures"] += 1
            self.state["total_failures_today"] += 1
            
            # Apply temporary block if too many consecutive failures
            if self.state["consecutive_failures"] >= 3:
                block_duration = min(
                    300 * (2 ** (self.state["consecutive_failures"] - 3)),
                    3600
                )
                self.state["blocked_until"] = time.time() + block_duration
                logger.warning(f"Too many failures. Blocking for {block_duration} seconds")
        
        self.save_state()
    
    def record_profile_view(self, success: bool = True) -> None:
        """
        Record a profile view
        
        Args:
            success: Whether the profile view was successful
        """
        self.state["daily_profiles"] += 1
        self.state["hourly_profiles"] += 1
        self.state["last_profile_time"] = time.time()
        
        if not success:
            self.state["total_failures_today"] += 1
        
        logger.debug(f"Profile view recorded: {self.state['daily_profiles']}/{self.limits['profiles_per_day']} daily")
        self.save_state()
    
    def get_delay(self, action_type: str = "search") -> float:
        """
        Get randomized delay with jitter for next action
        
        Args:
            action_type: Type of action ("search" or "profile")
        
        Returns:
            Delay in seconds
        """
        if action_type == "search":
            min_delay = self.limits["min_delay_between_searches"]
            max_delay = self.limits["max_delay_between_searches"]
        else:
            min_delay = self.limits["min_delay_between_profiles"]
            max_delay = self.limits["max_delay_between_profiles"]
        
        # Base delay with normal distribution
        mean = (min_delay + max_delay) / 2
        std_dev = (max_delay - min_delay) / 6
        base_delay = random.gauss(mean, std_dev)
        base_delay = max(min_delay, min(max_delay, base_delay))
        
        # Add jitter
        jitter_amount = base_delay * self.limits["jitter_range"]
        jitter = random.uniform(-jitter_amount, jitter_amount)
        
        # Apply exponential backoff if needed
        if self.state["consecutive_failures"] > 0:
            backoff_factor = self.limits["backoff_multiplier"] ** self.state["consecutive_failures"]
            base_delay = min(base_delay * backoff_factor, self.limits["max_backoff"])
        
        final_delay = max(min_delay, base_delay + jitter)
        
        logger.debug(f"Calculated delay: {final_delay:.1f} seconds (failures: {self.state['consecutive_failures']})")
        return final_delay
    
    def should_take_break(self) -> bool:
        """
        Determine if we should take a break
        
        Returns:
            True if break is recommended
        """
        # Check continuous actions
        if self.state["continuous_searches"] >= self.limits["max_continuous_searches"]:
            return True
        
        # Random break chance to appear more human
        if random.random() < 0.1:  # 10% chance
            return True
        
        # Break if we're approaching limits
        daily_usage = self.state["daily_searches"] / self.limits["searches_per_day"]
        if daily_usage > 0.7 and random.random() < 0.3:  # 30% chance when above 70% usage
            return True
        
        return False
    
    def get_break_duration(self) -> float:
        """
        Get recommended break duration
        
        Returns:
            Break duration in seconds
        """
        base_duration = random.uniform(
            self.limits["break_duration_min"],
            self.limits["break_duration_max"]
        )
        
        # Longer break if we have failures
        if self.state["consecutive_failures"] > 0:
            base_duration *= (1 + 0.5 * self.state["consecutive_failures"])
        
        return base_duration
    
    def get_status(self) -> dict:
        """
        Get current rate limiter status
        
        Returns:
            Dictionary with current limits and usage
        """
        self.reset_if_needed()
        
        return {
            "daily": {
                "searches": f"{self.state['daily_searches']}/{self.limits['searches_per_day']}",
                "profiles": f"{self.state['daily_profiles']}/{self.limits['profiles_per_day']}",
                "remaining_searches": self.limits["searches_per_day"] - self.state["daily_searches"],
                "remaining_profiles": self.limits["profiles_per_day"] - self.state["daily_profiles"],
            },
            "hourly": {
                "searches": f"{self.state['hourly_searches']}/{self.limits['searches_per_hour']}",
                "profiles": f"{self.state['hourly_profiles']}/{self.limits['profiles_per_hour']}",
            },
            "failures": {
                "consecutive": self.state["consecutive_failures"],
                "total_today": self.state["total_failures_today"],
            },
            "blocked": self.state["blocked_until"] > time.time(),
            "continuous_searches": self.state["continuous_searches"],
            "should_break": self.should_take_break()
        }
    
    def reset_session(self) -> None:
        """Reset session-specific counters"""
        self.state["continuous_searches"] = 0
        self.state["last_break_time"] = time.time()
        self.continuous_actions = 0
        self.save_state()
        logger.info("Session counters reset")
    
    def emergency_stop(self) -> None:
        """Emergency stop - block all actions for extended period"""
        self.state["blocked_until"] = time.time() + 3600  # Block for 1 hour
        self.state["consecutive_failures"] = 5  # Set high failure count
        self.save_state()
        logger.warning("Emergency stop activated - blocking for 1 hour")