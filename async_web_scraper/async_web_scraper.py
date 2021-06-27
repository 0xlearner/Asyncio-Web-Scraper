import asyncio
import aiohttp
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd





headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'X-Spoonflower-Window-UUID': 'a9bc37a2-9eb2-4a1e-8ea1-fcee89347364',
    'Content-Type': 'application/json',
    'Origin': 'https://www.spoonflower.com',
    'Connection': 'keep-alive',
    'Referer': 'https://www.spoonflower.com/',
    'Sec-GPC': '1',
    'If-None-Match': 'W/95d6572c326b81ce98c7ae27ac449d42',
    'TE': 'Trailers',
}




def get_fabric_names():
    res = requests.get('https://www.spoonflower.com/spoonflower_fabrics')
    soup = BeautifulSoup(res.text, 'lxml')
    fabrics = [fabric.find('h2').text.strip() for fabric in soup.find_all('div', {'class': 'product_detail medium_text'})]
    fabric = [("_".join(fab.upper().replace(u"\u2122", '').split())) for fab in fabrics]
    for index in range(len(fabric)):
        if 'COTTON_LAWN_(BETA)' in fabric[index]:
            fabric[index] = 'COTTON_LAWN_APPAREL'
        elif 'COTTON_POPLIN' in fabric[index]:
            fabric[index] = 'COTTON_POPLIN_BRAVA'
        elif 'ORGANIC_COTTON_KNIT' in fabric[index]:
            fabric[index] = 'ORGANIC_COTTON_KNIT_PRIMA'
        elif 'PERFORMANCE_PIQUÉ' in fabric[index]:
            fabric[index] = 'PERFORMANCE_PIQUE'
        elif 'CYPRESS_COTTON' in fabric[index]:
            fabric[index] = 'CYPRESS_COTTON_BRAVA'
    return fabric



async def get_designEndpoint(session, url):
    """
    Get Design End Point
    :param url:

    """
    async with session.get(url) as response:
        response = await response.read()
        # print(response)
        json_response = json.loads(response.decode("utf-8"))
        extracting_endpoint = json_response['page_results']
        # extracting designId
        design_Id = [item['designId'] for item in extracting_endpoint]
        # extracting designName
        design_Name = [item['name'] for item in extracting_endpoint]
        # extracting creator_Name
        creator_Name = [item['user']['screenName'] for item in extracting_endpoint]

        return design_Id, design_Name, creator_Name

async def get_Fabric_Pricing_Data(session, url):
    """

    Extract all the pricing data with respect to Fabric type
    :param url: detail url
            :Return: json data
    """
    
    async with session.get(url) as response:
        response = await response.read()
        json_response = json.loads(response)
        
        #print(json_response)
        # Extracting Data
        try:
            fabric_name = json_response['data']['fabric_code']
        except:
            fabric_name = 'N/A'
        try:
            test_swatch_meter = json_response['data']['pricing']['TEST_SWATCH_METER']['price']
        except:
            test_swatch_meter = 'N/A'
        try:
            fat_quarter_meter = json_response['data']['pricing']['FAT_QUARTER_METER']['price']
        except:
            fat_quarter_meter = 'N/A'
        try:
            meter = json_response['data']['pricing']['METER']['price']
        except:
            meter = 'N/A'

        # summary = fabric + "|" + str(test_swatch_meter) + "|" + str(fat_quarter_meter) + "|" + str(meter)
        return fabric_name, test_swatch_meter, fat_quarter_meter, meter

async def main():
    urls = []
    tasks = []
    async with aiohttp.ClientSession(headers=headers) as session:
        fabrics = get_fabric_names()
        design_Id, design_Name, creator_Name = await get_designEndpoint(session, 'https://pythias.spoonflower.com/search/v1/designs?lang=en&page_offset=0&sort=bestSelling&product=Fabric&forSale=true&showMatureContent=false&page_locale=en')
        for item in design_Id:
            for fab_type in fabrics[0:-3]:
                price_url = 'https://api-gateway.spoonflower.com/alpenrose/pricing/fabrics/FABRIC_'+ fab_type +'?quantity=1&shipping_country=PK&currency=EUR&measurement_system=METRIC&design_id='+str(item)+'&page_locale=en'
                print(price_url)
                urls.append(price_url)

        for url in urls:
            tasks.append(asyncio.create_task(get_Fabric_Pricing_Data(session, url)))

        results = await asyncio.gather(*tasks)
        #print(type(results))
        return design_Name, creator_Name, results

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    fabrics = get_fabric_names()[0:-3]
    design_Name, creator_Name, results = loop.run_until_complete(main())
    master_dict = {}
    
    for name, creator in zip(design_Name, creator_Name):
        for index in range(len(fabrics)):
            fabric = results[0][0]
            test_swatch_meter = results[0][1]
            fat_quarter_meter = results[0][2]
            meter = results[0][3]
            if (name, creator) not in master_dict.keys():
                master_dict[(name, creator)] = {}
            itemCount = len(master_dict[(name, creator)].values()) / 4
            master_dict[(name, creator)].update({'fabric_name_%02d' %itemCount: fabric,
                    'test_swatch_meter_%02d' %itemCount: test_swatch_meter,
                    'fat_quarter_meter_%02d' %itemCount: fat_quarter_meter,
                    'meter_%02d' %itemCount: meter})
            results.pop(0)
    print(master_dict)
    
    df = pd.DataFrame.from_dict(master_dict, orient='index').reset_index(drop=False)
    df = df.rename(columns={'level_0':'designName','level_1':'screenName'})
    df.to_csv('scraped_data.csv', index=False)
