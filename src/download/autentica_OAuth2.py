import requests

# Credenciais
username = "SEU_USUARIO"
password = "SUA_SENHA"

# Endpoint de token
token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

data = {
    "client_id": "cdse-public",
    "grant_type": "password",
    "username": username,
    "password": password,
}

response = requests.post(token_url, data=data)
access_token = response.json()["access_token"]

print("Token obtido com sucesso.")
