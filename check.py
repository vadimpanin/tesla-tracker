import requests
import psycopg2
import json
import hashlib
import time
import subprocess

def connectDatabase():
    conn_string = "host='localhost' dbname='tesla' user='postgres' password='secret'"
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    print("DB Connected!")
    return conn, cursor

def getCarIdByVin(vin, cur):
    cur.execute("SELECT carid FROM cars WHERE vin = %s", (vin,))
    result = cur.fetchone()
    return result[0] if result else None

def insertCar(vin, cur):
    cur.execute("INSERT INTO cars (vin) VALUES (%s) RETURNING carid", (vin,))
    return cur.fetchone()[0]

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

def getLatestUpdateData(carId, cur):
    cur.execute("SELECT updatehash FROM updates WHERE carid=%s ORDER BY lastseen DESC LIMIT 1", (carId,))
    result = cur.fetchone()
    updateHash = result[0]
    cur.execute("SELECT data FROM updatedata WHERE carid=%s and updatehash=%s",(carId, updateHash,))
    result = cur.fetchone()
    return result[0]

class CarDesc:
    def __init__(self, product : str, result : dict):
        self.vin = result['VIN']
        self.product = product
        self.trim = result['TRIM']
        self.price = result['InventoryPrice']
        self.color = result['PAINT']
        self.year = result['Year']
        self.odo = str(result['Odometer']) + result['OdometerType']

    def to_string(self):
        return f"{self.product} {self.trim} {self.vin} {self.price} {self.color} {self.year} {self.odo}"

def notifyNewCar(desc):
    message = f"new {desc.to_string()}"
    print(message)
    subprocess.call(["./telegram", message], shell=False)

def notifyNewPrice(desc, prevDesc):
    message = f"price {prevDesc.to_string()} -> {desc.price}"
    print(message)
    subprocess.call(["./telegram", message], shell=False)

def processResponseJson(json, cur, product):
    for result in json['results']:
        desc = CarDesc(product, result)
        print(desc.to_string())

        carId = getCarIdByVin(desc.vin, cur)
        if carId == None:
            carId = insertCar(desc.vin, cur)
            notifyNewCar(desc)
        else:
            prevDesc = CarDesc(product, getLatestUpdateData(carId, cur))
            if prevDesc.price != desc.price:
                notifyNewPrice(desc, prevDesc)

        insertUpdateData(carId, result, cur)


html_url = 'https://www.tesla.com/en_CA/inventory/used/my?arrangeby=plh&zip=V5C'
api_urls = {
        "MY": 'https://www.tesla.com/inventory/api/v4/inventory-results?query=%7B%22query%22%3A%7B%22model%22%3A%22my%22%2C%22condition%22%3A%22used%22%2C%22options%22%3A%7B%7D%2C%22arrangeby%22%3A%22Price%22%2C%22order%22%3A%22asc%22%2C%22market%22%3A%22CA%22%2C%22language%22%3A%22en%22%2C%22super_region%22%3A%22north%20america%22%2C%22lng%22%3A-123.0101935%2C%22lat%22%3A49.2790413%2C%22zip%22%3A%22V5C%22%2C%22range%22%3A0%2C%22region%22%3A%22BC%22%7D%2C%22offset%22%3A0%2C%22count%22%3A50%2C%22outsideOffset%22%3A0%2C%22outsideSearch%22%3Afalse%2C%22isFalconDeliverySelectionEnabled%22%3Afalse%2C%22version%22%3Anull%7D',
        "M3": 'https://www.tesla.com/inventory/api/v4/inventory-results?query=%7B%22query%22%3A%7B%22model%22%3A%22m3%22%2C%22condition%22%3A%22used%22%2C%22options%22%3A%7B%7D%2C%22arrangeby%22%3A%22Price%22%2C%22order%22%3A%22asc%22%2C%22market%22%3A%22CA%22%2C%22language%22%3A%22en%22%2C%22super_region%22%3A%22north%20america%22%2C%22lng%22%3A-123.0101935%2C%22lat%22%3A49.2790413%2C%22zip%22%3A%22V5C%22%2C%22range%22%3A0%2C%22region%22%3A%22BC%22%7D%2C%22offset%22%3A0%2C%22count%22%3A50%2C%22outsideOffset%22%3A0%2C%22outsideSearch%22%3Afalse%2C%22isFalconDeliverySelectionEnabled%22%3Afalse%2C%22version%22%3Anull%7D'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0 (Edition developer)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'max-age=0',
    'Sec-Ch-Ua-Platform': '"macOS"'
}

def doOneRun():

    html_response = requests.get(html_url, headers=headers)
    if html_response.status_code != 200:
        print("failed html request")
        return

    cookies = html_response.cookies

    for product_url in api_urls.items():
        product = product_url[0]
        api_url = product_url[1]
        #print(f"{product} {api_url}")
        response = requests.get(api_url, headers=headers, cookies=cookies)

        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()

            conn, cur = connectDatabase()
            processResponseJson(data, cur, product)
            conn.commit()
    
        else:
            print(f'Failed to retrieve data: status code {response.status_code}')


while True:
    doOneRun()
    time.sleep(300)

