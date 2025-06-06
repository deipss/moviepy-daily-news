import json

from volcengine.ApiInfo import ApiInfo
from volcengine.Credentials import Credentials
from volcengine.ServiceInfo import ServiceInfo
from volcengine.base.Service import Service


def batch_translate(txt_list,source_language='zh',target_language='en'):
    k_access_key = ''  # https://console.volcengine.com/iam/keymanage/
    k_secret_key = '=='
    k_service_info = \
        ServiceInfo('translate.volcengineapi.com',
                    {'Content-Type': 'application/json'},
                    Credentials(k_access_key, k_secret_key, 'translate', 'cn-north-1'),
                    5,
                    5)
    k_query = {
        'Action': 'TranslateText',
        'Version': '2020-06-01'
    }
    k_api_info = {
        'translate': ApiInfo('POST', '/', k_query, {}, {})
    }
    service = Service(k_service_info, k_api_info)
    body = {
        'SourceLanguage': source_language,
        'TargetLanguage': target_language,
        'TextList': txt_list,
    }
    res_json = service.json('translate', {}, json.dumps(body))
    res = json.loads(res_json)
    cn_list = []
    for i in res['TranslationList']:
        cn_list.append(i['Translation'])
    return cn_list


# if __name__ == '__main__':
#     data = batch_translate(['在在城桂林枯在在', '要在有有有以夺有'])
#     print(data)
