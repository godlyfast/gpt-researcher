# LinkedIn Stealth Browser with Anti-Detection Measures

import random
import time
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os
import platform

logger = logging.getLogger(__name__)


class StealthBrowser:
    """Enhanced browser with anti-detection measures for LinkedIn scraping"""
    
    def __init__(self):
        self.driver = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        ]
        
        self.window_sizes = [
            (1920, 1080), (1366, 768), (1440, 900), 
            (1536, 864), (1600, 900), (1280, 720),
            (1280, 800), (1024, 768), (1680, 1050)
        ]
        
        self.languages = [
            ["en-US", "en"],
            ["en-GB", "en"],
            ["en-CA", "en"],
            ["en-AU", "en"],
        ]
    
    def init_stealth_browser(self, use_undetected: bool = False) -> webdriver.Chrome:
        """
        Initialize browser with maximum stealth capabilities
        
        Args:
            use_undetected: If True, attempt to use undetected-chromedriver (requires installation)
        
        Returns:
            Chrome WebDriver instance with stealth settings
        """
        
        # Try to use undetected-chromedriver if available and requested
        if use_undetected:
            try:
                import undetected_chromedriver as uc
                return self._init_undetected_chrome()
            except ImportError:
                logger.warning("undetected-chromedriver not installed, falling back to enhanced Selenium")
        
        # Fall back to enhanced regular Chrome with stealth settings
        return self._init_enhanced_chrome()
    
    def _init_undetected_chrome(self):
        """Initialize undetected-chromedriver with stealth settings"""
        try:
            import undetected_chromedriver as uc
            
            options = uc.ChromeOptions()
            
            # Randomize window size
            width, height = random.choice(self.window_sizes)
            options.add_argument(f'--window-size={width},{height}')
            
            # Random user agent
            options.add_argument(f'--user-agent={random.choice(self.user_agents)}')
            
            # Random language
            lang = random.choice(self.languages)
            options.add_argument(f'--lang={lang[0]}')
            
            # Docker/container specific settings
            if os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER'):
                options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                if os.environ.get('DISPLAY'):
                    options.add_argument(f"--display={os.environ.get('DISPLAY')}")
                else:
                    options.add_argument("--display=:99")
            
            # Additional stealth options
            options.add_argument("--disable-blink-features=AutomationControlled")
            
            # Disable automation flags
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Initialize undetected Chrome
            self.driver = uc.Chrome(options=options, version_main=None)
            
            # Apply additional stealth via CDP
            self._apply_cdp_stealth()
            
            logger.info("Successfully initialized undetected-chromedriver with stealth settings")
            return self.driver
            
        except Exception as e:
            logger.error(f"Failed to initialize undetected-chromedriver: {e}")
            logger.info("Falling back to enhanced regular Chrome")
            return self._init_enhanced_chrome()
    
    def _init_enhanced_chrome(self):
        """Initialize regular Chrome with maximum stealth enhancements"""
        options = Options()
        
        # Randomize window size
        width, height = random.choice(self.window_sizes)
        options.add_argument(f'--window-size={width},{height}')
        
        # Random user agent
        user_agent = random.choice(self.user_agents)
        options.add_argument(f'--user-agent={user_agent}')
        
        # Random language
        lang = random.choice(self.languages)
        options.add_argument(f'--lang={lang[0]}')
        
        # Essential Docker/container configurations
        if os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER'):
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-software-rasterizer")
            
            if os.environ.get('DISPLAY'):
                options.add_argument(f"--display={os.environ.get('DISPLAY')}")
            else:
                options.add_argument("--display=:99")
        
        # Anti-detection arguments
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Additional stealth options
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-ipc-flooding-protection")
        
        # Memory optimizations
        options.add_argument("--memory-pressure-off")
        options.add_argument("--max_old_space_size=4096")
        
        # Enhanced preferences for stealth
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.images": 1,  # Load images for more realistic browsing
            "profile.managed_default_content_settings.stylesheets": 1,
            "profile.managed_default_content_settings.cookies": 1,
            "profile.managed_default_content_settings.javascript": 1,
            "profile.managed_default_content_settings.plugins": 2,
            "profile.managed_default_content_settings.popups": 2,
            "profile.managed_default_content_settings.geolocation": 2,
            "profile.managed_default_content_settings.media_stream": 2,
            "webrtc.ip_handling_policy": "disable_non_proxied_udp",
            "webrtc.multiple_routes_enabled": False,
            "webrtc.nonproxied_udp_enabled": False
        }
        options.add_experimental_option("prefs", prefs)
        
        # Set binary location for Docker environment
        if os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER'):
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
                        options.binary_location = chrome_path
                        logger.info(f"Using Chrome binary at: {chrome_path}")
                        break
        
        try:
            # Try using system chromedriver first (for Docker)
            if os.path.exists('/usr/bin/chromedriver'):
                service = Service('/usr/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                # Use webdriver-manager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            
            # Apply CDP stealth commands
            self._apply_cdp_stealth()
            
            # Apply selenium-stealth if available
            try:
                from selenium_stealth import stealth
                stealth(self.driver,
                    languages=lang,
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
                )
                logger.info("Applied selenium-stealth successfully")
            except ImportError:
                logger.info("selenium-stealth not installed, using CDP commands only")
            
            # Set timeouts
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            logger.info("Successfully initialized enhanced Chrome with stealth settings")
            return self.driver
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome browser: {e}")
            raise
    
    def _apply_cdp_stealth(self):
        """Apply Chrome DevTools Protocol commands for additional stealth"""
        if not self.driver:
            return
        
        try:
            # Override navigator.webdriver
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    // Remove webdriver property
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // Mock plugins
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [
                            {
                                0: {type: "application/x-google-chrome-pdf", suffixes: "pdf"},
                                description: "Portable Document Format",
                                filename: "internal-pdf-viewer",
                                length: 1,
                                name: "Chrome PDF Plugin"
                            },
                            {
                                0: {type: "application/pdf", suffixes: "pdf"},
                                description: "Portable Document Format",
                                filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                                length: 1,
                                name: "Chrome PDF Viewer"
                            },
                            {
                                0: {type: "application/x-nacl", suffixes: ""},
                                1: {type: "application/x-pnacl", suffixes: ""},
                                description: "Native Client Executable",
                                filename: "internal-nacl-plugin",
                                length: 2,
                                name: "Native Client"
                            }
                        ]
                    });
                    
                    // Mock languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                    
                    // Mock vendor
                    Object.defineProperty(navigator, 'vendor', {
                        get: () => 'Google Inc.'
                    });
                    
                    // Mock platform
                    Object.defineProperty(navigator, 'platform', {
                        get: () => 'Win32'
                    });
                    
                    // Mock hardware concurrency
                    Object.defineProperty(navigator, 'hardwareConcurrency', {
                        get: () => 8
                    });
                    
                    // Mock connection
                    Object.defineProperty(navigator, 'connection', {
                        get: () => ({
                            rtt: 100,
                            downlink: 10,
                            effectiveType: '4g',
                            saveData: false
                        })
                    });
                    
                    // Chrome specific
                    window.chrome = {
                        app: {
                            isInstalled: false,
                            InstallState: {
                                DISABLED: 'disabled',
                                INSTALLED: 'installed',
                                NOT_INSTALLED: 'not_installed'
                            },
                            RunningState: {
                                CANNOT_RUN: 'cannot_run',
                                READY_TO_RUN: 'ready_to_run',
                                RUNNING: 'running'
                            }
                        },
                        runtime: {
                            OnInstalledReason: {
                                CHROME_UPDATE: 'chrome_update',
                                INSTALL: 'install',
                                SHARED_MODULE_UPDATE: 'shared_module_update',
                                UPDATE: 'update'
                            },
                            OnRestartRequiredReason: {
                                APP_UPDATE: 'app_update',
                                OS_UPDATE: 'os_update',
                                PERIODIC: 'periodic'
                            },
                            PlatformArch: {
                                ARM: 'arm',
                                ARM64: 'arm64',
                                MIPS: 'mips',
                                MIPS64: 'mips64',
                                X86_32: 'x86-32',
                                X86_64: 'x86-64'
                            },
                            PlatformNaclArch: {
                                ARM: 'arm',
                                MIPS: 'mips',
                                MIPS64: 'mips64',
                                X86_32: 'x86-32',
                                X86_64: 'x86-64'
                            },
                            PlatformOs: {
                                ANDROID: 'android',
                                CROS: 'cros',
                                LINUX: 'linux',
                                MAC: 'mac',
                                OPENBSD: 'openbsd',
                                WIN: 'win'
                            },
                            RequestUpdateCheckStatus: {
                                NO_UPDATE: 'no_update',
                                THROTTLED: 'throttled',
                                UPDATE_AVAILABLE: 'update_available'
                            }
                        }
                    };
                    
                    // Permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                '''
            })
            
            # Disable webdriver flag in Chrome
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": self.driver.execute_script("return navigator.userAgent").replace("HeadlessChrome", "Chrome")
            })
            
            logger.info("Applied CDP stealth commands successfully")
            
        except Exception as e:
            logger.warning(f"Failed to apply some CDP commands: {e}")
    
    def close(self):
        """Close the browser safely"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.driver = None