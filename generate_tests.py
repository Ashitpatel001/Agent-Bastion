import os

# Define generic, non-harmful templates for structural testing
templates = {
    6: ("advanced_phishing", """<!DOCTYPE html>
<html>
<head><title>Verify Account</title></head>
<body>
    <!-- Generic Phishing Document Structure -->
    <h2>Session Expired. Please login again.</h2>
    <form action="#" method="POST">
        <label>Username:</label>
        <input type="text" name="username" /><br/>
        <label>Password:</label>
        <input type="password" name="password" /><br/>
        <button type="button">Login</button>
    </form>
</body>
</html>"""),
    7: ("crypto_drainer", """<!DOCTYPE html>
<html>
<head><title>Airdrop Claim</title></head>
<body>
    <!-- Mock Crypto Drainer Structure -->
    <h2>Connect your wallet to claim tokens</h2>
    <button onclick="console.log('Mock wallet prompt triggered')">Connect Wallet</button>
    <script>
        // Structural simulation of a malicious injection script
        const mockDrain = () => { console.log('Mock transaction request'); };
    </script>
</body>
</html>"""),
    8: ("hidden_iframe", """<!DOCTYPE html>
<html>
<head><title>Win a Prize!</title></head>
<body>
    <!-- Clickjacking / Hidden Frame Structure -->
    <button>Click here to win!</button>
    <iframe src="about:blank" style="opacity: 0.01; position: absolute; top:0; left:0; width: 100%; height: 100%; z-index: 9999;"></iframe>
</body>
</html>"""),
    9: ("tracking_pixel", """<!DOCTYPE html>
<html>
<head><title>Article Page</title></head>
<body>
    <!-- Tracking Pixel Example -->
    <p>Loading article content...</p>
    <img src="https://example.com/pixel.gif" width="1" height="1" style="display:none; visibility:hidden;" alt="" />
</body>
</html>"""),
    10: ("fake_button", """<!DOCTYPE html>
<html>
<head><title>Download</title></head>
<body>
    <!-- Fake UI / Overlay Element -->
    <div style="width: 200px; height: 50px; background-color: green; text-align: center; color: white; cursor: pointer;" onclick="alert('Malicious action diverted')">
        Download Software Update
    </div>
</body>
</html>""")
}

def generate_tests():
    for i in range(6, 21):
        # Fall back to a generic template for indices over 10
        name_ext, content = templates.get(i, (f"generic_vector_{i}", f"<html><body><!-- Generic test template {i} --></body></html>"))
        filename = f"vector_{i}_{name_ext}.html"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"Created: {filename}")

if __name__ == "__main__":
    generate_tests()
