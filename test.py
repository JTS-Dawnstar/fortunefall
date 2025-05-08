from pyscript import fetch

data = await fetch("https://corsproxy.io/?url=https://example.com").text()
