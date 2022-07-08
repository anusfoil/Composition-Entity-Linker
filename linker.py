import sys
import re
from numpy import result_type
import pandas as pd
import logging

from tqdm import tqdm

import hook


OPUS_TERMS = ["Op.", "K.", "BWV", "FWV", "D.", "SZ.", "L.", "M."]


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
        "no": None
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

    # if len(title.split("No.")) > 1:
    #     info["no"] = re.findall(r'\d+', title.split("No.")[-1])[0] 

    # if title == 'Piano Sonata No. 8 in C Minor, Op. 13 "Pathétique"':
    # if title == 'Piano Sonata No. 8 in C Minor op. 13 "pathetique"':
    # 	hook()

    return info['key'], info['opus']


def format_match(composition, record):
    """format a found match between record and composition"""

    title = composition["composition-title"]
    composer = composition["composer-openopus_name"]
    return f"===> Founded composition for record: \n \
            {record.composer}: {record.track} \n \
            as: \n \
            {composer}: {title} \n"

def similarity(composition, record):
    """return the overall similarity score for a composition

    Args:
        composition: title, work_title, alt_title
        track: track, 
    """


    return 

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

    def query(self, record):
        """query the track information and return the most likely composition

        Args:
            record (pd.row): 
            record.track: track title
            record.composer: 
            record.track_duration: in seconds
        """

        # filter by composer
        database_composer = self.database[self.database['composer-openopus_name'] == record.composer]
        
        key, catalog_number = parse_title_info(record.track)


        composition = database_composer[database_composer['composition-catalogue_number'].str.contains(catalog_number+"'")]
        if len(composition) >= 1:
            rlogger.info(format_match(composition.iloc[0], record))
            return 1
        elif len(composition) >= 2:
            # TODO
            pass
        else:
            rlogger.info(f"+++> Not found: {record.track}")  
            return 0      

        return 
    
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
