{ pkgs, ... }: {
  channel = "stable-24.05";
  packages = [ pkgs.docker ];
  
  services.docker.enable = true;
  
  env = { };
  
  idx = {
    extensions = [ "ms-azuretools.vscode-docker" ];
    
    workspace = {
      
      onCreate = {
        default.openFiles = [ "README.md" ];

        setup-kali-config = ''
          
          if ! grep -q "KALI_NAME=\"Bang\"" ~/.bashrc; then
            
            cat << 'EOF' >> ~/.bashrc

if [[ $- == *i* ]]; then

    KALI_NAME="Bang" 
    # -------------------------

    if ! docker info > /dev/null 2>&1; then
        sleep 1
    fi

    if ! docker ps --format '{{.Names}}' | grep -q "^$KALI_NAME$"; then
        docker start $KALI_NAME > /dev/null 2>&1 || docker run -t -d --name $KALI_NAME --hostname Bang -v "$(pwd)":/kali -w /kali kalilinux/kali-rolling > /dev/null
    fi

    if ! docker exec $KALI_NAME test -f /root/.setup_basic_done; then
        echo "⚙️  Setup dasar (Update & Venv)..."
        docker exec $KALI_NAME apt update > /dev/null 2>&1
        docker exec $KALI_NAME apt install -y fastfetch python3-venv > /dev/null 2>&1
        docker exec $KALI_NAME touch /root/.setup_basic_done
    fi

    if ! docker exec $KALI_NAME test -f /root/.full_tools_installed; then
        echo "======================================================"
        echo "🚀 Mendeteksi instalasi pertama untuk container: $KALI_NAME..."
        echo "📦 Sedang menginstall Tools Hacking..."
        echo "======================================================"

        docker exec -e DEBIAN_FRONTEND=noninteractive $KALI_NAME bash -c "apt update && apt install -y git"
        
        if [ $? -eq 0 ]; then
            docker exec $KALI_NAME touch /root/.full_tools_installed
            echo "✅ Instalasi Selesai!"
            sleep 2
        else
            echo "❌ Gagal install tools. Coba restart environment."
        fi
    fi

    if ! docker exec $KALI_NAME test -d /kali/myenv; then
        echo "🐍 Membuat Python Venv..."
        docker exec $KALI_NAME python3 -m venv /kali/myenv
    fi

    if ! docker exec $KALI_NAME grep -q "Government Bang" /root/.bashrc; then
        docker exec $KALI_NAME sed -i '/fastfetch/d' /root/.bashrc
        docker exec $KALI_NAME sed -i '/activate/d' /root/.bashrc
        docker exec $KALI_NAME bash -c "echo 'source /kali/myenv/bin/activate' >> /root/.bashrc"
        docker exec $KALI_NAME bash -c "echo \"fastfetch | sed 's/Google Compute Engine/Government Bang/g'\" >> /root/.bashrc"
    fi

    clear
    exec docker exec -it $KALI_NAME /bin/bash
fi
EOF
          fi
        '';
      };
      
      onStart = { };
    };
  };
}
