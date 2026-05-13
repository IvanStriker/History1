# History1
Сайт с карточками исторических деятелей

## Алгоритм развёртывания сайта на вашем сервере (Linux, Ubuntu):
**1. Установка Docker:**
```bash
sudo apt update
sudo apt upgrade -y

sudo apt install ca-certificates curl gnupg lsb-release -y
sudo mkdir -p /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update

sudo apt install docker-ce docker-ce-cli containerd.io \
docker-buildx-plugin docker-compose-plugin -y

sudo usermod -aG docker $USER

newgrp docker
```
**2. Клонирование репозитория:**
```bash
mkdir server
cd server
git clone https://github.com/IvanStriker/History1.git .
mkdir pgdata
```
**3. Запуск служб:**
```bash
docker compose up -d --build
```