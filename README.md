# QR-Based Cardless ATM Withdrawal System

A Flask prototype that lets a user withdraw cash from a simulated ATM without a physical card, using a dynamic QR code and PIN authentication.

## Tech Stack
Python, Flask, JavaScript, HTML, CSS

## Features
- Dynamic QR token generated for every withdrawal session (random, expires in 60 seconds)
- PIN authentication (PIN stored as a hash, not plain text)
- Replay-attack prevention: each QR token works only once and is blocked after 3 wrong PIN attempts
- Balance verification before a withdrawal is approved
- Simulated cash dispensing, split into 500 / 200 / 100 notes

## How It Works
1. The ATM screen (`/`) shows a QR code containing a one-time link.
2. The user scans it with a phone, which opens the withdrawal page.
3. The user enters the PIN and an amount.
4. The server checks the token, PIN and balance, then marks the token as used.
5. The ATM screen shows the simulated cash dispensing.

## Getting Started
```bash
git clone https://github.com/KallepalliNamitha/qr-cardless-atm.git
cd qr-cardless-atm
pip3 install -r requirements.txt
python3 app.py
```
Open http://127.0.0.1:5000 on your computer to see the ATM screen.

To scan with a phone, connect the phone to the same Wi-Fi, then open `http://<your-computer-IP>:5000` on the computer instead, so the QR code points to an address your phone can reach.

**Demo account:** PIN `1234`, starting balance Rs. 10,000. Data is stored in memory and resets when the server restarts.

## Note
This is a learning prototype. It simulates an ATM and does not connect to any bank.

## Author
Kallepalli Namitha Lakshmi Priya - [LinkedIn](https://linkedin.com/in/namitha-lakshmi-priya-kallepalli)
