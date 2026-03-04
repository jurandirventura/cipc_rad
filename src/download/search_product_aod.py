import requests

headers = {
    "Authorization": f"Bearer {access_token}"
}

query = """
https://catalogue.dataspace.copernicus.eu/odata/v1/Products?
$filter=Collection/Name eq 'SENTINEL-5P'
and contains(Name,'AER_AI')
and ContentDate/Start gt 2025-01-01T00:00:00.000Z
and ContentDate/Start lt 2025-12-31T23:59:59.999Z
"""

r = requests.get(query, headers=headers)
products = r.json()["value"]

print(f"{len(products)} produtos encontrados")
