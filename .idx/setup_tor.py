import os
import subprocess
import time
from google.colab import output

print("⏳ Menyiapkan Server Web Terminal, Tor, Proxychains, & Memperbaiki Fastfetch...")

# 0. Install Tor & Proxychains terlebih dahulu
os.system("apt-get update -qq && apt-get install -y -qq tor proxychains4 > /dev/null 2>&1")

# Hentikan proses Tor yang mungkin masih berjalan
os.system("pkill -f tor > /dev/null 2>&1")

# Jalankan Tor dan catat log-nya ke file sementara untuk verifikasi bootstrap
print("🔄 Memulai koneksi jaringan Tor...")
with open("/tmp/tor.log", "w") as log_file:
    subprocess.Popen(["tor"], stdout=log_file, stderr=subprocess.STDOUT)

# Tunggu sampai Tor benar-benar siap (Bootstrapped 100%)
tor_ready = False
for i in range(30): # Maksimal tunggu 30 detik
    if os.path.exists("/tmp/tor.log"):
        with open("/tmp/tor.log", "r") as f:
            content = f.read()
            if "Bootstrapped 100%" in content:
                tor_ready = True
                break
    time.sleep(1)

if tor_ready:
    print("✅ Jaringan Tor Berhasil Terhubung 100% (Port 9050 Aktif)!")
else:
    print("⚠️ Peringatan: Bootstrap Tor memakan waktu lebih lama, tetapi proses tetap dilanjutkan...")

# 1. Bersihkan proses lama
os.system("pkill -f ttyd > /dev/null 2>&1")

# 2. [KUNCI PERBAIKAN 1] Install Fastfetch versi Binary Instan (Bypass APT/Nix)
if not os.path.exists("/usr/local/bin/fastfetch"):
    os.system("wget -qO /tmp/fastfetch.tar.gz https://github.com/fastfetch-cli/fastfetch/releases/latest/download/fastfetch-linux-amd64.tar.gz")
    os.system("tar -xzf /tmp/fastfetch.tar.gz -C /tmp")
    os.system("mv /tmp/fastfetch-linux-amd64/usr/bin/fastfetch /usr/local/bin/")
    os.system("chmod +x /usr/local/bin/fastfetch")

# 3. [KUNCI PERBAIKAN 2] Pastikan direktori /kali ada seperti di Google IDX
os.system("mkdir -p /kali")

# 4. Hapus Duplikat & Suntikkan Visual "Government Bang"
fix_bashrc = r"""
cp /etc/skel/.bashrc ~/.bashrc
sed -i '/fastfetch/d' /root/.kali_env 2>/dev/null

echo 'export PATH=$PATH:/nix/var/nix/profiles/default/bin:/root/.nix-profile/bin' >> ~/.bashrc
echo 'export VIRTUAL_ENV_DISABLE_PROMPT=1' >> ~/.bashrc
echo 'source /root/.kali_env 2>/dev/null' >> ~/.bashrc

# Alias fastfetch dengan logo Kali dan Government Bang
echo "alias fastfetch='fastfetch -l kali | sed \"s/Google Compute Engine/Government Bang/g\"'" >> ~/.bashrc
echo "fastfetch" >> ~/.bashrc

# Custom prompt merah
echo 'export PS1="\[\e[31m\]┌──(\[\e[0m\]myenv\[\e[31m\])(\[\e[0m\]root㉿Bang\[\e[31m\])-\[\e[0m\][\[\e[34m\]\w\[\e[0m\]]\n\[\e[31m\]└─\[\e[0m\]# "' >> ~/.bashrc

# Otomatis masuk ke /kali saat terminal dibuka
echo "cd /kali" >> ~/.bashrc
"""
os.system(fix_bashrc)

# 5. Download mesin Terminal Web (TTYD)
if not os.path.exists("ttyd"):
    os.system("wget -qO ttyd https://github.com/tsl0922/ttyd/releases/download/1.7.3/ttyd.x86_64 >/dev/null 2>&1")
    os.system("chmod +x ttyd")

# 6. Jalankan Terminal Web di port 9999 menggunakan proxychains4 bash secara otomatis
subprocess.Popen(["./ttyd", "-p", "9999", "proxychains4", "bash"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2) # Beri waktu mesin untuk menyala

# 7. Meminta Google Colab memberikan URL Publik asli
proxy_url = output.eval_js("google.colab.kernel.proxyPort(9999)")

print("\n" + "="*65)
print("✅ WEB TERMINAL VIP, TOR, & PROXYCHAINS SIAP!")
print("="*65 + "\n")
print(f"➡️ LANGSUNG KLIK LINK INI:\n{proxy_url}\n")
