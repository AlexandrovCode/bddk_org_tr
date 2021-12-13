import datetime
import hashlib
import json
import re

# from geopy import Nominatim

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = 'http://www.bddk.org.tr'
    NICK_NAME = 'bddk.org.tr'
    fields = ['overview']

    header = {
        'User-Agent':
            'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Mobile Safari/537.36',
        'Accept':
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-language': 'en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7'
    }

    def get_by_xpath(self, tree, xpath, return_list=False):
        try:
            el = tree.xpath(xpath)
        except Exception as e:
            print(e)
            return None
        if el:
            if return_list:
                return [i.strip() for i in el]
            else:
                return el[0].strip()
        else:
            return None

    def getpages(self, searchquery):
        result_links = []
        url = 'http://www.bddk.org.tr/Kurulus'
        self.get_tree('http://www.bddk.org.tr/Home/DilDegistir', headers=self.header)
        tree = self.get_tree(url, headers=self.header)
        links = self.get_by_xpath(tree, '//div[@class="kategoriContainer"]/a/@href', return_list=True)
        categories = self.get_by_xpath(tree, '//div[@class="kategoriContainer"]/a/span[2]/text()', return_list=True)
        for link in range(len(links)):
            tree = self.get_tree(self.base_url + links[link], headers=self.header)
            names = self.get_by_xpath(tree, '//li[@class="row"]/div[1]/text()', return_list=True)
            for name in names:
                if searchquery in name:
                    result_links.append(f'{self.base_url + links[link]}?={categories[link]}?={name}')
        return result_links

    def get_business_classifier(self, tree, base_xpath, cat):
        final_list = []
        desc = f'{cat}'
        sub_cat = self.get_by_xpath(tree, base_xpath + '/../../../../div/h5/button/text()[1]')
        if sub_cat:
            desc += f', {sub_cat}'

        temp_dict = {
            'code': '',
            'description': desc,
            'label': ''
        }
        final_list.append(temp_dict)

        if final_list:
            return final_list
        else:
            return None

    def get_address(self, tree, base_xpath):
        address = self.get_by_xpath(tree,
                                    base_xpath + '/div[3]/button/@data-adres')

        try:
            zip = re.findall('\d\d\d\d\d*', address)[-1]
        except:
            zip = None
        city = address.split('/')[-1]
        if zip:
            street = address.split(zip)[0]
        else:
            street = ' '.join(address.split(' ')[:-1])
        temp_dict = {
            'streetAddress': street.strip(),
            'country': 'Turkey',
            'fullAddress': address + ', Turkey'
        }
        if zip:
            temp_dict['zip'] = zip

        if city:
            temp_dict['city'] = city
        return temp_dict

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date.strip(), format).strftime('%Y-%m-%d')
        return date

    def check_create(self, tree, xpath, title, dictionary, date_format=None):
        item = self.get_by_xpath(tree, xpath)
        if item:
            if date_format:
                item = self.reformat_date(item, date_format)
            dictionary[title] = item.strip()

    def get_regulator_address(self, tree):
        address = self.get_by_xpath(tree,
                                    '//td[@class="lead"]/../following-sibling::tr[2]/td/text()')
        temp_dict = {
            'fullAddress': address+', Turkey',
            'city': address.split('/')[-1].strip(),
            'country': 'Turkey'
        }
        return temp_dict

    def get_prev_names(self, tree):
        previous_names = []

        company_id = \
            self.get_by_xpath(tree, '//div/text()[contains(., "Company Title Changes")]/../../@ng-click').split(',')[-1]
        id_clean = re.findall('\w+', company_id)[0]
        url = f'https://www.kap.org.tr/en/BildirimSgbfApproval/UNV/{id_clean}'
        tree = self.get_tree(url)

        # names = self.get_by_xpath(tree, '//div[@class="w-clearfix notifications-row"]')
        js = tree.xpath('//text()')[0]
        if js:
            for i in json.loads(js):
                temp_dict = {
                    'name': i['basic']['companyName'],
                    'valid_to': self.reformat_date(i['basic']['publishDate'], '%d.%m.%y %H:%M')
                }
                previous_names.append(temp_dict)

        if previous_names:
            return previous_names
        return None

    def get_overview(self, link_name):
        category = link_name.split('?=')[1]
        name = link_name.split('?=')[-1]
        link = link_name.split('?=')[0]

        tree = self.get_tree(link, headers=self.header)
        base_xpath = f'//li[@class="row"]/div[1]/text()[contains(., "{name}")]/../..'
        company = {}

        try:
            orga_name = self.get_by_xpath(tree,
                                          f'//li[@class="row"]/div[1]/text()[contains(., "{name}")]')
        except:
            return None
        if orga_name: company['vcard:organization-name'] = orga_name.strip()

        company['isDomiciledIn'] = 'TR'



        self.check_create(tree, base_xpath + '/div[2]/a/@href',
                          'hasURL', company)

        classifier = self.get_business_classifier(tree, base_xpath, category)
        if classifier:
            company['bst:businessClassifier'] = classifier

        address = self.get_address(tree, base_xpath)
        if address:
            company['mdaas:RegisteredAddress'] = address



        self.check_create(tree, base_xpath + '/div[3]/button/@data-aciklama', 'bst:description', company)

        self.check_create(tree, base_xpath + '/div[3]/button/@data-telefon', 'tr-org:hasRegisteredPhoneNumber', company)

        self.check_create(tree, base_xpath + '/div[3]/button/@data-faks', 'hasRegisteredFaxNumber', company)

        iden = self.get_by_xpath(tree, base_xpath + '/div[3]/button/@data-eftkodu')
        if iden:
            company['identifiers'] = {"other_company_id_number": iden}

        company['regulator_name'] = 'Banking Regulation And Supervision Agency'

        reg_address = self.get_regulator_address(tree)
        if reg_address:
            company['regulatorAddress'] = reg_address

        company['regulator_url'] = self.base_url
        company['RegulationStatus'] = 'Authorised'

        company['@source-id'] = self.NICK_NAME
        return company

