import sys
import re
from numpy import result_type
import pandas as pd
import logging
from thefuzz import fuzz

from tqdm import tqdm

import hook


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

    movements_name = ", ".join(movements[1])

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
    key_split = re.findall(r'[Ii]n .+?,', title)
    if not key_split:
        key_split = re.findall(r'[Ii]n .+?or', title)
    if key_split:
        key = key_split[0][3:].replace(",", "")
        if "or" not in key:
            key += " Major"
        info['key'] = key.title() # capitalize


    for term in OPUS_TERMS:
        if len(title.split(term)) == 2:
            numeric = re.findall(r'\d+', title.split(term)[1])
            if numeric:
                info["opus"] = f"{term}{numeric[0]}" if ("." in term) else f"{term} {numeric[0]}"

    if len(title.split("No.")) > 1:
        num = re.findall(r'\d+', title.split("No.")[-1])
        if num:
            info["no"] = num[0] 


    return info['key'], info['opus'], info['no']


def format_match(composition, record):
    """format a found match between record and composition"""

    title = composition["composition-title"]
    composer = composition["composer-openopus_name"]
    return f"===> Founded composition for record: \n \
            {record.composer}: {record.track} \n \
            as: \n \
            {composer}: {title} \n"


def similarity(composition, record):
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
    }
    record: {
        "track": "Piano Sonata in A Minor, Op. 42, D. 845: I. Moderato", 
        "composer": "Franz Schubert,
    }

    Return: 
    """	

    # THR = 0.72

    return fuzz.partial_ratio(composition['composition-title'], record.track)


class CELlinker():
    def __init__(self, ref_file_path):
        self.database = pd.read_csv(ref_file_path)
        self.process_reference()

    def process_reference(self):

        self.database = self.database.fillna("N/A")

        # clean the movements
        movements = self.database["composition-movements_or_sections"].apply(parse_movements)
        self.database[['movements_num', 'movements_name']] = pd.DataFrame(movements.tolist())
        
        # clean the catalogue numbers

        return 

    def process_input(self, record):
        """standarize the record input for query"""
        
        # spotify crawled data
        record.composer = record.track_artists.split("/")[0]

        return record

    def query_composition(self, record):
        """query the track information and return the most likely composition

        Args:
            record.track: track title
            record.composer: 
        """

        # filter by composer
        database_composer = self.database[self.database['composer-openopus_name'] == record.composer]
        
        if len(database_composer) == 0:
            return None

        key, catalog_number, work_number = parse_title_info(record.track)

        # filter by catalog number
        composition = database_composer[database_composer['composition-catalogue_number'].str.contains(catalog_number+r"('| |/)")]
        # filter by work number (No.) given that multiple works under one catalog number
        composition_work = composition[composition['composition-catalogue_number'].str.contains(work_number+r"('| |/)")]

        if len(composition) == 1:
            return composition
        elif len(composition_work) == 1:
            return composition_work
        elif len(composition_work) >= 2:
            # TODO
            return None
        else:
            # no catalog number, search all for similarity. 
            database_composer["similarity"] = database_composer.apply(lambda x: similarity(x, record), axis=1)
            database_composer = database_composer.sort_values(by=["similarity"], ascending=False)

            # if "Pictures at an Exhibition dedicated to Viktor Hartman" in record.track:
            #     hook()

            THR = 0.72
            if database_composer.iloc[0].similarity < THR:
                return None
            else:

                return database_composer.iloc[0]
             
    
    def query_movement(self, composition, record):
        
        return 1

    def query(self, record):
        
        composition = self.query_composition(record)

        if composition is not None:
            formated_match = format_match(composition, record)
            # rlogger.info(formated_match)
            return self.query_movement(composition, record)
        else:
            rlogger.info(f"+++> Not found: {record.track}")
            return 0

    def batch_query(self, records_file_path):
        records = pd.read_csv(records_file_path)

        founded_count = 0
        for idx, record in tqdm(records.iterrows()):
            record = self.process_input(record)
            founded_count += self.query(record)
        
        print(f"founded {founded_count} / {len(records)}")

            # if idx == 100:
            #     hook()

        return 
    

    
if __name__ == "__main__":

    # logger = logging.getLogger()
    # logger.setLevel(logging.INFO)

    rlogger = logging.getLogger()
    rlogger.setLevel(logging.INFO)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)

    file_handler = logging.FileHandler('results.log')
    file_handler.setLevel(logging.INFO)

    rlogger.addHandler(file_handler)
    # logger.addHandler(stdout_handler)


    linker = CELlinker("ref_corpus/CEL_meta_new.csv")
    linker.batch_query("spotify_50pianists_records.csv")
