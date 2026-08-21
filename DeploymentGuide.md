# Comprehensive Deployment Guide: miniRAG on AWS Lightsail VPS

This guide will walk you through the entire process of deploying the miniRAG project on an AWS Lightsail VPS, from creating an account to setting up automated CI/CD pipelines.

---

## Step 1: Create an AWS Account

1. Go to the [AWS Console](https://aws.amazon.com/) and click **"Create an AWS Account"**.
2. Follow the on-screen instructions (you'll need an email, phone number for verification, and a valid credit card).
3. Once your account is active, log in to the AWS Management Console as a Root or IAM user.

---

## Step 2: Create a Lightsail VPS Instance

1. In the AWS Console search bar at the top, type **"Lightsail"** and click on it.
2. Click **"Create instance"**.
3. **Select Platform:** Choose **Linux/Unix**.
4. **Select Blueprint:** Choose **OS Only** > **Ubuntu 24.04 LTS** (or 22.04 LTS).
5. **Add Launch Script (Optional):** You can skip this.
6. **Change SSH Key Pair:** Keep the default key pair, or click "Create new" to generate one. **Download the private key (`.pem` file) if you create a new one**. You will need this to connect!
7. **Choose your Instance Plan:** Given the stack (PostgreSQL, Vector DB, RabbitMQ, Redis, etc.), select a plan with at least **4GB RAM** (8GB recommended for production).
8. **Name your instance:** e.g., `minirag-prod`.
9. Click **"Create instance"**. Wait a few minutes for the status to change from *Pending* to *Running*.

---

## Step 3: Connect (SSH) to Your Instance

### Option 1: Browser-based SSH (Easiest)
1. On the Lightsail dashboard, click the **orange terminal icon** next to your instance name.
2. A browser window will open, giving you direct SSH access.

### Option 2: Using your Terminal/Command Prompt (Recommended)
1. Open your local terminal (macOS/Linux) or PowerShell (Windows).
2. Ensure your downloaded `.pem` key has the correct permissions:

   **For macOS/Linux:**
   ```bash
   chmod 400 your-key.pem
   ```

   **For Windows (PowerShell):**
   ```powershell
   # Remove inherited permissions
   icacls your-key.pem /inheritance:r
   # Grant read access to your current user
   icacls your-key.pem /grant:r "$env:USERNAME`:(R)"
   ```

3. Connect using the Public IP shown on your Lightsail dashboard:

   **For macOS/Linux:**
   ```bash
   ssh -i /path/to/your-key.pem ubuntu@<YOUR_LIGHTSAIL_PUBLIC_IP>
   ```

   **For Windows (PowerShell/Command Prompt):**
   ```powershell
   ssh -i "C:\path\to\your-key.pem" ubuntu@<YOUR_LIGHTSAIL_PUBLIC_IP>
   ```

---

## Step 4: Attach a Static IP & Link Your Domain

By default, the Public IP can change if the instance restarts. We need a Static IP.

1. **Create Static IP:** In the Lightsail dashboard, go to the **Networking** tab. Click **"Create static IP"**. Attach it to your `minirag-prod` instance.
2. **Link Domain (DNS):**
   - Go to your Domain Registrar (e.g., GoDaddy, Namecheap, Cloudflare).
   - Go to the **DNS Management / DNS Records** page.
   - Add an **A Record**:
     - **Name/Host:** `@` (or your subdomain, like `app`)
     - **Value/Target:** `<YOUR_STATIC_IP>`
     - **TTL:** Auto / 3600

> [!TIP]
> DNS propagation can take anywhere from a few minutes to a few hours.

---

## Step 5: Install Dependencies (Docker, Git, Python)

Once logged into your server via SSH, update your system and install necessary packages.

### 1. Update system & install prerequisites
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg lsb-release git ufw python3-pip python3-venv
```

### 2. Install Docker & Docker Compose
```bash
# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 3. Add user to Docker group (so you don't need `sudo` for docker)
```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## Step 6: Clone the Repository & Configure the Project

### 1. Create a workspace & clone
```bash
mkdir -p ~/workspace
cd ~/workspace
git clone https://github.com/your-username/miniRag-Almahil-Solutions.git miniRag
cd miniRag
```
*(You may need to set up a GitHub Personal Access Token if the repo is private).*

### 2. Configure Environment Variables
You need to create your `.env` files inside the `env/` directory as required by `docker-compose.yml`.
```bash
mkdir -p env
# Create your .env files based on your project's .env.template files
nano env/.env.fastapi-app
nano env/.env.postgres
# ... create the rest (.env.redis, .env.rabbitmq, etc.)
```
*Ensure you put your secure passwords, API keys, and database URLs in these files.*

---

## Step 7: Build and Run the Docker Containers

Because the project relies heavily on `docker-compose.yml`, everything (FastAPI, Vite Frontend, Nginx, PostgreSQL, Qdrant) will be spun up together.

```bash
# Navigate to the docker directory if that's where the compose file is run from, or run from root:
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d
```

Check the status of your containers to ensure they are healthy:
```bash
docker compose -f docker/docker-compose.yml ps
```

> [!NOTE]
> Since Nginx is part of your Docker stack mapped to ports `80` and `443`, navigating to your Static IP or Domain in a web browser will now route traffic to the Vite frontend and FastAPI backend accordingly.

---

## Step 8: Setup HTTPS (SSL Certificates)

Your `docker-compose.yml` mounts `./nginx/ssl` to `/etc/nginx/ssl`. We need to generate Let's Encrypt certificates.

Temporarily stop Nginx, run Certbot, and move the certs:
```bash
sudo apt install certbot -y
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Create the SSL directory if it doesn't exist
mkdir -p ~/workspace/miniRag/docker/nginx/ssl

# Copy the generated certs into your project's SSL directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ~/workspace/miniRag/docker/nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ~/workspace/miniRag/docker/nginx/ssl/

# Restart Nginx
docker compose -f docker/docker-compose.yml restart nginx
```

---

## Step 9: Setup CI/CD with GitHub Actions

Your project has a `deploy-main.yml` workflow which SSHes into the server as `github_user` to restart services. Let's set that up.

### 1. Create the `github_user` on your VPS
Run the following on your server:
```bash
sudo adduser --disabled-password --gecos "" github_user
sudo usermod -aG docker github_user
```

### 2. Generate SSH Keys for `github_user`
```bash
sudo su - github_user
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 3. Retrieve the Private Key
Still as `github_user`, print the private key and **copy the entire output**:
```bash
cat ~/.ssh/id_ed25519
```
*Type `exit` to return to your normal `ubuntu` user.*

### 4. Give `github_user` permission to the workspace
```bash
sudo chown -R github_user:github_user /home/github_user/workspace/miniRag
```
*(If you cloned it in your ubuntu home dir, move it: `sudo mv ~/workspace /home/github_user/ && sudo chown -R github_user:github_user /home/github_user/workspace`)*

### 5. Setup Systemd Service (Optional but required for your current CI/CD script)
Your `deploy-main.yml` calls `sudo systemctl restart minirag.service`. Let's create it.
```bash
sudo nano /etc/systemd/system/minirag.service
```
Paste the following:
```ini
[Unit]
Description=MiniRAG Docker Compose Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/github_user/workspace/miniRag
ExecStart=/usr/bin/docker compose -f docker/docker-compose.yml up -d --build
ExecStop=/usr/bin/docker compose -f docker/docker-compose.yml down
User=github_user

[Install]
WantedBy=multi-user.target
```
Enable it and give `github_user` passwordless sudo rights *just* for restarting this service:
```bash
sudo systemctl enable minirag.service
sudo visudo
# Add this line at the bottom:
github_user ALL=(ALL) NOPASSWD: /bin/systemctl restart minirag.service
```

### 6. Add GitHub Secrets
1. Go to your repository on GitHub.
2. Navigate to **Settings** > **Secrets and variables** > **Actions**.
3. Click **"New repository secret"**.
4. Add the following secrets:
   - **Name:** `SSH_MAIN_HOST_IP`
     - **Secret:** `<Your-Lightsail-Static-IP>`
   - **Name:** `SSH_MAIN_PRIVATE_KEY`
     - **Secret:** *(Paste the entire `id_ed25519` private key you copied earlier)*

### Conclusion
Your VPS is now fully configured! Every time you push to the `main` branch, GitHub Actions will securely SSH into your Lightsail server, pull the latest code, and restart the Docker containers.
