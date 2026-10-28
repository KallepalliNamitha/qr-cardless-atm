"""QR-Based Cardless ATM Withdrawal System (prototype).

Flow:
1. The ATM screen (/) generates a dynamic, single-use QR token that expires in 60 seconds.
2. The user scans the QR code with a phone, which opens /scan/<token>.
3. The user enters their PIN and an amount.
4. The server verifies the token, PIN and balance, then simulates dispensing cash.

This is a learning prototype: data is kept in memory and resets when the server restarts.
"""
import base64
import io
import secrets
import time

import qrcode
from flask import Flask, jsonify, render_template_string, request
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

TOKEN_LIFETIME_SECONDS = 60
MAX_PIN_ATTEMPTS = 3
NOTES = (500, 200, 100)  # note denominations used for simulated dispensing

# Demo account (the PIN is stored as a hash, never as plain text). Demo PIN: 1234
account = {
    "name": "Demo User",
    "balance": 10000,
    "pin_hash": generate_password_hash("1234"),
}

# token -> {"expires": float, "used": bool, "attempts": int, "result": dict | None}
tokens = {}


# ---------- Helpers ----------
def new_token():
    """Create a random, hard-to-guess, single-use token."""
    token = secrets.token_urlsafe(16)
    tokens[token] = {
        "expires": time.time() + TOKEN_LIFETIME_SECONDS,
        "used": False,
        "attempts": 0,
        "result": None,
    }
    return token


def check_token(token):
    """Return (token_record, None) if usable, else (None, error_message)."""
    record = tokens.get(token)
    if record is None:
        return None, "Invalid QR code."
    if record["used"]:
        return None, "This QR code has already been used."  # replay-attack prevention
    if time.time() > record["expires"]:
        return None, "This QR code has expired. Please generate a new one at the ATM."
    if record["attempts"] >= MAX_PIN_ATTEMPTS:
        return None, "Too many wrong PIN attempts. This QR code is blocked."
    return record, None


def qr_image_data_uri(text):
    image = qrcode.make(text)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def split_into_notes(amount):
    """Simulate cash dispensing: greedy split into note denominations."""
    result = {}
    for note in NOTES:
        count, amount = divmod(amount, note)
        if count:
            result[note] = count
    return result


# ---------- Pages ----------
PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>QR Cardless ATM</title>
  <style>
    body { font-family: system-ui, sans-serif; background:#0f172a; color:#e2e8f0;
           display:flex; justify-content:center; padding:24px; }
    .card { background:#1e293b; border-radius:16px; padding:28px; width:100%; max-width:420px;
            text-align:center; }
    h1 { font-size:1.3rem; margin-top:0; }
    img { background:white; padding:10px; border-radius:12px; width:240px; height:240px; }
    input, button { width:100%; padding:12px; margin:8px 0; border-radius:8px; border:0;
                    font-size:1rem; box-sizing:border-box; }
    button { background:#22c55e; color:#052e16; font-weight:600; cursor:pointer; }
    .error { background:#7f1d1d; padding:10px; border-radius:8px; }
    .ok { background:#14532d; padding:10px; border-radius:8px; }
    .muted { color:#94a3b8; font-size:.9rem; }
  </style>
</head>
<body><div class="card">{{ body|safe }}</div></body>
</html>
"""

ATM_BODY = """
<h1>QR Cardless ATM</h1>
<div id="waiting">
  <p>Scan this QR code with your phone to start a withdrawal.</p>
  <img src="{{ qr }}" alt="QR code">
  <p class="muted">Expires in <span id="timer">{{ lifetime }}</span> seconds</p>
</div>
<div id="done" style="display:none"></div>
<script>
  let left = {{ lifetime }};
  const token = "{{ token }}";
  const timer = document.getElementById("timer");
  const tick = setInterval(() => {
    left -= 1; timer.textContent = Math.max(left, 0);
    if (left <= 0) { clearInterval(tick); location.reload(); }
  }, 1000);
  const poll = setInterval(async () => {
    const data = await (await fetch("/status/" + token)).json();
    if (data.state === "dispensed") {
      clearInterval(poll); clearInterval(tick);
      document.getElementById("waiting").style.display = "none";
      const box = document.getElementById("done");
      const notes = Object.entries(data.notes).map(([n, c]) => c + " x " + n).join(", ");
      box.innerHTML = '<div class="ok"><h2>Dispensing cash...</h2><p>Rs. ' + data.amount +
        '</p><p class="muted">' + notes + '</p><p>Remaining balance: Rs. ' + data.balance +
        '</p></div><button onclick="location.reload()">New withdrawal</button>';
      box.style.display = "block";
    }
  }, 2000);
</script>
"""

FORM_BODY = """
<h1>Withdraw cash</h1>
<p class="muted">Hello, {{ name }}</p>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="post" action="/withdraw">
  <input type="hidden" name="token" value="{{ token }}">
  <input type="password" name="pin" inputmode="numeric" maxlength="4" placeholder="4-digit PIN" required>
  <input type="number" name="amount" min="100" step="100" placeholder="Amount (multiples of 100)" required>
  <button type="submit">Withdraw</button>
</form>
"""

MESSAGE_BODY = """
<h1>{{ title }}</h1>
<div class="{{ css }}">{{ message }}</div>
"""


def render_page(body_template, **context):
    body = render_template_string(body_template, **context)
    return render_template_string(PAGE, body=body)


def message_page(title, message, ok=False):
    return render_page(MESSAGE_BODY, title=title, message=message, css="ok" if ok else "error")


# ---------- Routes ----------
@app.route("/")
def atm_screen():
    token = new_token()
    scan_url = request.host_url + "scan/" + token
    return render_page(
        ATM_BODY, qr=qr_image_data_uri(scan_url), token=token, lifetime=TOKEN_LIFETIME_SECONDS
    )


@app.route("/scan/<token>")
def scan(token):
    record, error = check_token(token)
    if error:
        return message_page("Cannot continue", error)
    return render_page(FORM_BODY, name=account["name"], token=token, error=None)


@app.route("/withdraw", methods=["POST"])
def withdraw():
    token = request.form.get("token", "")
    record, error = check_token(token)
    if error:
        return message_page("Cannot continue", error)

    pin = request.form.get("pin", "")
    try:
        amount = int(request.form.get("amount", ""))
    except ValueError:
        return render_page(FORM_BODY, name=account["name"], token=token, error="Enter a valid amount.")

    if amount < 100 or amount % 100 != 0:
        return render_page(FORM_BODY, name=account["name"], token=token,
                           error="Amount must be a multiple of 100.")

    # PIN authentication
    if not check_password_hash(account["pin_hash"], pin):
        record["attempts"] += 1
        left = MAX_PIN_ATTEMPTS - record["attempts"]
        if left <= 0:
            return message_page("Blocked", "Too many wrong PIN attempts. This QR code is blocked.")
        return render_page(FORM_BODY, name=account["name"], token=token,
                           error=f"Wrong PIN. {left} attempt(s) left.")

    # Balance verification
    if amount > account["balance"]:
        return render_page(FORM_BODY, name=account["name"], token=token,
                           error=f"Insufficient balance. Available: Rs. {account['balance']}.")

    # Success: burn the token so it can never be used again
    record["used"] = True
    account["balance"] -= amount
    record["result"] = {
        "amount": amount,
        "notes": split_into_notes(amount),
        "balance": account["balance"],
    }
    return message_page("Success", f"Rs. {amount} approved. Collect your cash from the ATM.", ok=True)


@app.route("/status/<token>")
def status(token):
    record = tokens.get(token)
    if record is None:
        return jsonify(state="invalid")
    if record["result"]:
        return jsonify(state="dispensed", **record["result"])
    if time.time() > record["expires"]:
        return jsonify(state="expired")
    return jsonify(state="waiting")


if __name__ == "__main__":
    # host="0.0.0.0" lets your phone reach the app over the same Wi-Fi network
    app.run(host="0.0.0.0", port=5000, debug=True)
