"""Diagnostyka: pokazuje surowe pola z RemoteOK API."""
import json
import requests

url = "https://remoteok.com/api"
headers = {"User-Agent": "JobRadar/1.0 (Automated Job Board Aggregator)"}

resp = requests.get(url, headers=headers, timeout=15)
data = resp.json()

print(f"Typ odpowiedzi: {type(data).__name__}")
print(f"Długość: {len(data)}")
print(f"Pierwszy element (metadane): {json.dumps(data[0], indent=2, ensure_ascii=False)[:500]}")
print()

# Znajdź pierwszą ofertę, która ma jakieś salary_min lub location
for i, item in enumerate(data[1:6], start=1):
    print(f"═══ Oferta #{i} ═══")
    print(f"Klucze dostępne: {sorted(item.keys())}")
    print()
    print(f"  position:        {item.get('position')!r}")
    print(f"  company:         {item.get('company')!r}")
    print(f"  location:        {item.get('location')!r}")
    print(f"  salary_min:      {item.get('salary_min')!r}")
    print(f"  salary_max:      {item.get('salary_max')!r}")
    print(f"  salary:          {item.get('salary')!r}")
    print(f"  date:            {item.get('date')!r}")
    print(f"  epoch:           {item.get('epoch')!r}")
    print(f"  tags:            {item.get('tags')!r}")
    print()