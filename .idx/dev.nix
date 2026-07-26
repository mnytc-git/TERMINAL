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

    echo -ne "\033]0;Bang\007"

    if ! docker info > /dev/null 2>&1; then
        sleep 1
    fi

    if ! docker ps --format '{{.Names}}' | grep -q "^$KALI_NAME$"; then

        docker start $KALI_NAME > /dev/null 2>&1 || docker run -t -d --name $KALI_NAME --hostname Bang -v "$(pwd)":/kali -w /kali kalilinux/kali-rolling > /dev/null
    fi

    if ! docker exec $KALI_NAME test -f /root/.setup_basic_done; then
        echo "⚙️  Setup dasar (Fastfetch & Venv)..."
        docker exec $KALI_NAME apt update > /dev/null 2>&1
        docker exec $KALI_NAME apt install -y fastfetch python3-venv > /dev/null 2>&1
        docker exec $KALI_NAME touch /root/.setup_basic_done
    fi

    if ! docker exec $KALI_NAME test -d /kali/myenv; then
        echo "🌐 Mengaktifkan Tor & Proxychains (Instant Retry Mode)..."
        docker exec -e DEBIAN_FRONTEND=noninteractive $KALI_NAME apt update > /dev/null 2>&1
        docker exec -e DEBIAN_FRONTEND=noninteractive $KALI_NAME apt install -y tor proxychains4 netcat-openbsd > /dev/null 2>&1
        
        # Konfigurasi Mutlak Tor Service & Auto-Reconnect Tanpa Jeda
        docker exec $KALI_NAME bash -c "
            /etc/init.d/tor stop >/dev/null 2>&1
            pkill -f tor >/dev/null 2>&1
            rm -rf /var/lib/tor/*
            touch /var/lib/tor/tor.log
            chown -R debian-tor:debian-tor /var/lib/tor
            chmod 700 /var/lib/tor

            echo 'SocksPort 127.0.0.1:9050' > /etc/tor/torrc
            echo 'DataDirectory /var/lib/tor' >> /etc/tor/torrc
            echo 'ClientUseIPv6 0' >> /etc/tor/torrc

            /etc/init.d/tor start >/dev/null 2>&1
        "

        # Loop Instan Tanpa Waktu Tunggu Lama (Auto-Reconnect Sampai Nyala)
        echo "🔄 Menghubungkan jalur Tor secara instan..."
        docker exec $KALI_NAME bash -c "
            while ! nc -z 127.0.0.1 9050; do
                /etc/init.d/tor start >/dev/null 2>&1
                sleep 0.2
            done
        "

        echo "🐍 Membuat Python Venv..."
        docker exec $KALI_NAME python3 -m venv /kali/myenv
    fi

    if ! docker exec $KALI_NAME grep -q "Government Bang" /root/.bashrc; then
        docker exec $KALI_NAME sed -i '/fastfetch/d' /root/.bashrc
        docker exec $KALI_NAME sed -i '/activate/d' /root/.bashrc
        docker exec $KALI_NAME bash -c "echo 'source /kali/myenv/bin/activate' >> ~/.bashrc"
        # Custom branding Government Bang
        docker exec $KALI_NAME bash -c "echo \"fastfetch | sed 's/Google Compute Engine/Government Bang/g'\" >> ~/.bashrc"
        
        # Sembunyikan banner proxychains secara total via fungsi bash wrapper
        docker exec $KALI_NAME bash -c "echo 'function proxychains4() { command proxychains4 \"\$@\" 2>/dev/null; }' >> ~/.bashrc"
        docker exec $KALI_NAME bash -c "export -f proxychains4"
    fi

    echo -ne "\033]0;Bang\007"
    
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
