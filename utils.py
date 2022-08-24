import string
import sys
import re
from thefuzz import fuzz

OPUS_TERMS = ["Op.", "K.", "BWV", "FWV", "D.", "Sz.", "L.", "M.", "S.", "Hob."]


def get_substring(exp, str):
    result = re.search(exp, str)
    if result:
        return result.group(0)

    return None

def parse_movements(movements):
    """
    movements: unformatted string
    e.g. [None, []]
        ['unruhig', []]
        ['3 movements', ['Allegro', 'Adagio', 'Allegro']]
        ['1. Presto 2. Largo 3. Allegro', []] <-- outlier

    returns: 
        movements_num: int
        movements_name: string of movements joint by ", "
        num equals the number of movements names
    """
    if movements == "N/A":
        return 0, "N/A" # nan

    movements = eval(movements)
    if movements[0] == None:
        return 0, "N/A" # nan

    if len(movements) > 2:
        # logger.error(f"too much lists: {movements}")
        pass

    match_number_result = re.match(r'\d+', movements[0])
    movements_num = int(match_number_result.group(0)) if match_number_result else 0
    if movements_num != len(movements[1]):
        # logger.error(f"number of movements: {movements}")
        pass

    movements_name = "||".join(movements[1])

    return movements_num, movements_name


def parse_title_info(title):
    """
    title: "Piano Sonata No. 9 in E Major, Op. 14, No. 1: II. Allegretto"

    Return: a dictionary of important information. e.g{
        "key": "E Major",
        "Opus": 14,
        "No": 1,
    }

    Note: for Number we refer to a lower level compared to the Opus. In this example we use No.1 instead of No.9
    """
    info = {
        "key": "N/A",
        "opus": "N/A",
        "no": "N/A"
    }

    """read the key and capitalize it"""
    key_split = re.findall(r'[Ii]n .+?,', title) # find "in"
    if not key_split:
        key_split = re.findall(r'[Ii]n .+?or', title)
    if not key_split: # no "in", but the key is in parentheses
        key_split = re.findall(r'\(.+?or', title)
    
    if key_split:
        key = re.sub(r"[(,]", "", key_split[0])
        key = re.sub(r"[Ii]n ", "", key)

        if "or" not in key:
            key += " Major"
        info['key'] = key.title() # capitalize

    info['key'] = info['key'].replace("♯", " Sharp")
    info['key'] = info['key'].replace("♭", " Flat")


    for term in OPUS_TERMS:
        # if there are multiple opus terms, get the last one
        if len(title.split(term)) >= 2:
            numeric = re.findall(r'\d+', title.split(term)[-1])
            if numeric:
                info["opus"] = f"{term}{numeric[0]}" if ("." in term) else f"{term} {numeric[0]}"

    if len(title.split("No.")) > 1:
        num = re.findall(r'\d+', title.split("No.")[-1])
        if num:
            info["no"] = num[0] 


    return info['key'], info['opus'], info['no']


def format_match(result, record):
    """format a found match between record and composition
    
    result:
        composition: str, composition name
        movement: str
        composer: str, composer in database
    record: 
    """

    title = result["composition"]
    movement = result["movement"]
    composer = result["composer"]
    return f"===> Founded composition for record: \n \
            {record.composer}: {record.title} \n \
            as: \n \
            {composer}: {title}: {movement} \n"


def composer_transliteration_similarity(openopus_composer, track_composer):
    """
    openopus_composer: {'transliteration': ['Jean Sébastien Bach (fr)', 'Jan Sebastian Bach', 'John Sebastian Bach (en)'], 'other_languages': ['Jean-Sébastien Bach', 'Иоганн Себастьян Бах', 'ইয়োহান জেবাস্টিয়ান বাখ', 'یۆھان سباستیان باخ', '巴赫'], 'aliases': ['Bach', 'Ёган Бах', 'Бах', 'Йоганн Себастиан', 'Бах']}
    """

    if type(openopus_composer) == str:
        return string_fuzz_similarity(track_composer, openopus_composer)
    # list of all names
    all_names = openopus_composer['transliterations'] + list(openopus_composer['other_languages'].values()) + list(openopus_composer['alias'].values())
    if not all_names:
        return 0
    return max([string_fuzz_similarity(track_composer, name) for name in all_names])


def string_fuzz_similarity(s1, s2):
    return fuzz.partial_ratio(s1, s2)


def similarity(composition, key, record):
    """
    composition: title, compositon
    record: track, 

    Input: rep includes all possible movements
    composition = {
        "composition-title"                                                   Impromptu passione
        "composition-link"                     https://imslp.org/wiki/Impromptu_passione_(Mus...
        "composition-work_title"                                              Impromptu passione
        "composition-alt_title"                ['Souvenir de Beltov et Liouba (Recollection o...
        "composition-translations"                                                            {}
        "composition-alias"                                                                   {}
        "composition-catalogue_number"                                                        []
        "composition-I-catalogue_number"                                                  IMM 27
        "composition-key"                                                                    N/A
        "composition-movements_or_sections"                                            ['1', []]
        "composition-language"                                                               N/A
        "composition-average_duration"                                                       N/A
        "composition-composer_period"                                                   Romantic
        "composition-piece_style"                                                       Romantic
        "composition-instrumentation"                                                      piano
        "composition-genre"                                                           Impromptus
        "composer-openopus_name"                                               Modest Mussorgsky
        "composer-imslp_name"                                                 Mussorgsky, Modest
        "composer-birth"                                                              21-03-1839
        "composer-death"                                                              28-03-1881
        "movements_num"                                                                        1
        "movements_name"                       Allegro moderato (G major)||Minuet - Trio (G m...
    }

    key: "A Minor"

    record: {
        "title": "Piano Sonata in A Minor, Op. 42, D. 845: I. Moderato", 
        "composer": "Franz Schubert,
    }

    Return: 
    """	

    title_translations = [composition['composition-title']]
    if composition['composition-translations'] != "N/A":
        title_translations += list(eval(composition['composition-translations']).values()) 
    if composition['composition-alias'] != "N/A":
        title_translations += list(eval(composition['composition-alias']).values())
    composition_sim = list(map(lambda x: string_fuzz_similarity(x, record.title), title_translations))


    mvt_sim = [0]
    if composition["movements_name"] != "N/A":
        movements = composition["movements_name"] if type(composition["movements_name"]) == str else composition["movements_name"].values[0]
        movements = movements.split("||")
        mvt_sim = list(map(lambda x: string_fuzz_similarity(x, record.title) - 30 * (key != parse_title_info(x)[0]), 
                movements))

    # if "Polonaise in G-flat major" in composition['composition-title']:
    #     hook()

    # the similarity is determined by title and movements together
    return max(composition_sim) + max(mvt_sim)
