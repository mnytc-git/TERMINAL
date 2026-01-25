{ pkgs, ... }: 
let
  # We define the Kali logic as a separate package/script.
  # This prevents quoting/escaping errors in the main config.
  kaliSetupScript = pkgs.writeShellScriptBin "init-kali" ''
    # Only run in interactive mode
    if [[ $- != *i* ]]; then return; fi

    KALI_NAME="kali-persistent"
    
    # Wait for Docker Daemon (prevents crash on startup)
    until docker info > /dev/null 2>&1; do
       echo "⏳ Waiting for Docker daemon..."
       sleep 1
    done

    # Start Kali if not running
    if ! docker ps --format '{{.Names}}' | grep -q "^$KALI_NAME$"; then
        docker start $KALI_NAME > /dev/null 2>&1 || docker run -t -d --name $KALI_NAME --hostname Bang -v "$(pwd)":/kali -w /kali kalilinux/kali-rolling > /dev/null
    fi

    # Basic Setup (Update & Venv)
    if ! docker exec $KALI_NAME test -f /root/.setup_basic_done; then
        echo "⚙️  Setup dasar (Update & Venv)..."
        docker exec $KALI_NAME apt update > /dev/null 2>&1
        docker exec $KALI_NAME apt install -y fastfetch python3-venv > /dev/null 2>&1
        docker exec $KALI_NAME touch /root/.setup_basic_done
    fi

    # Full Tools Installation
    if ! docker exec $KALI_NAME test -f /root/.full_tools_installed; then
        echo "======================================================"
        echo "🚀 Mendeteksi instalasi pertama..."
        echo "📦 Sedang menginstall Tools Hacking..."
        echo "======================================================"

        docker exec -e DEBIAN_FRONTEND=noninteractive $KALI_NAME bash -c "apt update && apt install -y git sudo golang"
        
        if [ $? -eq 0 ]; then
            docker exec $KALI_NAME touch /root/.full_tools_installed
            echo "✅ Instalasi Selesai!"
            sleep 2
        else
            echo "❌ Gagal install tools. Coba restart environment."
        fi
    fi

    # Python Venv Setup
    if ! docker exec $KALI_NAME test -d /kali/myenv; then
        echo "🐍 Membuat Python Venv..."
        docker exec $KALI_NAME python3 -m venv /kali/myenv
    fi

    # Configure Container .bashrc
    if ! docker exec $KALI_NAME grep -q "Government Bang" /root/.bashrc; then
        docker exec $KALI_NAME sed -i '/fastfetch/d' /root/.bashrc
        docker exec $KALI_NAME sed -i '/activate/d' /root/.bashrc
        docker exec $KALI_NAME bash -c "echo 'source /kali/myenv/bin/activate' >> /root/.bashrc"
        docker exec $KALI_NAME bash -c "echo \"fastfetch | sed 's/Google Compute Engine/Government Bang/g'\" >> /root/.bashrc"
    fi

    # Hijack Shell - clear screen first
    clear
    echo "🔓 Masuk ke Kali Linux..."
    exec docker exec -it $KALI_NAME /bin/bash
  '';

in {
  channel = "stable-24.05";
  
  packages = [ 
    pkgs.docker
    kaliSetupScript # Install our custom script
  ];
  
  services.docker.enable = true;
  
  env = { };
  
  idx = {
    extensions = [ "ms-azuretools.vscode-docker" ];
    
    workspace = {
      onCreate = {
        default.openFiles = [ "README.md" ];
        
        # SCRIPT YANG LEBIH AMAN
        # Kita hanya inject perintah untuk menjalankan script di atas
        setup-kali-hook = ''
          # Pastikan file ada untuk mencegah error grep
          touch ~/.bashrc
          
          if ! grep -q "init-kali" ~/.bashrc; then
            echo "source ${kaliSetupScript}/bin/init-kali" >> ~/.bashrc
          fi
        '';
      };
      
      onStart = { 
        # Optional: Ensure permissions are correct on start
      };
    };
  };
}
