#!/usr/bin/env python3
"""
Upload file besar ke desu.si menggunakan browser automation.
Skrip ini dirancang untuk dijalankan di Google Colab atau lingkungan lokal
yang sudah memiliki Chromium/Chrome + ChromeDriver.
"""

import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:
    logging.error("Selenium belum terpasang. Jalankan: pip install selenium")
    sys.exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None

try:
    from google.colab import drive
    HAS_COLAB_DRIVE = True
except ImportError:
    HAS_COLAB_DRIVE = False

UPLOAD_URL = "https://desu.si/"
MAX_FILE_SIZE_GB = 15.0
SEARCH_DIR = '/content/drive/MyDrive/'


def install_selenium():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "selenium"])


def install_webdriver_manager() -> bool:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "webdriver-manager"])
        global ChromeDriverManager
        from webdriver_manager.chrome import ChromeDriverManager as _ChromeDriverManager
        ChromeDriverManager = _ChromeDriverManager
        return True
    except Exception as exc:
        logging.debug('webdriver-manager install error: %s', exc)
        return False


def find_chrome_binary():
    """Cari Chrome/Chromium binary di berbagai lokasi."""
    candidates = [
        'google-chrome',
        'google-chrome-stable',
        'chromium',
        'chromium-browser',
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
        '/snap/bin/chromium',
        '/opt/google/chrome/chrome',
        '/opt/chromium/chrome',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    ]
    found_candidates = []
    
    # First, try which() and verify path exists
    for candidate in candidates:
        which_result = shutil.which(candidate)
        if which_result and os.path.exists(which_result):
            return which_result
    
    # Second, try direct path checks
    for candidate in candidates:
        if os.path.exists(candidate) and os.path.isfile(candidate):
            return candidate
    
    # Third, check common debian package locations after apt install
    debian_paths = [
        '/usr/lib/chromium-browser/chromium-browser',
        '/usr/lib/chromium/chromium',
        '/snap/chromium/current/chromium',
    ]
    for path in debian_paths:
        if os.path.exists(path) and os.path.isfile(path):
            return path
    
    return None


def install_google_chrome() -> bool:
    """Download dan install Google Chrome Stable jika Chromium tidak tersedia."""
    if sys.platform != 'linux':
        return False
    deb_url = 'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb'
    deb_path = '/tmp/google-chrome-stable_current_amd64.deb'
    try:
        logging.info('Mendownload Google Chrome Stable...')
        subprocess.check_call(['wget', '-q', '-O', deb_path, deb_url])
        subprocess.check_call(['apt-get', 'install', '-y', '-qq', deb_path],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        if os.path.exists('/usr/bin/google-chrome-stable'):
            logging.info('Google Chrome Stable berhasil diinstall.')
            return True
        logging.warning('Google Chrome Stable terinstall tapi binary tidak ditemukan di lokasi standar.')
        return True
    except Exception as exc:
        logging.debug('Google Chrome install failed: %s', exc)
        return False


def install_chromium() -> bool:
    """Install Chromium otomatis di sistem (Linux only)."""
    if sys.platform != 'linux':
        return False
    try:
        logging.info('Mencoba install chromium-browser via apt...')
        subprocess.check_call(['apt-get', 'update', '-qq'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call(['apt-get', 'install', '-y', '-qq', 'chromium-browser'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        if os.path.exists('/usr/bin/chromium-browser'):
            logging.info('Chromium berhasil diinstall di /usr/bin/chromium-browser.')
            return True
        elif os.path.exists('/usr/lib/chromium-browser/chromium-browser'):
            logging.info('Chromium berhasil diinstall di /usr/lib/chromium-browser/chromium-browser.')
            return True
        logging.warning('chromium-browser tidak ditemukan setelah install apt.')
    except Exception as exc:
        logging.debug('Chromium install failed: %s', exc)

    logging.info('Mencoba install Google Chrome Stable sebagai fallback...')
    return install_google_chrome()


def install_chromium_dependencies() -> bool:
    """Install system dependencies yang dibutuhkan Chromium di headless environment."""
    if sys.platform != 'linux':
        return False
    deps = [
        'libglib2.0-0',
        'libnss3',
        'libxss1',
        'libasound2',
        'libatk1.0-0',
        'libatk-bridge2.0-0',
        'libgtk-3-0',
        'libgdk-pixbuf2.0-0',
        'libx11-xcb1',
        'libxcomposite1',
        'libxdamage1',
        'libxrandr2',
        'libxcursor1',
        'libxfixes3',
        'libxtst6',
        'libxkbcommon0',
        'libdbus-1-3',
        'libgbm1',
        'libcups2',
        'fonts-liberation',
        'libappindicator3-1',
    ]
    try:
        logging.info('Installing Chromium system dependencies...')
        subprocess.check_call(['apt-get', 'update', '-qq'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call(['apt-get', 'install', '-y', '-qq'] + deps,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info('System dependencies installed successfully.')
        time.sleep(1)
        return True
    except Exception as exc:
        logging.debug('System dependencies install failed: %s', exc)
        return False


def get_chrome_version(chrome_path: str) -> str | None:
    try:
        output = subprocess.check_output([chrome_path, '--version'], stderr=subprocess.STDOUT, text=True)
        match = re.search(r'(\d+\.\d+\.\d+\.\d+)', output)
        if match:
            return match.group(1)
    except Exception as exc:
        logging.debug('Gagal membaca versi Chrome: %s', exc)
    return None


def chrome_can_start(chrome_path: str) -> bool:
    if not chrome_path or not os.path.exists(chrome_path):
        return False
    cmd = [
        chrome_path,
        '--headless',
        '--disable-gpu',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--remote-debugging-port=0',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-extensions',
        '--disable-crash-reporter',
        'about:blank',
    ]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3)
        ret = proc.poll()
        if ret is not None:
            stderr = proc.stderr.read().decode(errors='ignore') if proc.stderr else ''
            logging.debug('Chrome startup test failed for %s: %s', chrome_path, stderr.strip())
            return False
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        return True
    except Exception as exc:
        logging.debug('Chrome startup validation failed: %s', exc)
        return False


def find_chromedriver(chrome_path: str | None = None):
    driver_path = shutil.which('chromedriver')
    if driver_path:
        logging.info('Found chromedriver on PATH: %s', driver_path)
        return driver_path
    # Colab / Debian package locations
    common_paths = [
        '/usr/bin/chromedriver',
        '/usr/local/bin/chromedriver',
        '/opt/bin/chromedriver',
    ]
    for path in common_paths:
        if os.path.exists(path):
            logging.info('Found chromedriver in common path: %s', path)
            return path

    if ChromeDriverManager is None:
        if install_webdriver_manager():
            logging.info('webdriver_manager terpasang, akan mencoba download ChromeDriver otomatis.')
        else:
            return None

    try:
        version = get_chrome_version(chrome_path) if chrome_path else None
        if version:
            logging.info('Detected Chrome version: %s', version)
            try:
                driver_path = ChromeDriverManager(version=version).install()
                logging.info('Downloaded ChromeDriver for exact version: %s', driver_path)
                return driver_path
            except Exception as exc:
                logging.debug('Exact version install failed: %s', exc)
                major_version = version.split('.')[0]
                logging.info('Trying ChromeDriver for major version: %s', major_version)
                try:
                    driver_path = ChromeDriverManager(version=major_version).install()
                    logging.info('Downloaded ChromeDriver for major version: %s', driver_path)
                    return driver_path
                except Exception as exc2:
                    logging.debug('Major version install failed: %s', exc2)
        logging.info('Trying generic ChromeDriver install...')
        driver_path = ChromeDriverManager().install()
        logging.info('Downloaded generic ChromeDriver: %s', driver_path)
        return driver_path
    except Exception as exc:
        logging.debug('ChromeDriver manager failed: %s', exc)

    # Last fallback: try apt-based chromedriver if available
    try:
        logging.info('Mencoba install paket chromedriver via apt sebagai fallback...')
        subprocess.check_call(['apt-get', 'update', '-qq'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call(['apt-get', 'install', '-y', '-qq', 'chromedriver'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        driver_path = shutil.which('chromedriver')
        if driver_path:
            logging.info('Chromedriver berhasil diinstall dari apt: %s', driver_path)
            return driver_path
    except Exception as exc:
        logging.debug('Apt chromedriver fallback failed: %s', exc)

    return None


def build_driver(chrome_path=None, driver_path=None):
    options = Options()

    # Colab/container compatible headless flags
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-accelerated-2d-canvas')
    options.add_argument('--disable-gpu-compositing')
    options.add_argument('--disable-background-networking')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-device-discovery-notifications')
    options.add_argument('--disable-hang-monitor')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-default-apps')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--disable-sync')
    options.add_argument('--disable-crash-reporter')
    options.add_argument('--disable-remote-fonts')
    options.add_argument('--mute-audio')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-prompt-on-repost')
    options.add_argument('--single-process')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--hide-scrollbars')
    options.add_argument('--disable-extensions-file-access-check')
    options.add_argument('--disable-features=TranslateUI,BackgroundTaskHinting,AudioServiceOutOfProcess,VizDisplayCompositor')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-client-side-phishing-detection')
    options.add_argument('--enable-automation')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    if chrome_path is None:
        chrome_path = find_chrome_binary()

    if chrome_path is not None and not chrome_can_start(chrome_path):
        logging.warning('Binary Chrome/Chromium ditemukan tapi tidak bisa dijalankan: %s', chrome_path)
        logging.info('Mencoba install Google Chrome Stable sebagai fallback...')
        if install_google_chrome():
            time.sleep(2)
            chrome_path = find_chrome_binary()

    if chrome_path is None:
        logging.warning('Chrome binary tidak ditemukan, mencoba install Chromium/Chrome...')
        install_chromium_dependencies()
        if install_chromium():
            time.sleep(2)
            chrome_path = find_chrome_binary()

        if chrome_path is None:
            logging.error('Gagal menemukan Chrome binary setelah install.')
            raise FileNotFoundError('Chrome binary tidak ditemukan dan tidak bisa diinstall.')

    if chrome_path is not None and not chrome_can_start(chrome_path):
        logging.error('Binary Chrome/Chromium tidak bisa dijalankan walaupun terpasang: %s', chrome_path)
        raise EnvironmentError('Chrome/Chromium binary tidak dapat dijalankan.')

    options.add_argument('--headless')

    if chrome_path:
        logging.info(f'Menggunakan Chrome binary: {chrome_path}')
        options.binary_location = chrome_path

    if driver_path is None:
        driver_path = find_chromedriver(chrome_path)
    if driver_path is None:
        raise FileNotFoundError('chromedriver tidak ditemukan.')

    service = Service(driver_path)
    return webdriver.Chrome(service=service, options=options)


def verify_file(file_path: Path):
    if not file_path.exists():
        raise FileNotFoundError(f'File tidak ditemukan: {file_path}')
    size_gb = file_path.stat().st_size / (1024**3)
    if size_gb > MAX_FILE_SIZE_GB:
        raise ValueError(f'File terlalu besar untuk desu.si: {size_gb:.2f} GB > {MAX_FILE_SIZE_GB} GB')
    return True


def search_mp4_files(search_dir: str) -> list[Path]:
    mp4_files = []
    for root, _, files in os.walk(search_dir):
        for file in files:
            if file.lower().endswith('.mp4'):
                path = Path(root) / file
                if path.stat().st_size / (1024**3) <= MAX_FILE_SIZE_GB:
                    mp4_files.append(path)
    return sorted(mp4_files)


def choose_file(mp4_files: list[Path]) -> Path:
    while True:
        try:
            pilihan = int(input("👉 Ketik NOMOR video yang ingin di-upload: "))
            if 1 <= pilihan <= len(mp4_files):
                return mp4_files[pilihan - 1]
            print("❌ Nomor tidak valid. Coba lagi.")
        except ValueError:
            print("❌ Input harus angka. Coba lagi.")


def check_google_drive() -> bool:
    if not Path('/content/drive').exists():
        logging.error('Google Drive belum dimount. Jalankan mount drive di notebook Colab terlebih dahulu:')
        logging.error('from google.colab import drive')
        logging.error("drive.mount('/content/drive')")
        return False
    return True


def extract_link_from_html(html: str) -> str | None:
    """Extract desu.si link from HTML content with multiple patterns."""
    # Pattern 1: Standard desu.si link
    match = re.search(r'https?://desu\.si/[A-Za-z0-9]+', html)
    if match:
        return match.group(0)

    # Pattern 2: Link without protocol
    match = re.search(r'desu\.si/[A-Za-z0-9]+', html)
    if match:
        return f"https://{match.group(0)}"

    # Pattern 3: Link in quotes or attributes
    match = re.search(r'["\']([^"\']*desu\.si/[^"\']*)["\']', html)
    if match:
        link = match.group(1)
        if not link.startswith('http'):
            link = f"https://{link}"
        return link

    # Pattern 4: Link in href or src attributes
    match = re.search(r'(?:href|src)=["\']([^"\']*desu\.si/[^"\']*)["\']', html)
    if match:
        link = match.group(1)
        if not link.startswith('http'):
            link = f"https://{link}"
        return link

    return None


def convert_to_direct_link(desu_link: str) -> str:
    """Convert desu.si upload link to direct download link."""
    if not desu_link or 'desu.si' not in desu_link:
        return desu_link

    # Extract the code from the link
    match = re.search(r'desu\.si/([A-Za-z0-9]+)', desu_link)
    if match:
        code = match.group(1)
        return f"https://i.desu.si/{code}.mp4"

    return desu_link


def upload_via_browser(file_path: str) -> str | None:
    logging.info('Membuka browser headless untuk upload...')
    driver = None
    try:
        driver = build_driver()
    except Exception as exc:
        logging.error('Gagal membuat WebDriver: %s', exc)
        if 'DevToolsActivePort' in str(exc) or 'Chrome failed to start' in str(exc) or 'chrome not reachable' in str(exc):
            logging.error('💡 Chromium/Chrome gagal start. Pastikan dependency terpasang atau gunakan Google Chrome Stable.')
            logging.error('   Coba jalankan di Colab: !apt-get update -qq && apt-get install -y -qq libglib2.0-0 libnss3 libxss1 libasound2 libatk1.0-0 libatk-bridge2.0-0 libgtk-3-0 libgdk-pixbuf2.0-0 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libxcursor1 libxfixes3 libxtst6 libxkbcommon0 libdbus-1-3 libgbm1 libcups2 fonts-liberation libappindicator3-1')
            logging.error('   Jika Chromium masih gagal, gunakan Google Chrome Stable atau periksa apakah binary %s dapat menjalankan --headless.', chrome_path or 'unknown')
        return None

    if driver is None:
        return None

    try:
        logging.info('Navigasi ke desu.si...')
        driver.get(UPLOAD_URL)

        # Wait for page to load completely
        time.sleep(3)
        wait = WebDriverWait(driver, 30)

        logging.info('Mencari input file...')
        # Try multiple selectors for file input
        file_input_selectors = [
            (By.NAME, 'files[]'),
            (By.CSS_SELECTOR, 'input[type="file"]'),
            (By.CSS_SELECTOR, 'input[name="files[]"]'),
            (By.XPATH, '//input[@type="file"]'),
        ]

        file_input = None
        for selector in file_input_selectors:
            try:
                file_input = wait.until(EC.presence_of_element_located(selector))
                logging.info('Found file input with selector: %s', selector)
                break
            except:
                continue

        if file_input is None:
            logging.error('File input tidak ditemukan di halaman.')
            logging.debug('Page source: %s', driver.page_source[:2000])
            return None

        # Make sure the element is visible and interactable
        driver.execute_script('arguments[0].style.display = "block";', file_input)
        driver.execute_script('arguments[0].style.visibility = "visible";', file_input)
        driver.execute_script('arguments[0].style.opacity = "1";', file_input)
        driver.execute_script('arguments[0].removeAttribute("hidden");', file_input)

        # Scroll to element
        driver.execute_script('arguments[0].scrollIntoView(true);', file_input)

        # Wait for element to be clickable
        try:
            wait.until(EC.element_to_be_clickable(file_input))
        except:
            logging.warning('Element tidak clickable, melanjutkan dengan send_keys...')

        logging.info('Mengirim file path ke input...')
        file_input.send_keys(file_path)

        # Verify file was selected
        try:
            selected_files = driver.execute_script('return arguments[0].files;', file_input)
            if selected_files and len(selected_files) > 0:
                logging.info('File berhasil dipilih: %s', selected_files[0].name if hasattr(selected_files[0], 'name') else 'unknown')
                # Try to trigger change event
                driver.execute_script('arguments[0].dispatchEvent(new Event("change", { bubbles: true }));', file_input)
                driver.execute_script('arguments[0].dispatchEvent(new Event("input", { bubbles: true }));', file_input)
            else:
                logging.warning('File tidak terdeteksi sebagai terpilih.')
        except Exception as exc:
            logging.debug('Gagal verifikasi file selection: %s', exc)

        logging.info('Mencari tombol submit...')
        # Try multiple selectors for submit button
        submit_selectors = [
            (By.CSS_SELECTOR, 'input[type=submit]'),
            (By.CSS_SELECTOR, 'button[type=submit]'),
            (By.CSS_SELECTOR, 'input[value*="upload" i]'),
            (By.CSS_SELECTOR, 'button:contains("Upload")'),
            (By.XPATH, '//input[@type="submit"]'),
            (By.XPATH, '//button[contains(text(), "Upload")]'),
            (By.XPATH, '//input[contains(@value, "Upload")]'),
            (By.CSS_SELECTOR, 'input[name="submit"]'),
        ]

        submit_button = None
        for selector in submit_selectors:
            try:
                submit_button = driver.find_element(*selector)
                logging.info('Found submit button with selector: %s', selector)
                break
            except:
                continue

        if submit_button is None:
            logging.error('Tombol submit tidak ditemukan.')
            return None

        # Wait for submit button to be enabled and clickable
        logging.info('Menunggu tombol submit siap...')
        max_wait = 30  # Reduced wait time since button might never enable
        button_enabled = False

        for i in range(max_wait):
            try:
                # Check if button is enabled
                is_enabled = driver.execute_script('return !arguments[0].disabled;', submit_button)
                is_visible = driver.execute_script('return arguments[0].offsetWidth > 0 && arguments[0].offsetHeight > 0;', submit_button)
                button_text = driver.execute_script('return arguments[0].value || arguments[0].textContent || arguments[0].innerText;', submit_button)

                logging.debug('Button state (attempt %d): enabled=%s, visible=%s, text="%s"', i+1, is_enabled, is_visible, button_text.strip())

                if is_enabled:
                    logging.info('Submit button enabled!')
                    button_enabled = True
                    break
                else:
                    logging.debug('Submit button masih disabled, menunggu...')
                    time.sleep(1)
            except Exception as exc:
                logging.debug('Error checking button state (attempt %d): %s', i+1, exc)
                time.sleep(1)

        # If button never enables, try to force submit anyway
        if not button_enabled:
            logging.warning('Submit button tetap disabled setelah %d detik. Mencoba force submit...', max_wait)

            # Try to submit the form directly using JavaScript
            try:
                # Find the form containing the file input
                form = driver.execute_script('return arguments[0].form;', file_input)
                if form:
                    driver.execute_script('arguments[0].submit();', form)
                    logging.info('Form submitted using JavaScript.')
                else:
                    # Try clicking the button with JavaScript anyway
                    driver.execute_script('arguments[0].scrollIntoView(true);', submit_button)
                    driver.execute_script('arguments[0].removeAttribute("disabled");', submit_button)
                    driver.execute_script('arguments[0].click();', submit_button)
                    logging.info('Submit button diklik menggunakan JavaScript (force).')
            except Exception as exc:
                logging.error('Force submit gagal: %s', exc)
                return None
        else:
            # Button is enabled, click normally
            try:
                driver.execute_script('arguments[0].scrollIntoView(true);', submit_button)
                driver.execute_script('arguments[0].click();', submit_button)
                logging.info('Submit button diklik menggunakan JavaScript.')
            except Exception as exc:
                logging.error('Normal submit click gagal: %s', exc)
                return None

        logging.info('Upload dimulai, menunggu hasil...')
        time.sleep(10)  # Longer initial wait for upload to start

        # Wait for upload completion - check for link or success message
        wait = WebDriverWait(driver, 3600)

        def upload_complete(browser):
            page = browser.page_source.lower()
            url = browser.current_url.lower()

            # Check for desu.si link in page or URL
            if extract_link_from_html(page):
                return True
            if 'desu.si/' in url and url != UPLOAD_URL.lower():
                logging.info('Redirect detected to: %s', url)
                return True

            # Check for common success/error indicators
            success_indicators = ['success', 'berhasil', 'complete', 'finished', 'uploaded', 'upload complete']
            error_indicators = ['error', 'failed', 'gagal', 'invalid', 'too large', 'file size']

            for indicator in success_indicators:
                if indicator in page:
                    logging.info('Detected success indicator: %s', indicator)
                    return True

            for indicator in error_indicators:
                if indicator in page:
                    logging.warning('Detected error indicator: %s', indicator)
                    return True  # Stop waiting, but upload failed

            # Check if we're still on upload page (upload might be in progress)
            if 'upload' in page and 'file' in page:
                return False  # Still uploading

            return False

        try:
            wait.until(upload_complete)
        except Exception as exc:
            logging.warning('Timeout menunggu upload selesai: %s', exc)

        # Additional wait and final check
        time.sleep(5)
        page_source = driver.page_source
        current_url = driver.current_url

        link = extract_link_from_html(page_source)

        if link:
            logging.info('Upload berhasil, link ditemukan: %s', link)
            return convert_to_direct_link(link)
        elif current_url != UPLOAD_URL:
            # Check if redirected to a result page
            logging.info('Redirect ke halaman hasil: %s', current_url)
            if 'desu.si' in current_url:
                # Try to extract link from URL or page
                url_match = re.search(r'desu\.si/([A-Za-z0-9]+)', current_url)
                if url_match:
                    link = f"https://desu.si/{url_match.group(1)}"
                    logging.info('Link extracted from URL: %s', link)
                    return convert_to_direct_link(link)
                # Reload page to get final content
                driver.refresh()
                time.sleep(3)
                page_source = driver.page_source
                link = extract_link_from_html(page_source)
                if link:
                    return convert_to_direct_link(link)
        else:
            logging.error('Upload selesai tapi link tidak ditemukan.')
            logging.debug('Final URL: %s', current_url)
            logging.debug('Final page source snippet: %s', page_source[:1500])
            return None

    except Exception as exc:
        logging.error('Upload browser gagal: %s', exc)
        try:
            logging.debug('Status URL: %s', driver.current_url)
            logging.debug('Page source snippet: %s', driver.page_source[:800])
        except:
            pass
        return None
    finally:
        if driver:
            driver.quit()


def main():
    file_path: Path
    if len(sys.argv) == 1 or sys.argv[1] in ('--choose', '-c'):
        if not check_google_drive():
            sys.exit(1)

        mp4_files = search_mp4_files(SEARCH_DIR)
        if not mp4_files:
            logging.error('Tidak ada file MP4 yang ditemukan di Google Drive.')
            sys.exit(1)

        print('\n✅ Ditemukan %d file MP4 di Google Drive:\n' % len(mp4_files))
        for i, path in enumerate(mp4_files, start=1):
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f'[{i}] {path.name} ({size_mb:.2f} MB)')

        print('\n' + '-' * 50)
        file_path = choose_file(mp4_files)
    elif len(sys.argv) == 2:
        file_path = Path(sys.argv[1]).resolve()
    else:
        print('Usage: python desu_si_selenium_upload.py [--choose | /path/to/video.mp4]')
        sys.exit(1)

    try:
        verify_file(file_path)
    except Exception as exc:
        logging.error(exc)
        sys.exit(1)

    logging.info(f'File yang dipilih: {file_path}')
    link = upload_via_browser(str(file_path))
    if link:
        direct_link = convert_to_direct_link(link)
        print('\n🎉 UPLOAD BERHASIL!')
        print(f'� Upload link: {link}')
        print(f'📥 Direct download: {direct_link}')
    else:
        print('\n❌ Upload gagal. Pastikan ChromeDriver tersedia dan desu.si menerima upload dari browser.')


if __name__ == '__main__':
    main()
