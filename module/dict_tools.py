from copy import deepcopy

def deep_merge(a: dict, b: dict) -> dict:
    
    result = deepcopy(a)

    for b_level, b_source_list in b.items(): #b_level=b-key; b_source_list=b-value  Levels

        for b_source in b_source_list:

            if b_level not in result.keys():
                result[b_level] = []

            if b_source['source'] in [item['source'] for item in result[b_level]]:
                continue

            result[b_level].append(b_source)

    return result



def deep_list_merge(a: [], b: []) -> []:
    """[
            {
                'level': 3, 
                'sources': 
                    [
                        {
                            'source': 'prouzalib/qrpglesrc/cpysrc2ifs.sqlrpgle.pgm', 
                            'cmds': []
                        }, 
                        {'source': ...
    """
    
    result = deepcopy(a)

    for b_level_item in b:

        b_level = b_level_item['level']
        b_sources = b_level_item['sources']

        result_level_item = [item for item in result if item['level'] == b_level]
        if result_level_item:
            result_level_item = result_level_item[0]

        if not result_level_item:
            result_level_item={'level': b_level, 'sources': []}
        
        print(f"{result_level_item=}")

        for b_source in b_sources: #b_level=b-key; b_source_list=b-value  Levels

            if b_source['source'] in [item['source'] for item in result_level_item['sources']]:
                continue

            #result_level_item['sources'].append({'source': b_source['source'], 'cmds': b_source['cmds']})

            found = False
            for i in range(len(result)):
                if b_level != result[i]['level']:
                    continue
                found = True
                result[i]['sources'].append({'source': b_source['source'], 'cmds': b_source['cmds']})
                break

            if not found:
                result.append({'level': b_level, 'sources': [{'source': b_source['source'], 'cmds': b_source['cmds']}]})

    return result



def dict_merge(base_dct, merge_dct):
    base_dct.update({
        key: dict_merge(rtn_dct[key], merge_dct[key])
        if isinstance(base_dct.get(key), dict) and isinstance(merge_dct[key], dict)
        else merge_dct[key]
        for key in merge_dct.keys()
    })