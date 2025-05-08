from pyscript import fetch, display

print("this is a thing")
display("this thing is being displayed")

data = await fetch("https://corsproxy.io/?url=https://example.com").text()

print(data)
display(data)
