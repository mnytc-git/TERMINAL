{ pkgs, ... }: {
  channel = "stable-24.05";
  packages = [ pkgs.docker ];
  
  services.docker.enable = true;
  
  env = { };
  
  idx = {
    extensions = [ "ms-azuretools.vscode-docker" ];
    
    workspace = {
      
      onCreate = {
        default.openFiles = [ ".idx/dev.nix" "README.md" ];
      };
      
      onStart = {

        prepull-kali = ''
          docker pull kalilinux/kali-rolling || true
        '';

        inject-bashrc = ''
          # Cek apakah script sudah ada di bashrc host agar tidak duplikat
          if ! grep -q "KALI_NAME=\"kali-persistent\"" ~/.bashrc; then
            
            cat << 'EOF' >> ~/.bashrc

# --- KALI LINUX AUTO-START LOGIC ---
if [[ $- == *i* ]]; then
    KALI_NAME="kali-persistent"

    # 1. Cek & Jalankan Container
    if ! docker ps --format '{{.Names}}' | grep -q "^$KALI_NAME$"; then
        docker start $KALI_NAME > /dev/null 2>&1 || docker run -t -d --name $KALI_NAME --hostname Bang -v "$(pwd)":/kali -w /kali kalilinux/kali-rolling > /dev/null
    fi

    # 2. Setup Dasar (Fastfetch & Python venv) - Cepat
    if ! docker exec $KALI_NAME test -f /root/.setup_basic_done; then
        echo "⚙️  Setup dasar (Update & Venv)..."
        docker exec $KALI_NAME apt update > /dev/null 2>&1
        docker exec $KALI_NAME apt install -y fastfetch python3-venv > /dev/null 2>&1
        docker exec $KALI_NAME touch /root/.setup_basic_done
    fi

    # 3. INSTALASI TOOLS BERAT (Hacking Tools) - Hanya jalan jika belum ada
    if ! docker exec $KALI_NAME test -f /root/.full_tools_installed; then
        echo "======================================================"
        echo "🚀 Mendeteksi instalasi pertama..."
        echo "📦 Sedang menginstall Tools Hacking & Dependensi..."
        echo "☕ Ini akan memakan waktu lumayan lama, mohon tunggu..."
        echo "======================================================"
        
        # Jalankan Install
        docker exec -e DEBIAN_FRONTEND=noninteractive $KALI_NAME bash -c "apt update && apt install -y git curl wget nano zip unzip sqlmap wpscan joomscan htop whatweb dirsearch nikto wafw00f ffuf nuclei zaproxy speedtest-cli finalrecon subfinder httpx-toolkit naabu amass python3-pip golang-go nmap"
        
        if [ $? -eq 0 ]; then
            docker exec $KALI_NAME touch /root/.full_tools_installed
            echo "✅ Instalasi Tools Selesai!"
            sleep 2 # Jeda sebentar agar user sempat baca tulisan selesai
        else
            echo "❌ Terjadi kesalahan saat install tools."
        fi
    fi

    # 4. Buat Python venv jika folder 'myenv' belum ada
    if ! docker exec $KALI_NAME test -d /kali/myenv; then
        echo "🐍 Membuat Python Virtual Environment (myenv)..."
        docker exec $KALI_NAME python3 -m venv /kali/myenv
    fi

    # 5. Konfigurasi .bashrc Internal Container
    if ! docker exec $KALI_NAME grep -q "Government Bang" /root/.bashrc; then
        docker exec $KALI_NAME sed -i '/fastfetch/d' /root/.bashrc
        docker exec $KALI_NAME sed -i '/activate/d' /root/.bashrc
        docker exec $KALI_NAME bash -c "echo 'source /kali/myenv/bin/activate' >> /root/.bashrc"
        docker exec $KALI_NAME bash -c "echo \"fastfetch | sed 's/Google Compute Engine/Government Bang/g'\" >> /root/.bashrc"
    fi

    # 6. BERSIHKAN LAYAR & MASUK
    # Perintah 'clear' di sini akan menghapus semua output log install di atas
    clear
    
    exec docker exec -it $KALI_NAME /bin/bash
fi
# -----------------------------------

EOF
          fi
        '';
      };
    };
  };
}
