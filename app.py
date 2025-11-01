from flask import Flask, render_template, request, jsonify
import json
import paho.mqtt.client as mqtt
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# MQTT
broker = "10.69.133.120"  # Use "localhost" if broker runs on same Pi
port = 1883
client = mqtt.Client(client_id="POS_Client", protocol=mqtt.MQTTv311)
try:
    client.connect(broker, port, 60)
    print("MQTT Connected")
except Exception as e:
    print(" MQTT connection failed:", e)


kitchen_items = {
    "Annapoornai": {"Dosa": 30, "Idly": 20, "Vadai": 15, "Chapathi": 25, "Poori": 30},
    "PFC": {"Pizza": 120, "Burger": 90, "Fries": 60, "Pasta": 100, "Sandwich": 70}
}

#  Order Number
order_file = "order_no.txt"

def get_next_order_no():
    """Retrieve and increment order number."""
    if os.path.exists(order_file):
        with open(order_file, "r") as f:
            try:
                order_no = int(f.read().strip()) + 1
            except ValueError:
                order_no = 100
    else:
        order_no = 100
    with open(order_file, "w") as f:
        f.write(str(order_no))
    return order_no

# Email Function
    def send_email(to_email, subject, html_body):
    sender_email = "prasannaproject1245@gmail.com"
    sender_password = "dibh lnce snog yvcr"  # Gmail app password

    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        print(" Email sent successfully!")
    except Exception as e:
        print(" Email sending failed:", e)

# Flask Routes 
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = request.get_json()
        order_list = data.get("order", [])
        customer_email = data.get("email", "")
        order_no = get_next_order_no()

        total_amount = 0
        kitchen_orders = {stall: {"order_no": order_no} for stall in kitchen_items}

        html_rows = ""
        for item in order_list:
            name = item["name"]
            qty = int(item["qty"])
            price = int(item["price"])
            total = qty * price
            total_amount += total

 # Assign to correct stall
            for stall, items in kitchen_items.items():
                if name in items:
                    kitchen_orders[stall][name] = qty
                    html_rows += f"""
                    <tr>
                        <td>{name}</td>
                        <td>{qty}</td>
                        <td>₹{price}</td>
                        <td>₹{total}</td>
                        <td>{stall}</td>
                    </tr>
                    """

        
        for stall, orders in kitchen_orders.items():
            if len(orders) > 1:
                topic = f"kitchen/{stall.replace(' ', '_')}/orders"
                client.publish(topic, json.dumps(orders))

        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
        <h2>🧾 Order Bill - #{order_no}</h2>
        <table border="1" cellspacing="0" cellpadding="8" style="border-collapse: collapse; width: 100%;">
        <tr style="background-color: #f2f2f2;">
            <th>Item</th><th>Qty</th><th>Price</th><th>Total</th><th>From Stall</th>
        </tr>
        {html_rows}
        </table>
        <h3 style="text-align:right;">Total Amount: ₹{total_amount}</h3>
        <p>Thank you for ordering from <b>Smart Food Court!</b></p>
        </body>
        </html>
        """
  
        if customer_email:
            send_email(customer_email, f"Order #{order_no} Confirmation", html_body)

        return jsonify({"message": f" Order #{order_no} processed. Total ₹{total_amount}."})

    return render_template("index.html", kitchen_items=kitchen_items)

# ---------------- Run Flask ----------------
if __name__ == "__main__":

    app.run(host="0.0.0.0", port=8080, debug=True)
