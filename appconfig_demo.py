from datetime import datetime, timedelta
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from string import Template
import webbrowser
import boto3
from dotenv import load_dotenv
import os

load_dotenv()
WEBSERVER_PORT = 80
APPCONFIG_APPLICATION_NAME = os.getenv("APPCONFIG_APPLICATION_NAME", "default_app")
APPCONFIG_CONFIG_PROFILE_NAME = os.getenv("APPCONFIG_CONFIG_PROFILE_NAME", "default_profile")
APPCONFIG_ENVIRONMENT_NAME = os.getenv("APPCONFIG_ENVIRONMENT_NAME", "default_env")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

cached_config_data = {}
cached_config_token = None
cached_token_expiration_time = None

def get_config():
    global cached_config_token
    global cached_config_data
    global cached_token_expiration_time
    appconfigdata = boto3.client("appconfigdata", region_name=AWS_REGION)

    # If we don't have a token yet, call start_configuration_session to get one
    if not cached_config_token or datetime.now() >= cached_token_expiration_time:
        start_session_response = appconfigdata.start_configuration_session(
            ApplicationIdentifier=APPCONFIG_APPLICATION_NAME,
            EnvironmentIdentifier=APPCONFIG_ENVIRONMENT_NAME,
            ConfigurationProfileIdentifier=APPCONFIG_CONFIG_PROFILE_NAME,
        )
        cached_config_token = start_session_response["InitialConfigurationToken"]

    get_config_response = appconfigdata.get_latest_configuration(
        ConfigurationToken=cached_config_token
    )
    # Response always includes a fresh token to use in next call
    cached_config_token = get_config_response["NextPollConfigurationToken"]
    # Token will expire if not refreshed within 24 hours, so keep track of
    # the expected expiration time minus a bit of padding
    cached_token_expiration_time = datetime.now() + timedelta(hours=23, minutes=59)
    # 'Configuration' in the response will only be populated the first time we
    # call GetLatestConfiguration or if the config contents have changed since
    # the last time we called. So if it's empty we know we already have the latest
    # config, otherwise we need to update our cache.
    content = get_config_response["Configuration"].read()
    if content:
        try:
            cached_config_data = json.loads(content.decode("utf-8"))
            print("received new config data:", cached_config_data)
        except json.JSONDecodeError as error:
            raise ValueError(error.msg) from error

    return cached_config_data

def get_html():
    # For simplicity this code fetches a fresh config from AppConfig every time a page is served.
    config = get_config()
    allow_bitcoin_flag = config["allow-bitcoin-at-checkout"]

    if allow_bitcoin_flag["enabled"]:
        dropdown_display_css = "initial"
        default_currency = allow_bitcoin_flag["default-currency"]
        bitcoinDiscountPercentage = allow_bitcoin_flag.get("bitcoin-discount-percent", 0)
        bitcoinDiscountEndDate = allow_bitcoin_flag.get("bitcoin-discount-end-date", "")
    else:
        default_currency = "USD"
        dropdown_display_css = "none"
        bitcoinDiscountPercentage = 0
        bitcoinDiscountEndDate = ""

    if bitcoinDiscountEndDate:
        discountEndDatetime = datetime.strptime(bitcoinDiscountEndDate, "%d/%m/%Y")
        if datetime.today() > discountEndDatetime:
            bitcoinDiscountPercentage = 0

    usd_selected = "selected='selected'" if default_currency == "USD" else ""
    mmk_selected = "selected='selected'" if default_currency == "MMK" else ""

    html_template = """
<html>
<head>
    <meta content="text/html;charset=utf-8" http-equiv="Content-Type">
    <meta content="utf-8" http-equiv="encoding">
    <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background-color: #121212;
            color: #ffffff;
        }
        .container {
            width: 100%;
            max-width: 500px;
            background-color: #1e1e1e;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #333;
            box-shadow: 0 4px 8px rgba(0,0,0,0.5);
        }
        h1 {
            font-family: 'Bebas Neue', cursive;
            font-size: 2rem;
            text-align: center;
            color: #ff9800;
        }
        .cart {
            width: 100%;
            background-color: #282828;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #444;
        }
        .cart h4 {
            font-size: 1.25rem;
            margin-bottom: 10px;
            color: #fff;
        }
        .cart .price {
            font-size: 1.25rem;
            font-weight: bold;
            color: #ff9800;
        }
        .right {
            float: right;
        }
        #currency {
            margin-right: 5px;
            display: $dropdownDisplayCSS;
            width: 80px;
            background-color: #333;
            color: #fff;
            border: none;
            padding: 5px;
        }
        .total {
            font-size: 1.25rem;
            font-weight: bold;
        }
        @media (max-width: 600px) {
            .container {
                padding: 15px;
            }
            h1 {
                font-size: 1.5rem;
            }
        }
    </style>
    <title>AWS Community Day | AppConfig Demo</title>
</head>
<body onload="dropdownChanged()">
    <div class="container">
        <h1>AWS Community Day AppConfig Demo</h1>
        <div class="cart">
            <h4>Shopping Cart Example</h4>
            Premium Product A <span class="right price"></span>
            <hr>
            <p id="mmk-discount">
                <i>
                    <small>November discount, order using MMK by $bitcoinDiscountEndDate</small>
                    <span class="right">$bitcoinDiscountPercentage%</span>
                </i>
            </p>
            <b>Total:</b>
            <span class="right">
                <select name="currency" id="currency" onchange="dropdownChanged()" autocomplete="off">
                    <option value="USD" $usdSelected>USD</option>
                    <option value="MMK" $mmkSelected>MMK</option>
                </select>
                <span class="total"></span>
            </span>
        </div>
    </div>
</body>
<script>
    function dropdownChanged() {
        currency = "USD"
        if ('$dropdownDisplayCSS' !== 'none') {
            currency = document.getElementById("currency").value;
        }
        if (currency === "USD") {
            currencySymbol="$$";
            price = 50; 
        } else {
            currencySymbol="MMK";
            price = 150000;  
        }
        discount=$bitcoinDiscountPercentage;
        if (discount && currency === "MMK") {
            total = price - (price*discount/100);
            total = total.toFixed(6);
            document.getElementById("mmk-discount").style.display = 'inherit';
        } else {
            total = price;
            document.getElementById("mmk-discount").style.display = 'none';
        }
        document.querySelectorAll(".price").forEach(txt => { txt.textContent = currencySymbol+price; })
        document.querySelectorAll(".total").forEach(txt => { txt.textContent = currencySymbol+total; })
    }
</script>
</html>
    """
    html = Template(html_template).substitute(
        dropdownDisplayCSS=dropdown_display_css,
        usdSelected=usd_selected,
        mmkSelected=mmk_selected,
        bitcoinDiscountPercentage=bitcoinDiscountPercentage,
        bitcoinDiscountEndDate=bitcoinDiscountEndDate,
    )
    return html

class SimpleCheckoutPageWebServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes(get_html(), "utf-8"))

if __name__ == "__main__":
    hostname = "0.0.0.0"
    webServer = HTTPServer((hostname, WEBSERVER_PORT), SimpleCheckoutPageWebServer)
    url = f"http://{hostname}:{WEBSERVER_PORT}"
    print(f"Local webserver started. To view, navigate your browser to: {url}")
    # webbrowser.open(url, new=2)
    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
