import requests
import psycopg2
import json
import hashlib

def connectDatabase():
    conn_string = "host='localhost' dbname='tesla' user='postgres' password='secret'"
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    print("DB Connected!")
    return conn, cursor

def carIdByVin(vin, cur):
    cur.execute("INSERT INTO cars (vin) VALUES (%s) ON CONFLICT (vin) DO NOTHING", (vin,))
    cur.execute("SELECT carid FROM cars WHERE vin = %s", (vin,))
    carId = cur.fetchone()[0]
    print(carId)
    return carId

def getJsonHash(jsonData):
    json_str = json.dumps(jsonData, sort_keys=True)  # sort_keys for consistent hash values

    json_bytes = json_str.encode('utf-8')

    md5_hash = hashlib.md5(json_bytes)

    return md5_hash.hexdigest()

def insertUpdateData(carId, jsonData, cur):
    jsonHash = getJsonHash(jsonData)
    cur.execute("INSERT INTO updatedata (carid, updatehash, data) VALUES (%s, %s, %s) ON CONFLICT (carid, updatehash) DO NOTHING;", (carId, jsonHash, json.dumps(jsonData, sort_keys=True)))

    cur.execute("""
        INSERT INTO updates (carid, updatehash, firstseen, lastseen)
        VALUES (%s, %s, NOW(), NOW())
        ON CONFLICT (carid, updatehash) DO UPDATE
        SET lastseen = NOW();
        """, (carId, jsonHash,))

def processResponseJson(json, cur):
    for result in json['results']:
        print(result['InventoryPrice'])
        carId = carIdByVin(result['VIN'], cur)
        insertUpdateData(carId, result, cur)


html_url = 'https://www.tesla.com/en_CA/inventory/used/my?arrangeby=plh&zip=V5C'
api_url = 'https://www.tesla.com/inventory/api/v4/inventory-results?query=%7B%22query%22%3A%7B%22model%22%3A%22my%22%2C%22condition%22%3A%22used%22%2C%22options%22%3A%7B%7D%2C%22arrangeby%22%3A%22Price%22%2C%22order%22%3A%22asc%22%2C%22market%22%3A%22CA%22%2C%22language%22%3A%22en%22%2C%22super_region%22%3A%22north%20america%22%2C%22lng%22%3A-123.0101935%2C%22lat%22%3A49.2790413%2C%22zip%22%3A%22V5C%22%2C%22range%22%3A0%2C%22region%22%3A%22BC%22%7D%2C%22offset%22%3A0%2C%22count%22%3A50%2C%22outsideOffset%22%3A0%2C%22outsideSearch%22%3Afalse%2C%22isFalconDeliverySelectionEnabled%22%3Afalse%2C%22version%22%3Anull%7D'

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0 (Edition developer)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'max-age=0',
    'Sec-Ch-Ua-Platform': '"macOS"'
}

html_response = requests.get(html_url, headers=headers)
if html_response.status_code != 200:
    print("failed html request")
    exit(1)

cookies = html_response.cookies


# Make the HTTP GET request to the URL
response = requests.get(api_url, headers=headers, cookies=cookies)

# Check if the request was successful (status code 200)
if response.status_code == 200:
    # Parse the JSON response
    data = response.json()

    conn, cur = connectDatabase()
    processResponseJson(data, cur)
    conn.commit()
    
    # Now you can work with your JSON data object
 #   print(data)
else:
    print(f'Failed to retrieve data: status code {response.status_code}')

