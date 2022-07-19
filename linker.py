import sys
import re
from numpy import argmax
import pandas as pd
import logging
import pkg_resources

from tqdm import tqdm

from track import Track
from utils import *

import hook


class CELlinker():
    def __init__(self, ref_file_path=None, log=True):
        if not ref_file_path:
            ref_file_path = pkg_resources.resource_stream(__name__, "ref_corpus/CEL_meta_new.csv")

        self.database = pd.read_csv(ref_file_path)
        self.all_composers = pd.unique(self.database['composer-openopus_name'])
        self.process_reference()
        self.log = log

    def process_reference(self):

        self.database = self.database.fillna("N/A")

        # clean the movements
        movements = self.database["composition-movements_or_sections"].apply(parse_movements)
        self.database[['movements_num', 'movements_name']] = pd.DataFrame(movements.tolist())
        
        # clean the catalogue numbers

        return 

    def process_input(self, record):
        """standarize the record input for query

        clean the composer as the most similar composer name
        """
        
        composer = record.track_artists.split("/")[0]
        if composer not in self.all_composers:
            composer_similarity = list(map(lambda x: string_fuzz_similarity(x, composer), self.all_composers))
            composer = self.all_composers[argmax(composer_similarity)]

        # spotify crawled data
        track = Track(record.track,
                        composer=composer)

        return track

    def query_composition(self, record):
        """query the track information and return the most likely composition

        Args:
            record.title: track title
            record.composer: 

        Returns:
            composition: row in the reference dataframe

            (if composition not found then return 0)
        """

        # filter by composer
        composer_composition_list = self.database[self.database['composer-openopus_name'] == record.composer]
        
        if len(composer_composition_list) == 0:
            return None

        key, catalog_number, work_number = parse_title_info(record.title)

        # filter by catalog number
        composition_list = composer_composition_list[composer_composition_list['composition-catalogue_number'].str.contains(catalog_number+r"(?:'| |/)")]
        # filter by work number (No.) given that multiple works under one catalog number
        composition_work_list = composition_list[composition_list['composition-catalogue_number'].str.contains(work_number+r"(?:'| |/)")]


        if len(composition_list) == 1:
            return composition_list
        elif len(composition_work_list) == 1:
            return composition_work_list
        else:
            if len(composition_list) == 0:
                composition_list = composer_composition_list
            # no catalog number or more catalog number, search all for similarity. 
            composition_list["similarity"] = composition_list.apply(lambda x: similarity(x, record), axis=1)
            composition_list = composition_list.sort_values(by=["similarity"], ascending=False)

            # if "Lyriske Stykke Op. 12 No.1: I" in record.title:
            #     hook()
            # if "Cello Sonata No. 5 in D Major, Op. 102 No. 2: " in record.title:
            #     hook()

            THR = 60
            if composition_list.iloc[0].similarity < THR:
                return 0
            else:
                return composition_list.iloc[0]
             
    
    def query_movement(self, composition, record):
        
        return composition


    def query(self, record):
        """query the record, return composition as the database row entry"""
        
        composition = self.query_composition(record)

        if composition is not 0:
            formated_match = format_match(composition, record)
            # print(formated_match)
            # rlogger.info(formated_match)
            return self.query_movement(composition, record)
        else:
            if self.log:
                rlogger.info(f"+++> Not found: {record.composer}: {record.title} ")
            return 0

    def batch_query(self, records_file_path):
        records = pd.read_csv(records_file_path)

        founded, total = [], len(records)
        for idx, record in tqdm(records.iloc[:1000].iterrows()):
            if ("Applause" in record.track) or ("applause" in record.track):
                total -= 1
                continue

            result = self.query(self.process_input(record))
            if type(result) != int:
                founded.append(result)
        
        print(f"founded {len(founded)} / {total}")

            # if idx == 100:
            #     hook()

        return 
    
    def compare(self, track1, track2):
        """ compare two tracks for their similarity. right now test if they are map to the same composition
        """
        return self.query(track1) == self.query(track2)

    
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
