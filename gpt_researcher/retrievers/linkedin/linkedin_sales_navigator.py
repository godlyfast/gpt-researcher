# LinkedIn Sales Navigator Retriever

import os
import json
import time
import logging
import platform
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import requests
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class LinkedInSalesNavigator:
    """
    LinkedIn Sales Navigator Retriever for searching leads and companies
    """
    
    def __init__(self, query, headers=None, topic="general", query_domains=None):
        """
        Initializes the LinkedInSalesNavigator object.
        
        Args:
            query (str): The search query string.
            headers (dict, optional): Additional headers with credentials. Defaults to None.
            topic (str, optional): The topic for the search. Defaults to "general".
            query_domains (list, optional): List of domains to include in the search. Defaults to None.
        """
        self.query = query
        self.headers = headers or {}
        self.topic = topic
        self.query_domains = query_domains
        
        # Get LinkedIn credentials
        self.username = self.get_credential("linkedin_username")
        self.password = self.get_credential("linkedin_password")
        self.session_token = self.get_credential("linkedin_session_token")
        
        # Remove quotes from session token if present
        if self.session_token:
            self.session_token = self.session_token.strip("'\"")
        
        # Check for saved cookies
        self.cookies_file = Path("linkedin_cookies.pkl")
        self.has_saved_session = self.cookies_file.exists()
        
        # Initialize browser options
        self.driver = None
        self.logged_in = False
        
    def get_credential(self, key):
        """
        Gets LinkedIn credentials from headers or environment variables
        
        Args:
            key (str): The credential key to retrieve
            
        Returns:
            str: The credential value
        """
        # First check headers
        value = self.headers.get(key)
        if value:
            return value
            
        # Then check environment variables
        env_key = key.upper()
        value = os.environ.get(env_key)
        if value:
            return value
            
        logger.warning(f"LinkedIn credential '{key}' not found. Please set it in headers or as environment variable {env_key}")
        return None
    
    def init_browser(self):
        """
        Initialize Chrome browser with appropriate options for Docker environment
        """
        if self.driver:
            return
            
        chrome_options = Options()
        
        # Essential Docker/container configurations
        chrome_options.add_argument("--headless=new")  # Use new headless mode
        chrome_options.add_argument("--no-sandbox")  # Required for Docker
        chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
        chrome_options.add_argument("--disable-gpu")  # GPU not available in Docker
        chrome_options.add_argument("--disable-software-rasterizer")
        
        # Additional stability options for containers
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Memory and performance optimizations
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        
        # Remove single-process as it can cause issues with some setups
        if os.environ.get('SINGLE_PROCESS_CHROME'):
            chrome_options.add_argument("--single-process")
        
        # Window and display settings
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        
        # Virtual display for Docker
        if os.environ.get('DISPLAY'):
            chrome_options.add_argument(f"--display={os.environ.get('DISPLAY')}")
        elif os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER'):
            chrome_options.add_argument("--display=:99")
        
        # User agent to avoid detection
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Disable images and unnecessary features for faster loading
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.cookies": 1,
            "profile.managed_default_content_settings.javascript": 1,
            "profile.managed_default_content_settings.plugins": 2,
            "profile.managed_default_content_settings.popups": 2,
            "profile.managed_default_content_settings.geolocation": 2,
            "profile.managed_default_content_settings.media_stream": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Set binary location for Docker environment
        # Check if running in Docker
        if os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER'):
            # Use the Chrome binary installed in Docker
            if platform.system() == "Linux":
                possible_chrome_paths = [
                    "/usr/bin/chromium",
                    "/usr/bin/chromium-browser",
                    "/usr/bin/google-chrome",
                    "/usr/bin/google-chrome-stable",
                    "/usr/local/bin/chrome",
                ]
                for chrome_path in possible_chrome_paths:
                    if os.path.exists(chrome_path):
                        chrome_options.binary_location = chrome_path
                        logger.info(f"Using Chrome binary at: {chrome_path}")
                        break
        
        try:
            # Try using the system chromedriver first (installed in Docker)
            if os.path.exists('/usr/bin/chromedriver'):
                try:
                    service = Service('/usr/bin/chromedriver')
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info("Chrome browser initialized with system chromedriver")
                except Exception as e:
                    logger.error(f"Failed to initialize with system chromedriver: {e}")
                    # Try webdriver-manager as fallback
                    try:
                        service = Service(ChromeDriverManager().install())
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                        logger.info("Chrome browser initialized with webdriver-manager")
                    except Exception as e2:
                        logger.error(f"Failed with both webdriver-manager and system driver: {e2}")
                        raise
            else:
                # Try webdriver-manager
                try:
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info("Chrome browser initialized with webdriver-manager")
                except Exception as e:
                    logger.error(f"Failed with webdriver-manager: {e}")
                    # Last resort - try without service
                    try:
                        self.driver = webdriver.Chrome(options=chrome_options)
                        logger.info("Chrome browser initialized without service")
                    except Exception as e2:
                        logger.error(f"Failed all initialization attempts: {e2}")
                        raise
                
            # Set timeouts
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome browser: {e}")
            logger.error(f"Chrome options: {chrome_options.arguments}")
            # Don't raise exception, return gracefully
            logger.warning("LinkedIn retriever will return empty results due to Chrome initialization failure")
            self.driver = None
    
    def login(self):
        """
        Login to LinkedIn Sales Navigator using session token, saved session, or credentials
        """
        if self.logged_in:
            return True
            
        try:
            self.init_browser()
            
            # Check if browser initialization failed
            if not self.driver:
                logger.warning("Browser initialization failed, cannot login to LinkedIn")
                return False
            
            # Try to use session token first (highest priority)
            if self.session_token:
                logger.info("Found LinkedIn session token in environment, attempting to use it...")
                if self._load_session_token():
                    logger.info("Successfully logged in using session token")
                    self.logged_in = True
                    return True
                else:
                    logger.warning("Session token failed, trying other methods...")
            
            # Try to use saved session file
            if self.has_saved_session:
                logger.info("Found saved LinkedIn session file, attempting to use it...")
                if self._load_saved_session():
                    logger.info("Successfully logged in using saved session")
                    self.logged_in = True
                    return True
                else:
                    logger.warning("Saved session failed, falling back to credential login")
            
            # Fall back to credential login if no saved session or it failed
            if not self.username or not self.password:
                logger.error("LinkedIn credentials not configured and no valid saved session")
                logger.info("Tip: Run 'python linkedin_manual_login.py' to create a saved session")
                return False
            
            # Log credentials info (masked)
            logger.info(f"Attempting login with username: {self.username}")
            logger.info(f"Password length: {len(self.password)}")
            logger.info(f"Password (repr for debugging): {repr(self.password)}")
            
            # Navigate to LinkedIn login page
            logger.info("Navigating to LinkedIn login page...")
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(3)
            
            # Log current page state
            logger.info(f"Current URL before login: {self.driver.current_url}")
            logger.info(f"Page title: {self.driver.title}")
            
            # Enter credentials
            logger.info("Entering username...")
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            username_field.clear()
            username_field.send_keys(self.username)
            
            logger.info("Entering password...")
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Take screenshot before clicking login
            try:
                self.driver.save_screenshot("/tmp/linkedin_before_login.png")
                logger.info("Screenshot saved: /tmp/linkedin_before_login.png")
            except:
                pass
            
            # Click login button
            logger.info("Clicking login button...")
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for login to complete and handle various redirect scenarios
            return self._verify_login_success()
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def _verify_login_success(self, max_attempts=3):
        """
        Verify login success by checking for various LinkedIn redirect scenarios
        
        Args:
            max_attempts (int): Maximum number of verification attempts
            
        Returns:
            bool: True if login successful, False otherwise
        """
        for attempt in range(max_attempts):
            try:
                # Wait a bit for redirect to complete
                time.sleep(5)
                current_url = self.driver.current_url.lower()
                logger.info(f"Login attempt {attempt + 1}: Current URL is {current_url}")
                
                # Take screenshot after login attempt
                try:
                    self.driver.save_screenshot(f"/tmp/linkedin_after_login_{attempt}.png")
                    logger.info(f"Screenshot saved: /tmp/linkedin_after_login_{attempt}.png")
                except:
                    pass
                
                # Check for successful login indicators
                success_indicators = [
                    "feed",           # Main LinkedIn feed
                    "sales",          # Sales Navigator
                    "/in/",           # Profile page (/in/username)
                    "mynetwork",      # Network page
                    "messaging",      # Messages
                    "jobs",           # Jobs page
                    "notifications"   # Notifications
                ]
                
                if any(indicator in current_url for indicator in success_indicators):
                    self.logged_in = True
                    logger.info(f"Successfully logged in to LinkedIn (redirected to {current_url})")
                    return True
                
                # Check for challenge/verification pages that require user action
                challenge_indicators = [
                    "checkpoint/challenge",    # Security verification
                    "check/add-phone",        # Phone verification
                    "add-phone",              # Phone number request
                    "challenge",              # General challenge
                    "verify",                 # Verification page
                ]
                
                if any(indicator in current_url for indicator in challenge_indicators):
                    logger.warning(f"LinkedIn requires additional verification: {current_url}")
                    logger.warning("Please complete the verification manually or use a different account")
                    return False
                
                # Check if still on login page with errors
                if "/login" in current_url:
                    # Look for error messages
                    try:
                        # More comprehensive error selectors
                        error_selectors = [
                            ".form__label--error",
                            ".alert-content",
                            ".error",
                            "[data-test-id='error-message']",
                            "#error-for-password",
                            "#error-for-username",
                            ".login__form_action_container .error"
                        ]
                        
                        error_messages = []
                        for selector in error_selectors:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for elem in elements:
                                if elem.text.strip():
                                    error_messages.append(elem.text.strip())
                        
                        if error_messages:
                            logger.error(f"Login failed with errors: {'; '.join(error_messages)}")
                            # Try to get full page source for debugging
                            try:
                                with open('/tmp/linkedin_error_page.html', 'w') as f:
                                    f.write(self.driver.page_source)
                                logger.info("Full page source saved to /tmp/linkedin_error_page.html")
                            except:
                                pass
                            return False
                    except Exception as e:
                        logger.debug(f"Error checking for error messages: {e}")
                    
                    # If still on login page but no specific error, might need more time
                    logger.warning(f"Still on login page (attempt {attempt + 1}), waiting longer...")
                    if attempt < max_attempts - 1:
                        time.sleep(5)
                        continue
                    else:
                        logger.error("Login failed - remained on login page")
                        return False
                
                # Check for other common redirect patterns
                if "linkedin.com" in current_url and "/uas/login" not in current_url:
                    # We're on a LinkedIn page that's not the login page
                    # This might be a successful login to an unexpected page
                    logger.info(f"Login appears successful - redirected to LinkedIn page: {current_url}")
                    self.logged_in = True
                    return True
                
                # If we get here, we're in an unexpected state
                logger.warning(f"Unexpected redirect during login: {current_url}")
                if attempt < max_attempts - 1:
                    time.sleep(2)
                    continue
                    
            except Exception as e:
                logger.error(f"Error during login verification (attempt {attempt + 1}): {e}")
                if attempt < max_attempts - 1:
                    time.sleep(2)
                    continue
        
        logger.error("Login verification failed after all attempts")
        return False
    
    def _load_session_token(self):
        """
        Load session token from environment and apply it to the browser
        
        Returns:
            bool: True if session loaded successfully, False otherwise
        """
        try:
            # Navigate to LinkedIn first (required for cookies to work)
            self.driver.get("https://www.linkedin.com")
            time.sleep(2)
            
            # Create the li_at cookie with the session token
            cookie = {
                'name': 'li_at',
                'value': self.session_token,
                'domain': '.linkedin.com',
                'path': '/',
                'secure': True,
                'httpOnly': True
            }
            
            logger.info(f"Setting li_at cookie with token: {self.session_token[:30]}...")
            
            # Add the cookie to the browser
            self.driver.add_cookie(cookie)
            
            # Also add other necessary cookies for LinkedIn
            # Add JSESSIONID if needed
            jsessionid_cookie = {
                'name': 'JSESSIONID',
                'value': f'"ajax:{int(time.time()*1000)}"',
                'domain': '.www.linkedin.com',
                'path': '/',
                'secure': True,
                'httpOnly': True
            }
            self.driver.add_cookie(jsessionid_cookie)
            
            # Refresh the page to apply cookies
            logger.info("Refreshing page to apply session token...")
            self.driver.refresh()
            time.sleep(3)
            
            # Check if we're logged in by navigating to feed
            self.driver.get("https://www.linkedin.com/feed/")
            time.sleep(3)
            
            current_url = self.driver.current_url
            logger.info(f"Current URL after session token: {current_url}")
            
            # Check if we're successfully logged in
            if "feed" in current_url or "sales" in current_url:
                logger.info("✅ Successfully authenticated with session token!")
                return True
            elif "login" in current_url or "checkpoint" in current_url:
                logger.warning("Session token appears to be invalid or expired")
                return False
            else:
                logger.info(f"Unexpected URL after session token: {current_url}")
                # Try to verify by checking for profile elements
                try:
                    # Check for common logged-in elements
                    self.driver.find_element(By.CSS_SELECTOR, "[data-control-name='nav.settings']")
                    logger.info("Found profile settings - appears to be logged in")
                    return True
                except:
                    logger.warning("Could not verify login status")
                    return False
                    
        except Exception as e:
            logger.error(f"Error loading session token: {e}")
            return False
    
    def _load_saved_session(self):
        """
        Load saved cookies from file and apply them to the browser
        
        Returns:
            bool: True if session loaded successfully, False otherwise
        """
        try:
            # Navigate to LinkedIn first (required for cookies to work)
            self.driver.get("https://www.linkedin.com")
            time.sleep(2)
            
            # Load cookies from file
            with open(self.cookies_file, 'rb') as file:
                cookies = pickle.load(file)
            
            logger.info(f"Loading {len(cookies)} saved cookies...")
            
            # Add each cookie to the browser
            for cookie in cookies:
                # Remove sameSite attribute if present (can cause issues)
                if 'sameSite' in cookie:
                    del cookie['sameSite']
                # Remove expiry if it's causing issues
                if 'expiry' in cookie:
                    cookie['expiry'] = int(cookie['expiry'])
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Could not add cookie {cookie.get('name', 'unknown')}: {e}")
            
            # Navigate to Sales Navigator to test the session
            logger.info("Testing saved session...")
            self.driver.get("https://www.linkedin.com/sales/home")
            time.sleep(3)
            
            # Check if we're logged in
            current_url = self.driver.current_url.lower()
            if "sales" in current_url or "feed" in current_url or "/in/" in current_url:
                logger.info(f"Saved session is valid! Current URL: {current_url}")
                return True
            else:
                logger.warning(f"Saved session might be expired. Current URL: {current_url}")
                return False
                
        except FileNotFoundError:
            logger.warning(f"Cookie file not found: {self.cookies_file}")
            return False
        except Exception as e:
            logger.error(f"Error loading saved session: {e}")
            return False
    
    async def search_leads(self, max_results=10):
        """
        Search for leads on LinkedIn Sales Navigator using progressive fallback
        
        Args:
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of lead information, None if rate limited
        """
        if not self.login():
            logger.error("Failed to login to LinkedIn Sales Navigator")
            # Return None to indicate login failure (for fallback to Tavily)
            return None
            
        try:
            # Parse the query using new smart approach
            filters = self.parse_query_filters(self.query)
            logger.info(f"Parsed query filters: {filters}")
            
            # Use progressive fallback search
            results = await self.search_with_progressive_fallback(filters, "people", max_results)
            
            logger.info(f"LinkedIn Sales Navigator lead search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Lead search failed: {e}")
            return []
    
    async def search_companies(self, max_results=10):
        """
        Search for companies on LinkedIn Sales Navigator using progressive fallback
        
        Args:
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of company information, None if rate limited
        """
        if not self.login():
            logger.error("Failed to login to LinkedIn Sales Navigator")
            # Return None to indicate login failure (for fallback to Tavily)
            return None
            
        try:
            # Parse the query using new smart approach
            filters = self.parse_query_filters(self.query)
            logger.info(f"Parsed query filters: {filters}")
            
            # Use progressive fallback search
            results = await self.search_with_progressive_fallback(filters, "companies", max_results)
            
            logger.info(f"LinkedIn Sales Navigator company search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Company search failed: {e}")
            return []
    
    def parse_intent(self, query: str) -> dict:
        """
        Parse the query to extract semantic intent for LinkedIn search optimization
        
        Args:
            query (str): The search query in any language
            
        Returns:
            dict: Parsed intent with roles, skills, locations, etc.
        """
        intent = {
            "roles": [],
            "skills": [],
            "locations": [],
            "company_criteria": {},
            "seniority": [],
            "keywords_raw": query.lower()
        }
        
        # Extract roles (English and Ukrainian patterns)
        role_patterns = {
            "javascript developer": ["javascript", "js", "frontend", "backend", "fullstack", "розробник"],
            "cto": ["cto", "chief technology", "tech lead", "технічний директор"],
            "ceo": ["ceo", "chief executive", "founder", "засновник", "директор"],
            "developer": ["developer", "engineer", "programmer", "розробник", "програміст"],
            "manager": ["manager", "менеджер", "керівник"]
        }
        
        for role, patterns in role_patterns.items():
            if any(pattern in intent["keywords_raw"] for pattern in patterns):
                intent["roles"].append(role)
        
        # Extract technical skills
        skill_patterns = {
            "JavaScript": ["javascript", "js", "node", "react", "vue", "angular"],
            "Python": ["python", "django", "flask"],
            "Java": ["java", "spring"],
            "TypeScript": ["typescript", "ts"]
        }
        
        for skill, patterns in skill_patterns.items():
            if any(pattern in intent["keywords_raw"] for pattern in patterns):
                intent["skills"].append(skill)
        
        # Extract locations (support multiple languages)
        location_patterns = {
            "Valencia": ["valencia", "валенсії", "валенсія"],
            "Barcelona": ["barcelona", "барселоні", "барселона"],
            "Madrid": ["madrid", "мадрид"],
            "Spain": ["spain", "іспанії", "іспанія"]
        }
        
        for location, patterns in location_patterns.items():
            if any(pattern in intent["keywords_raw"] for pattern in patterns):
                intent["locations"].append(location)
        
        # Extract company criteria
        if any(term in intent["keywords_raw"] for term in ["100", "співробітників", "employees"]):
            intent["company_criteria"]["size"] = "1-100"
        elif any(term in intent["keywords_raw"] for term in ["startup", "стартап"]):
            intent["company_criteria"]["size"] = "1-50"
            
        if any(term in intent["keywords_raw"] for term in ["funded", "investment", "інвестиції"]):
            intent["company_criteria"]["funding"] = "funded"
            
        # Extract seniority (decision makers)
        if any(term in intent["keywords_raw"] for term in ["лпр", "decision maker", "ceo", "cto", "founder"]):
            intent["seniority"].extend(["owner", "partner", "cxo", "vp", "director"])
            
        return intent
    
    def generate_optimized_keywords(self, intent: dict) -> str:
        """
        Generate LinkedIn-optimized Boolean search keywords
        
        Args:
            intent (dict): Parsed intent from query
            
        Returns:
            str: Optimized keyword string with Boolean operators
        """
        keyword_parts = []
        
        # Process roles (max 2 for effectiveness)
        if intent["roles"]:
            roles = intent["roles"][:2]  # Limit to 2 most relevant roles
            role_string = ' OR '.join(f'"{role}"' for role in roles)
            keyword_parts.append(f"({role_string})")
        
        # Process skills (max 2 primary skills)
        if intent["skills"]:
            skills = intent["skills"][:2]  # Focus on primary skills
            skills_string = ' OR '.join(intent["skills"][:2])
            if keyword_parts:  # Combine with roles using AND
                keyword_parts.append(f"AND ({skills_string})")
            else:
                keyword_parts.append(skills_string)
        
        # If no structured keywords found, extract simple terms
        if not keyword_parts:
            # Fallback: extract 1-2 key terms from original query
            simple_terms = self._extract_simple_keywords(intent["keywords_raw"])
            return ' OR '.join(simple_terms[:2])
            
        return ' '.join(keyword_parts)
    
    def _extract_simple_keywords(self, query: str) -> list:
        """
        Extract simple keywords as fallback when structured parsing fails
        
        Args:
            query (str): Raw query string
            
        Returns:
            list: Simple keyword terms
        """
        # Remove common words and extract meaningful terms
        stop_words = {'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                      'склади', 'будь', 'ласка', 'список', 'які', 'мають', 'шукають'}
        
        words = query.lower().split()
        keywords = []
        
        for word in words:
            # Clean word and check if meaningful
            clean_word = ''.join(c for c in word if c.isalnum())
            if len(clean_word) > 2 and clean_word not in stop_words:
                keywords.append(clean_word)
                
        return keywords
    
    def build_native_filters(self, intent: dict) -> dict:
        """
        Build LinkedIn Sales Navigator native filters from intent
        
        Args:
            intent (dict): Parsed intent
            
        Returns:
            dict: Native LinkedIn filter parameters
        """
        filters = {}
        
        # Location filter (geographic targeting)
        if intent["locations"]:
            filters["geoIncluded"] = ','.join(intent["locations"])
        
        # Company size filter
        if intent["company_criteria"].get("size"):
            size_map = {
                "1-50": "B",   # 1-50 employees
                "1-100": "C",  # 51-200 employees (closest to 1-100)
                "51-200": "D", 
                "201-500": "E"
            }
            size = intent["company_criteria"]["size"]
            if size in size_map:
                filters["companySize"] = size_map[size]
        
        # Seniority filter (for decision makers)
        if intent["seniority"]:
            filters["seniorityIncluded"] = ','.join(intent["seniority"])
        
        # Function filter (for technical roles)
        if any(role in intent["roles"] for role in ["javascript developer", "developer"]):
            filters["functionIncluded"] = "engineering"
            
        # Current job title only (best practice)
        filters["currentJobTitle"] = "true"
        
        return filters
    
    def parse_query_filters(self, query):
        """
        Main method to parse query using new smart approach
        
        Args:
            query (str): The search query
            
        Returns:
            dict: Optimized filters with keywords and native LinkedIn filters
        """
        # Step 1: Parse semantic intent
        intent = self.parse_intent(query)
        
        # Step 2: Generate optimized keywords
        optimized_keywords = self.generate_optimized_keywords(intent)
        
        # Step 3: Build native filters
        native_filters = self.build_native_filters(intent)
        
        # Return combined result
        return {
            "keywords": optimized_keywords,
            "native_filters": native_filters,
            "intent": intent  # Keep for debugging and fallback
        }
    
    def build_sales_nav_url(self, filters, search_type="people"):
        """
        Build LinkedIn Sales Navigator search URL with optimized filters
        
        Args:
            filters (dict): Search filters with keywords and native_filters
            search_type (str): Type of search (people or companies)
            
        Returns:
            str: The search URL
        """
        base_url = f"https://www.linkedin.com/sales/search/{search_type}"
        params = []
        
        # Add optimized keywords
        if filters.get("keywords"):
            params.append(f"keywords={quote_plus(filters['keywords'])}")
        
        # Add native LinkedIn filters
        native_filters = filters.get("native_filters", {})
        
        for filter_key, filter_value in native_filters.items():
            if filter_value:
                if filter_key == "currentJobTitle" and filter_value == "true":
                    params.append("currentJobTitle=true")
                else:
                    params.append(f"{filter_key}={quote_plus(str(filter_value))}")
            
        # Combine URL with proper parameter separation
        if params:
            return f"{base_url}?{'&'.join(params)}"
        return base_url
    
    async def search_with_progressive_fallback(self, filters, search_type="people", max_results=10):
        """
        Implement progressive fallback search strategy for better results
        
        Args:
            filters (dict): Parsed filters with keywords and native_filters
            search_type (str): Type of search (people or companies)
            max_results (int): Maximum results to return
            
        Returns:
            list: Search results
        """
        logger.info(f"Starting progressive search with filters: {filters}")
        
        # Strategy 1: Full optimized search
        try:
            search_url = self.build_sales_nav_url(filters, search_type)
            logger.info(f"Trying optimized search: {search_url}")
            
            self.driver.get(search_url)
            time.sleep(5)
            
            results = self._extract_search_results(search_type, max_results)
            
            if len(results) > 0:
                logger.info(f"✅ Optimized search successful: {len(results)} results")
                return results
            else:
                logger.warning("❌ Optimized search returned 0 results, trying fallback...")
                
        except Exception as e:
            logger.error(f"Optimized search failed: {e}")
        
        # Add delay between strategies to avoid rate limiting
        time.sleep(15)
        
        # Strategy 2: Simplified keywords search
        try:
            intent = filters.get("intent", {})
            simple_keywords = self._extract_simple_keywords(intent.get("keywords_raw", self.query))
            
            if simple_keywords:
                simplified_filters = {
                    "keywords": " OR ".join(simple_keywords[:2]),  # Max 2 simple terms
                    "native_filters": {
                        "geoIncluded": filters.get("native_filters", {}).get("geoIncluded", ""),
                        "currentJobTitle": "true"
                    }
                }
                
                search_url = self.build_sales_nav_url(simplified_filters, search_type)
                logger.info(f"Trying simplified search: {search_url}")
                
                self.driver.get(search_url)
                time.sleep(10)  # Increased delay to avoid rate limiting
                
                results = self._extract_search_results(search_type, max_results)
                
                if len(results) > 0:
                    logger.info(f"✅ Simplified search successful: {len(results)} results")
                    return results
                else:
                    logger.warning("❌ Simplified search returned 0 results, trying minimal...")
                    
        except Exception as e:
            logger.error(f"Simplified search failed: {e}")
        
        # Add delay between strategies to avoid rate limiting
        time.sleep(15)
        
        # Strategy 3: Minimal search (location only)
        try:
            minimal_filters = {
                "keywords": simple_keywords[0] if simple_keywords else "developer",
                "native_filters": {
                    "geoIncluded": filters.get("native_filters", {}).get("geoIncluded", ""),
                }
            }
            
            search_url = self.build_sales_nav_url(minimal_filters, search_type)
            logger.info(f"Trying minimal search: {search_url}")
            
            self.driver.get(search_url)
            time.sleep(5)
            
            results = self._extract_search_results(search_type, max_results)
            
            if len(results) > 0:
                logger.info(f"✅ Minimal search successful: {len(results)} results")
                return results
            else:
                logger.warning("❌ Minimal search returned 0 results, trying OR broadening...")
                
        except Exception as e:
            logger.error(f"Minimal search failed: {e}")
        
        # Add delay between strategies to avoid rate limiting
        time.sleep(15)
        
        # Strategy 4: OR-based broadening for AI post-processing
        try:
            intent = filters.get("intent", {})
            or_keywords = self._create_or_broadening_query(intent)
            or_filters = self._create_or_broadening_filters(intent)
            
            broadening_filters = {
                "keywords": or_keywords,
                "native_filters": or_filters
            }
            
            search_url = self.build_sales_nav_url(broadening_filters, search_type)
            logger.info(f"🎯 Trying OR broadening search: {search_url}")
            logger.info(f"OR Keywords: {or_keywords}")
            
            self.driver.get(search_url)
            time.sleep(5)
            
            results = self._extract_search_results(search_type, max_results * 2)  # Get more results for AI filtering
            
            if len(results) > 0:
                logger.info(f"✅ OR broadening successful: {len(results)} results for AI post-processing")
                # Add metadata to indicate these results need AI filtering
                for result in results:
                    result["ai_filter_needed"] = True
                    result["original_criteria"] = {
                        "roles": intent.get("roles", []),
                        "locations": intent.get("locations", []),
                        "company_criteria": intent.get("company_criteria", {}),
                        "seniority": intent.get("seniority", []),
                        "skills": intent.get("skills", [])
                    }
                return results
            else:
                logger.warning("❌ OR broadening also returned 0 results")
                
        except Exception as e:
            logger.error(f"OR broadening search failed: {e}")
        
        # Add delay between strategies to avoid rate limiting
        time.sleep(15)
        
        # Strategy 5: Ultra-broad location-only search for maximum data
        try:
            locations = filters.get("intent", {}).get("locations", [])
            if locations:
                ultra_broad_filters = {
                    "keywords": "developer OR manager OR founder",
                    "native_filters": {
                        "geoIncluded": ",".join(locations),
                        "currentJobTitle": "true"
                    }
                }
                
                search_url = self.build_sales_nav_url(ultra_broad_filters, search_type)
                logger.info(f"🌍 Trying ultra-broad location search: {search_url}")
                
                self.driver.get(search_url)
                time.sleep(10)  # Increased delay to avoid rate limiting
                
                results = self._extract_search_results(search_type, max_results * 3)  # Even more results
                
                if len(results) > 0:
                    logger.info(f"✅ Ultra-broad search successful: {len(results)} results for AI post-processing")
                    for result in results:
                        result["ai_filter_needed"] = True
                        result["search_strategy"] = "ultra_broad"
                        result["original_criteria"] = intent
                    return results
                    
        except Exception as e:
            logger.error(f"Ultra-broad search failed: {e}")
        
        # If all strategies fail, return empty results
        logger.error("🚨 All progressive search strategies failed")
        return []
    
    def _create_or_broadening_query(self, intent: dict) -> str:
        """
        Create OR-based broadening query for better AI post-processing
        
        Args:
            intent (dict): Parsed intent
            
        Returns:
            str: OR-based broadening query
        """
        or_parts = []
        
        # Add roles with OR
        if intent.get("roles"):
            roles_or = ' OR '.join(f'"{role}"' for role in intent["roles"][:3])
            or_parts.append(f"({roles_or})")
        
        # Add skills with OR
        if intent.get("skills"):
            skills_or = ' OR '.join(intent["skills"][:3])
            or_parts.append(f"({skills_or})")
        
        # Add seniority terms with OR
        if intent.get("seniority"):
            seniority_terms = ["founder", "CEO", "CTO", "director", "manager"]
            seniority_or = ' OR '.join(seniority_terms[:3])
            or_parts.append(f"({seniority_or})")
        
        # Add company-related terms
        if intent.get("company_criteria", {}).get("funding"):
            funding_terms = ["startup", "funded", "investment"]
            funding_or = ' OR '.join(funding_terms)
            or_parts.append(f"({funding_or})")
        
        # If no specific parts, use general terms
        if not or_parts:
            return "developer OR engineer OR founder OR manager"
        
        # Combine with OR (not AND) for maximum results
        return ' OR '.join(or_parts[:3])  # Limit to 3 major OR groups
    
    def _create_or_broadening_filters(self, intent: dict) -> dict:
        """
        Create broadened native filters for OR search
        
        Args:
            intent (dict): Parsed intent
            
        Returns:
            dict: Broadened native filters
        """
        filters = {}
        
        # Keep location - this is usually the most important
        if intent.get("locations"):
            filters["geoIncluded"] = ','.join(intent["locations"])
        
        # Remove or broaden company size (allow more companies)
        # Don't apply company size filter for broader results
        
        # Keep current job title filter
        filters["currentJobTitle"] = "true"
        
        # Don't apply function filter for broader results
        # This allows us to find founders/managers in any function
        
        return filters
    
    def _extract_search_results(self, search_type, max_results):
        """
        Extract search results from the current page
        
        Args:
            search_type (str): Type of search (people or companies)
            max_results (int): Maximum results to extract
            
        Returns:
            list: Extracted results
        """
        results = []
        
        try:
            if search_type == "people":
                # Look for lead elements
                lead_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-anonymize='person-name']")[:max_results]
                
                for element in lead_elements:
                    try:
                        # Get parent container
                        container = element.find_element(By.XPATH, "./ancestor::li[contains(@class, 'reusable-search__result-container')]")
                        
                        # Extract lead information
                        name = element.text if element.text else "N/A"
                        
                        # Try to get title and company
                        try:
                            title_element = container.find_element(By.CSS_SELECTOR, "[data-anonymize='title']")
                            title = title_element.text if title_element.text else "N/A"
                        except:
                            title = "N/A"
                        
                        try:
                            company_element = container.find_element(By.CSS_SELECTOR, "[data-anonymize='company-name']")
                            company = company_element.text if company_element.text else "N/A"
                        except:
                            company = "N/A"
                        
                        # Get profile URL
                        try:
                            link_element = container.find_element(By.CSS_SELECTOR, "a[href*='/sales/lead/']")
                            profile_url = link_element.get_attribute("href") if link_element else ""
                        except:
                            profile_url = ""
                        
                        # Get location if available
                        try:
                            location_element = container.find_element(By.CSS_SELECTOR, "[data-anonymize='location']")
                            location = location_element.text if location_element.text else "N/A"
                        except:
                            location = "N/A"
                        
                        results.append({
                            "name": name,
                            "title": title,
                            "company": company,
                            "location": location,
                            "profile_url": profile_url,
                            "source": "LinkedIn Sales Navigator"
                        })
                        
                    except Exception as e:
                        logger.debug(f"Error extracting lead data: {e}")
                        continue
            
            else:  # companies
                company_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-anonymize='company-name']")[:max_results]
                
                for element in company_elements:
                    try:
                        # Get parent container
                        container = element.find_element(By.XPATH, "./ancestor::li[contains(@class, 'reusable-search__result-container')]")
                        
                        # Extract company information
                        name = element.text if element.text else "N/A"
                        
                        # Try to get industry and size
                        try:
                            industry_element = container.find_element(By.CSS_SELECTOR, "[data-anonymize='industry']")
                            industry = industry_element.text if industry_element.text else "N/A"
                        except:
                            industry = "N/A"
                        
                        try:
                            size_element = container.find_element(By.CSS_SELECTOR, "[data-anonymize='company-size']")
                            size = size_element.text if size_element.text else "N/A"
                        except:
                            size = "N/A"
                        
                        # Get company URL
                        try:
                            link_element = container.find_element(By.CSS_SELECTOR, "a[href*='/sales/company/']")
                            company_url = link_element.get_attribute("href") if link_element else ""
                        except:
                            company_url = ""
                        
                        # Get location
                        try:
                            location_element = container.find_element(By.CSS_SELECTOR, "[data-anonymize='location']")
                            location = location_element.text if location_element.text else "N/A"
                        except:
                            location = "N/A"
                        
                        results.append({
                            "name": name,
                            "industry": industry,
                            "size": size,
                            "location": location,
                            "company_url": company_url,
                            "source": "LinkedIn Sales Navigator"
                        })
                        
                    except Exception as e:
                        logger.debug(f"Error extracting company data: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error extracting search results: {e}")
        
        return results
    
    def search(self, max_results=10):
        """
        Main search method that determines whether to search for leads or companies
        Uses the new progressive fallback approach for better results
        
        Args:
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of search results formatted for GPT Researcher
        """
        try:
            logger.info(f"Starting LinkedIn Sales Navigator search for: {self.query}")
            
            # Since we can't use async in the main retriever interface, we need to run the async methods
            import asyncio
            
            # Create event loop if it doesn't exist
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Determine search type based on query
            if any(term in self.query.lower() for term in ["company", "companies", "startup", "стартап", "компанії"]):
                raw_results = loop.run_until_complete(self.search_companies(max_results))
                search_type = "companies"
                logger.info(f"Detected company search type")
            else:
                raw_results = loop.run_until_complete(self.search_leads(max_results))
                search_type = "leads"
                logger.info(f"Detected lead search type")
            
            # Format results for GPT Researcher
            formatted_results = []
            for result in raw_results:
                if search_type == "companies":
                    body = f"Company: {result.get('name', 'N/A')}\n"
                    body += f"Industry: {result.get('industry', 'N/A')}\n"
                    body += f"Size: {result.get('size', 'N/A')}\n"
                    body += f"Location: {result.get('location', 'N/A')}\n"
                    href = result.get('company_url', '')
                else:
                    body = f"Name: {result.get('name', 'N/A')}\n"
                    body += f"Title: {result.get('title', 'N/A')}\n"
                    body += f"Company: {result.get('company', 'N/A')}\n"
                    body += f"Location: {result.get('location', 'N/A')}\n"
                    href = result.get('profile_url', '')
                    
                # Check if this result needs AI filtering
                ai_filter_info = ""
                if result.get("ai_filter_needed"):
                    original_criteria = result.get("original_criteria", {})
                    ai_filter_info += "\n[AI FILTER NEEDED]\n"
                    ai_filter_info += f"Original Criteria: {original_criteria}\n"
                    ai_filter_info += "Please evaluate if this profile matches the original search criteria.\n"
                
                formatted_results.append({
                    "href": href,
                    "body": body + ai_filter_info
                })
            
            logger.info(f"🎯 LinkedIn Sales Navigator search completed: {len(formatted_results)} formatted results")
            
            # Log sample result for debugging
            if formatted_results:
                logger.info(f"Sample result: {formatted_results[0]['body'][:100]}...")
            else:
                logger.warning("⚠️ No results found with progressive search strategy")
                
            return formatted_results
            
        except Exception as e:
            logger.error(f"LinkedIn Sales Navigator search failed: {e}")
            import traceback
            logger.error(f"Full error traceback: {traceback.format_exc()}")
            return []
        finally:
            # Clean up browser
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("LinkedIn browser session closed")
                except Exception as cleanup_error:
                    logger.warning(f"Error cleaning up browser: {cleanup_error}")
                finally:
                    self.driver = None
                    self.logged_in = False