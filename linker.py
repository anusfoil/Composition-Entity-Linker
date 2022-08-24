import sys
import re
from numpy import argmax
import pandas as pd
import logging
import pkg_resources
import json

from tqdm import tqdm

from track import Track
from utils import *

import hook


class CELlinker():
    def __init__(self, ref_file_path=None, log=True):

        ref_file_path = pkg_resources.resource_stream(__name__, "ref_corpus/CEL_meta_new.csv")
        composer_transliteration_json = "ref_corpus/composer_translations.json"

        self.database = pd.read_csv(ref_file_path)
        self.openopus_composers = pd.unique(self.database['composer-openopus_name'])
        with open(composer_transliteration_json, 'r') as f:
            self.composer_transliteration = json.load(f)
        self.process_reference()
        self.log = log

    def process_reference(self):

        self.database = self.database.fillna("N/A")

        # clean the movements
        movements = self.database["composition-movements_or_sections"].apply(parse_movements)
        self.database[['movements_num', 'movements_name']] = pd.DataFrame(movements.tolist())
        
        # clean the catalogue numbers

        return 

    def process_spotify_input(self, record):
        
        composer = record.track_artists.split("/")[0]
        track = Track(record.track,
                        composer=composer)

        return track

    def process_input(self, track):
        """standarize the record input for query
            - clean the composer as the most similar composer name 
            - replace common keywords 
        """

        track.title = track.title.replace("соч.", "Op.")

        if track.composer not in self.openopus_composers:
            composer_similarity = list(map(
                lambda x: composer_transliteration_similarity(
                    self.composer_transliteration[x] if x in self.composer_transliteration else x, 
                    track.composer), 
                self.openopus_composers))
            track.composer = self.openopus_composers[argmax(composer_similarity)]

        return track

    def query_composition(self, record):
        """query the track information and return the most likely composition

        Args:
            record.title: track title
            record.composer: 

        Returns:
            composition: row in the reference dataframe, or None
            movement: None, will be processed in next step
        """

        result = {
            "found_flag": False,
            "composition": None,
            "movement": None,
            "composer": None
        }

        # filter by composer
        composer_composition_list = self.database[self.database['composer-openopus_name'] == record.composer]
        
        # No composer case: search in the entire database
        if len(composer_composition_list) == 0:
            composer_composition_list = self.database

        key, catalog_number, work_number = parse_title_info(record.title)

        # filter by catalog number
        composition_list = composer_composition_list[composer_composition_list['composition-catalogue_number'].str.contains(catalog_number+r"(?:'| |/)")]
        # filter by work number (No.) given that multiple works under one catalog number
        composition_work_list = composition_list[composition_list['composition-catalogue_number'].str.contains(work_number+r"(?:'| |/)")]

        if len(composition_list) == 1:
            result['composition'] = composition_list
        elif len(composition_work_list) == 1:
            result['composition'] = composition_work_list
        else:
            if len(composition_list) == 0:
                composition_list = composer_composition_list

            # no catalog number or more catalog number, search all for similarity. similarity includes the movement
            composition_list["similarity"] = composition_list.apply(lambda x: similarity(x, key, record), axis=1)
            composition_list = composition_list.sort_values(by=["similarity"], ascending=False)

            # if "Баллада No. 1 соль минор" in record.title:
            #     hook()

            THR = 60
            if composition_list.iloc[0].similarity < THR:
                return result
            else:
                result['composition'] = composition_list.iloc[0]
        
        result["composer"] = result['composition']['composer-openopus_name']
        if type(result["composer"]) != str:
            result["composer"] = result["composer"].values[0]
        result["found_flag"] = True
        return result
    
    def query_movement(self, result, record):
        """given the composition entry in reference, match the most likly movement part of the record
        
        args:
            result: 
            record: 
        
        """

        if result["found_flag"]:
            composition = result["composition"]
            movements = composition["movements_name"] if type(composition["movements_name"]) == str else composition["movements_name"].values[0]
            movements = movements.split("||")
            mvt_similarity = list(map(lambda x: string_fuzz_similarity(x, record.title), movements))
            found_mvt = movements[argmax(mvt_similarity)]

            result["movement"] = found_mvt
            result["composition"] = result["composition"]["composition-title"]

            if type(result['composition']) != str:
                result['composition'] = result['composition'].values[0]
        
        return result


    def query(self, record):
        """query the record, return composition as the database row entry"""

        record = self.process_input(record)
        result = self.query_movement(self.query_composition(record), record)
        return result


    def batch_query(self, records_file_path):
        records = pd.read_csv(records_file_path)

        founded, total = [], len(records)
        for idx, record in tqdm(records.iterrows()):
            if ("Applause" in record.track) or ("applause" in record.track) :
                total -= 1
                continue

            query_record = self.process_spotify_input(record)

            # if "Концерт для клавира и струнных" in record.title:
            #     hook()

            result = self.query(query_record)

            if result["found_flag"]:
                founded.append(result)
                formated_match = format_match(result, record)
                # print(formated_match)
                if self.log:
                    rlogger.info(formated_match)
            else:
                if self.log:
                    rlogger.info(f"+++> Not found: {record.composer}: {record.title} ")
        
        print(f"founded {len(founded)} / {total}")


        return 
    
    def compare(self, track1, track2):
        """ compare two tracks for their similarity. right now test if they are map to the same composition
        """
        result1 = self.query(track1)
        result2 = self.query(track2)
        if result1["found_flag"] and result2["found_flag"]:
            return ((result1["composition"] == result2["composition"])
                    and (result1["movement"] == result2["movement"]))

        return False

    
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


    linker = CELlinker(log=True)
    linker.batch_query("spotify_50pianists_records.csv")
