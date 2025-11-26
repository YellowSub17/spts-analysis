

ps20 = [(431, 436)]
ps30 = [(415, 420)]
ps40 = [(408, 413)]
ps50 = [(395, 400)]


### ranges are python indexed (end is +1 of what you want)

ps50nm2p00mm = [
    (444,449), 
]

ps50nm2p50mm = [
    (462,467),
]

ps50nm2p25mm = [
    (478,481),
]

ps40nm2p00mm = [
    (496,501),
]

ps40nm2p25mm = [
    (514,519),
]

ps30nm2p00mm = [
    (525,528),
]

ps30nm2p25mm = [
#    (520,524), ##### was this 2mm or 2.25 inj?
    (556, 560), 
    (561, 564)
]

ps20nm2p00mm = [
    (565, 570),
    (573, 579),
    (580, 582),
]

ps20nm2p25mm = [
    (598, 604),
    (605, 610),
]

def generate_filenames(ranges, a, let='a'):
    files = []
    for r in ranges:
        files +=[f'/home/tejvarmay/scattering_data/data/newdata/data00{i}_analysis_{let}{a}/spts.cxi' for i in range(r[0], r[1])]
    return files


    

### todo:
### feratin
### new neutralizer ranges

background_runs = [
    705,
    694,
    683,
    671,
    664,
    657,
    650,
    643,
    636,
    631,
    624,
    618,
    610,
    604,
    579,
    570,
]

bkgrnd = [ (i, i+1) for i in background_runs ]



ps40nm = [(651,657)]
ps30nm = [(658, 664)]
ps20nm = [(665, 671)]
ps50nm = [(674, 683)]

fe_he42 = [(684, 694)]
fe_he28 = [(695, 705)]


