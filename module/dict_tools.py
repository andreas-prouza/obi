from copy import deepcopy

def deep_merge(a: dict, b: dict) -> dict:
    result = deepcopy(a)
    for bk, bv in b.items():
        av = result.get(bk)
        if isinstance(av, dict) and isinstance(bv, dict):
            result[bk] = deep_merge(av, bv)
        else:
            #print(type(result))
            if bk not in result.keys():
              result[bk] = []
            result[bk] = sorted(list(set(result[bk] + deepcopy(bv))))
    return result


def dict_merge(base_dct, merge_dct):
    base_dct.update({
        key: dict_merge(rtn_dct[key], merge_dct[key])
        if isinstance(base_dct.get(key), dict) and isinstance(merge_dct[key], dict)
        else merge_dct[key]
        for key in merge_dct.keys()
    })