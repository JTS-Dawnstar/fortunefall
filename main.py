from pyscript import fetch

response = await fetch(
    "https://jts-dawnstar.pyscriptapps.com/api-proxy-tutorial-copy/api/proxies/status-check",
    method="OPTIONS"
).json()


print(response)


response = await fetch(
    "https://jts-dawnstar.pyscriptapps.com/api-proxy-tutorial-copy/api/proxies/climate-hourly?StationID=888&Month=10&Day=24&Year=2020",
    method="POST"
).text()

print(response)


# response = await fetch(
#     "https://jts-dawnstar.pyscriptapps.com/api-proxy-tutorial-copy/api/proxies/geeks",
#     method="GET"
# ).text()

# print(response)
