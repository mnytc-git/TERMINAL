#!/usr/bin/env python3
"""
ULTIMATE AUTO-STREAMING BOT
Auto-Resolve Domain -> LK21 Search (Sapu Jagat) -> Auto Detect New File -> Upload desu.si -> Auto Play WatchParty -> Auto Delete
"""

import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

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
    from selenium.webdriver.common.keys import Keys
except ImportError:
    logging.error("Selenium belum terpasang. Jalankan: pip install selenium")
    sys.exit(1)

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except:
    pass

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None

UPLOAD_URL = "https://desu.si/"
MAX_FILE_SIZE_GB = 15.0
SEARCH_DIR = '/content/drive/MyDrive/'
ROOM_URL = "https://www.watchparty.me/watch/fantastic-receipt-move"


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
    candidates = [
        'google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser',
        '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium',
        '/usr/bin/chromium-browser', '/snap/bin/chromium', '/opt/google/chrome/chrome',
    ]
    for candidate in candidates:
        which_result = shutil.which(candidate)
        if which_result and os.path.exists(which_result):
            return which_result
    for candidate in candidates:
        if os.path.exists(candidate) and os.path.isfile(candidate):
            return candidate
    return None

def install_google_chrome() -> bool:
    if sys.platform != 'linux':
        return False
    deb_url = 'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb'
    deb_path = '/tmp/google-chrome-stable_current_amd64.deb'
    try:
        logging.info('Mendownload Google Chrome Stable...')
        subprocess.check_call(['wget', '-q', '-O', deb_path, deb_url])
        subprocess.check_call(['apt-get', 'install', '-y', '-qq', deb_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        return True
    except Exception:
        return False

def build_driver():
    options = Options()
    
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--mute-audio')
    options.add_argument('--window-size=1920,1080')

    chrome_path = find_chrome_binary()
    if not chrome_path:
        install_google_chrome()
        chrome_path = find_chrome_binary()

    if chrome_path:
        options.binary_location = chrome_path

    if ChromeDriverManager is None:
        install_webdriver_manager()

    try:
        driver_path = ChromeDriverManager().install()
    except Exception:
        driver_path = shutil.which('chromedriver')

    if not driver_path:
        raise FileNotFoundError('chromedriver tidak ditemukan.')

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_script_timeout(600)
    driver.implicitly_wait(10)
    
    return driver

def verify_file(file_path: Path):
    if not file_path.exists():
        raise FileNotFoundError(f'File tidak ditemukan: {file_path}')
    size_gb = file_path.stat().st_size / (1024**3)
    if size_gb > MAX_FILE_SIZE_GB:
        raise ValueError(f'File terlalu besar: {size_gb:.2f} GB')
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
            pilihan = int(input("\n👉 Ketik NOMOR video yang ingin diproses: "))
            if 1 <= pilihan <= len(mp4_files):
                return mp4_files[pilihan - 1]
            print("❌ Nomor tidak valid. Coba lagi.")
        except ValueError:
            print("❌ Input harus angka. Coba lagi.")

def execute_script_with_retry(driver, script, *args, max_retries=2, retry_delay=0.5):
    for attempt in range(max_retries):
        try:
            return driver.execute_script(script, *args)
        except Exception as exc:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None

def check_google_drive() -> bool:
    if not Path('/content/drive').exists():
        logging.error('Google Drive belum dimount. Mount terlebih dahulu.')
        return False
    return True

def run_auto_lk21_flow() -> Path | None:
    if requests is None or BeautifulSoup is None:
        print("❌ requests/beautifulsoup4 tidak tersedia. Install dengan: pip install requests beautifulsoup4")
        return None
    
    # Base Domain Default (Bisa berupa root atau subdomain lama)
    BASE_DOMAIN = "https://tv12.lk21official.cc"
    DOWNLOAD_DOMAIN = "https://dadadidi.de/get"
    
    print("\n" + "="*50)
    print("🎬 LK21 SEARCH & AUTO-DETECTOR")
    print("="*50)
    
    keyword = input("👉 Masukkan judul film (Contoh: Wonder Woman): ").strip()
    if not keyword:
        return None
    
    print(f"\n🔍 Menghubungkan ke server LK21...")
    driver = None
    try:
        driver = build_driver()
        
        # --- LOGIKA TINGKAT TINGGI: AUTO-RESOLVE DYNAMIC DOMAIN ---
        # Bot memancing server untuk mengetahui apakah ada redirect ke subdomain baru
        driver.get(BASE_DOMAIN)
        time.sleep(4) # Waktu tunggu agar redirect HTTP/Cloudflare selesai
        
        parsed_url = urlparse(driver.current_url)
        ACTIVE_DOMAIN = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        if ACTIVE_DOMAIN != BASE_DOMAIN:
            print(f"🔄 Auto-Redirect Terdeteksi! Skrip beradaptasi ke domain baru: {ACTIVE_DOMAIN}")
        else:
            print(f"✅ Domain stabil: {ACTIVE_DOMAIN}")
            
        print(f"🔍 Mencari film '{keyword}' di {ACTIVE_DOMAIN}...")
        search_query = keyword.replace(' ', '+')
        driver.get(f"{ACTIVE_DOMAIN}/search?s={search_query}")
        time.sleep(3)
        page_source = driver.page_source
        
        soup = BeautifulSoup(page_source, 'html.parser')
        movies = []
        
        # --- LOGIKA TINGKAT TINGGI: SELEKTOR SAPU JAGAT ---
        for article in soup.select('.post-item, article, .item-series, .film-item, div[class*="item"]'):
            title_elem = article.find(['h2', 'h3']) or article.find('a', title=True)
            link_elem = article.find('a', href=True)
            if title_elem and link_elem:
                title = title_elem.get_text(strip=True)
                if not title and title_elem.has_attr('title'):
                    title = title_elem['title']
                
                href = link_elem['href']
                if title and len(href) > 2 and 'javascript' not in href and '#' not in href:
                    movies.append({'title': title, 'url': href})
        
        unique_movies = []
        seen_urls = set()
        for m in movies:
            if m['url'] not in seen_urls:
                unique_movies.append(m)
                seen_urls.add(m['url'])
                
        if not unique_movies:
            print("❌ Bot tidak menemukan film secara otomatis (Mungkin diblokir Cloudflare).")
            # --- JARING PENGAMAN (FALLBACK) ---
            manual_link = input("👉 Tempel/Paste link film LK21-nya secara manual (atau tekan Enter untuk batal): ").strip()
            if not manual_link:
                return None
            slug = manual_link.rstrip('/').split('/')[-1]
            download_url = f"{DOWNLOAD_DOMAIN}/{slug}"
            
        else:
            print(f"\n✅ Ditemukan {len(unique_movies)} hasil pencarian:\n")
            for i, m in enumerate(unique_movies[:20], 1):
                print(f"[{i}] {m['title'][:70]}")
                
            choice = input("\n👉 Pilih nomor film (0 untuk batal): ")
            try:
                choice = int(choice)
            except ValueError:
                choice = 0
                
            if choice <= 0 or choice > len(unique_movies):
                return None
                
            selected = unique_movies[choice-1]
            slug = selected['url'].rstrip('/').split('/')[-1]
            download_url = f"{DOWNLOAD_DOMAIN}/{slug}"
        
        print("\n🎉 LINK DOWNLOAD BERHASIL DIRAKIT!")
        print("👇 KLIK LINK DI BAWAH INI UNTUK MENYIMPANNYA KE GOOGLE DRIVE ANDA 👇")
        print(f"📥 {download_url}")
        print("-" * 50)
        
        old_files = set(search_mp4_files(SEARCH_DIR))
        
        print("\n⏳ Bot sedang memantau folder Google Drive Anda...")
        print("   Silakan KLIK link di atas, dan pilih 'Tetap Download' di halaman Google.")
        print("   Bot akan mendeteksi otomatis jika file sudah masuk...\n")
        
        while True:
            time.sleep(3)
            current_files = set(search_mp4_files(SEARCH_DIR))
            new_files = current_files - old_files
            
            if new_files:
                new_file = sorted(list(new_files), key=lambda f: f.stat().st_mtime, reverse=True)[0]
                print(f"🔔 File baru terdeteksi: {new_file.name}")
                print("   Memastikan proses save/download selesai 100%...")
                
                last_size = -1
                while True:
                    time.sleep(3)
                    current_size = new_file.stat().st_size
                    if current_size == last_size and current_size > 0:
                        break
                    last_size = current_size
                    
                print("✅ File sudah utuh dan siap diproses!")
                return new_file
                
    except Exception as e:
        print(f"❌ Error saat pencarian: {e}")
        return None
    finally:
        if driver: driver.quit()

def upload_via_browser(file_path: str) -> str | None:
    logging.info('Membuka browser headless untuk upload ke desu.si...')
    try:
        driver = build_driver()
    except Exception as exc:
        logging.error('Gagal membuat WebDriver: %s', exc)
        return None

    try:
        logging.info('Navigasi ke desu.si...')
        driver.get(UPLOAD_URL)
        time.sleep(2)
        wait = WebDriverWait(driver, 30)

        logging.info('Mencari input file...')
        file_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"], input[name="files[]"]')))
        
        driver.execute_script('arguments[0].style.display = "block"; arguments[0].removeAttribute("hidden");', file_input)
        
        logging.info('Mengirim file path ke input...')
        file_input.send_keys(file_path)

        logging.info('Mencari tombol submit...')
        submit_button = driver.find_element(By.CSS_SELECTOR, 'input[type=submit], button[type=submit]')
        
        execute_script_with_retry(driver, 'arguments[0].click();', submit_button)
        logging.info('Upload dimulai, menunggu hasil...')
        
        start_time = time.time()
        max_wait_seconds = 86400  # Maksimal 24 Jam

        while time.time() - start_time < max_wait_seconds:
            try:
                url = driver.current_url.lower()
                
                if url and 'desu.si/' in url and url != UPLOAD_URL.lower():
                    try:
                        body_text = driver.find_element(By.TAG_NAME, 'body').text
                        body_text_clean = body_text.replace('\\/', '/')
                        
                        if '403 forbidden' in body_text.lower() or 'error' in body_text.lower():
                            logging.error('Server menolak file: %s', body_text)
                            return None

                        match = re.search(r'(https?://[^\s"\'<>\[\]]+\.mp4)', body_text_clean)
                        if match:
                            return match.group(1)
                    except Exception:
                        pass
                
                page = execute_script_with_retry(driver, 'return document.documentElement.outerHTML;')
                if page:
                    page_clean = page.replace('\\/', '/')
                    match = re.search(r'(https?://[^\s"\'<>\[\]]+\.mp4)', page_clean)
                    if match:
                        return match.group(1)

                elapsed = int(time.time() - start_time)
                if elapsed % 15 == 0:
                    logging.info('Upload in progress... (elapsed: %d seconds)', elapsed)
                time.sleep(1)

            except Exception as exc:
                time.sleep(1)
                
        return None

    except Exception as exc:
        logging.error('Upload browser gagal: %s', exc)
        return None
    finally:
        if driver:
            driver.quit()

def play_on_watchparty(video_link: str, room_url: str):
    logging.info('\n🤖 [AUTO-PLAY] Menghubungkan ke WatchParty Room...')
    driver = None
    try:
        driver = build_driver()
        driver.get(room_url)
        wait = WebDriverWait(driver, 20)

        logging.info('🔍 Mencari kolom input URL...')
        input_selector = "input[placeholder*='Enter video file URL']"
        input_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, input_selector)))
        
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, input_selector)))

        logging.info('🧹 Membersihkan kolom input (React Bypass)...')
        input_box.send_keys(Keys.CONTROL, 'a')
        input_box.send_keys(Keys.BACKSPACE)
        time.sleep(0.5)

        logging.info('🔗 Memasukkan link dan menekan ENTER...')
        input_box.send_keys(video_link)
        time.sleep(0.5)
        input_box.send_keys(Keys.ENTER)

        logging.info('🎬 SUKSES! Video diputar di WatchParty. Bot keluar dari room...')
        time.sleep(3) 

    except Exception as exc:
        logging.error('Gagal memutar video di WatchParty: %s', exc)
    finally:
        if driver:
            driver.quit()

def main():
    if not check_google_drive():
        sys.exit(1)

    print("\n" + "="*55)
    print("🚀 ULTIMATE AUTO-STREAMING BOT")
    print("   (LK21 -> Google Drive -> desu.si -> WatchParty)")
    print("="*55)
    print("[1] 🔍 Cari & Download dari LK21 (Full Otomatis)")
    print("[2] 📂 Pilih File MP4 yang sudah ada di Google Drive")
    print("="*55)
    
    choice = input("👉 Pilih menu (1/2): ").strip()
    
    file_path = None
    if choice == '1':
        file_path = run_auto_lk21_flow()
        if not file_path:
            print("❌ Proses dibatalkan.")
            return
    elif choice == '2':
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
    else:
        print("❌ Pilihan tidak valid.")
        return

    try:
        verify_file(file_path)
    except Exception as exc:
        logging.error(exc)
        sys.exit(1)

    logging.info(f'\n🚀 Memulai proses unggah untuk: {file_path.name}')
    
    link = upload_via_browser(str(file_path))
    
    if link and 'desu.si' in link and link.endswith('.mp4'):
        print('\n🎉 UPLOAD BERHASIL!')
        print(f'📥 Direct download: {link}')
        
        play_on_watchparty(link, ROOM_URL)
        
        try:
            file_path.unlink()
            print(f'\n🗑️ File asli di Google Drive berhasil dihapus: {file_path.name}')
            print('✅ Skenario Ultimate selesai dengan sempurna!')
        except Exception as e:
            print(f'\n⚠️ Link berhasil didapatkan, tapi gagal menghapus file di Drive: {e}')
    else:
        print('\n❌ Upload gagal, diblokir server, atau link tidak valid.')
        print(f'⚠️ File "{file_path.name}" TIDAK dihapus dari Google Drive demi keamanan.')

if __name__ == '__main__':
    main()
