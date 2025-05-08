from pyscript import fetch


response = await fetch("https://corsproxy.io/?url=https://example.com")
if response.ok:
    data = await response.text()
else:
    print(response.status)
