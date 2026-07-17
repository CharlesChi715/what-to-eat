# AI Worklog

Newest first. One entry per completed deliverable.

17/07/2026. Set up wireless access from my iMac to files on my Windows PC by exposing a WSL2 Python HTTP server over the local Wi-Fi network:

    I’m not exactly sure if this was the exact step：
    
1. In WSL2, start the server:
   cd ~/temp
   python3 -m http.server 8000

2. In Windows, set the Wi-Fi network to Private which lower restrictions of communication through wifi:
   Settings > Network & internet > Wi-Fi > your network > Network profile > Private

3. Open Windows PowerShell as Administrator.

4. Allow inbound traffic on port 8000:
   New-NetFirewallRule -DisplayName "Python HTTP 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

5. Get the WSL2 IP address in powerShell or ipconfig:
   $wslIp = (wsl hostname -I).Trim().Split()[0]
   $wslIp

6. Forward Windows port 8000 to WSL2:
   netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8000 connectaddress=$wslIp connectport=8000

7. Check the forwarding rule:
   netsh interface portproxy show all

8. From the iMac, open:
   http://192.168.0.12:8000

If it stops working after a WSL restart, recreate step 6 because the WSL IP can change.